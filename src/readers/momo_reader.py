"""Lecteur des relevés MTN Mobile Money (MoMo).

Lit la feuille « CPTE BUSINESS » des relevés MoMo de l'Hôtel Zingana.
Extrait les paiements clients (Type == 'Payment' et Status == 'Successful')
et écarte les virements internes vers le compte principal (Type == 'Adjustment').
"""

import re
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Union

from openpyxl import load_workbook

from src.models import (
    MODE_MTN_MOMO,
    LotImport,
    Periode,
    TransactionOM,
)
from src.normalization.amounts import ZERO, AmountParseError, parse_amount
from src.normalization.dates import parse_date
from src.normalization.references import normalize_msisdn
from src.normalization.text import clean_text, normalize_key
from src.readers.om_reader import CompteOM, LectureOM

PROFONDEUR_ENTETE = 10


class MomoReader:
    """Charge un relevé MTN Mobile Money et en extrait les transactions clients."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)

    def read(self) -> LectureOM:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable : {self.filepath}")

        classeur = load_workbook(self.filepath, read_only=True, data_only=True)
        try:
            nom_feuille = self._trouver_feuille(classeur)
            feuille = classeur[nom_feuille]
            lignes = [tuple(ligne) for ligne in feuille.iter_rows(values_only=True)]
        finally:
            classeur.close()

        rang_entete, colonnes = self._mapper_colonnes(lignes)

        lot = LotImport()
        comptes_vus: set[str] = set()
        dates_vues: list[date] = []

        for numero, ligne in enumerate(lignes[rang_entete + 1:], start=rang_entete + 2):
            if not any(c not in (None, "") for c in ligne):
                continue

            self._traiter_ligne(numero, ligne, colonnes, lot, comptes_vus, dates_vues)

        comptes = [
            CompteOM(
                numero=c,
                intitule="MTN Mobile Money",
                libelle=f"Compte Marchand MoMo ({c})",
            )
            for c in sorted(comptes_vus)
        ]
        if not comptes:
            comptes = [CompteOM(numero="MOMO", intitule="MTN Mobile Money", libelle="Compte MoMo")]

        periode_declaree = None
        if dates_vues:
            periode_declaree = Periode(min(dates_vues), max(dates_vues))

        return LectureOM(
            lot=lot,
            comptes=comptes,
            commissions=[],
            periode_declaree=periode_declaree,
        )

    def _trouver_feuille(self, classeur) -> str:
        """Privilégie la feuille CPTE BUSINESS ou celle contenant BUSINESS."""
        for nom in classeur.sheetnames:
            cle = normalize_key(nom)
            if "CPTE BUSINESS" in cle or "BUSINESS" in cle:
                return nom
        # Fallback : première feuille
        return classeur.sheetnames[0]

    def _mapper_colonnes(self, lignes: list[tuple]) -> tuple[int, dict[str, int]]:
        """Identifie la ligne d'en-tête et les colonnes clés du relevé MoMo."""
        champs_attendus = {
            "date": {"DATE"},
            "status": {"STATUS", "STATUT"},
            "type": {"TYPE"},
            "from": {"FROM"},
            "from_name": {"FROM NAME", "NOM DU PAYEUR", "NOM PAYEUR"},
            "to": {"TO"},
            "to_handler_name": {"TO HANDLER NAME"},
            "amount": {"AMOUNT", "MONTANT"},
            "balance": {"BALANCE", "SOLDE"},
        }

        for rang, ligne in enumerate(lignes[:PROFONDEUR_ENTETE]):
            trouves = {}
            for idx, cell in enumerate(ligne):
                if cell is None:
                    continue
                cle = normalize_key(str(cell))
                for champ, alias in champs_attendus.items():
                    if champ not in trouves and cle in alias:
                        trouves[champ] = idx

            if "date" in trouves and "amount" in trouves and ("type" in trouves or "status" in trouves):
                return rang, trouves

        raise ValueError(
            f"En-tête MoMo introuvable dans les {PROFONDEUR_ENTETE} premières lignes "
            f"de {self.filepath.name}."
        )

    def _traiter_ligne(
        self,
        numero: int,
        ligne: tuple,
        colonnes: dict[str, int],
        lot: LotImport,
        comptes_vus: set[str],
        dates_vues: list[date],
    ) -> None:
        idx_date = colonnes.get("date")
        idx_status = colonnes.get("status")
        idx_type = colonnes.get("type")
        idx_from = colonnes.get("from")
        idx_from_name = colonnes.get("from_name")
        idx_to = colonnes.get("to")
        idx_amount = colonnes.get("amount")

        val_date = ligne[idx_date] if idx_date is not None and idx_date < len(ligne) else None
        if val_date in (None, ""):
            return

        dt = None
        if isinstance(val_date, datetime):
            dt = val_date
        elif isinstance(val_date, date):
            dt = datetime.combine(val_date, time(0, 0, 0))
        else:
            try:
                d = parse_date(val_date)
                dt = datetime.combine(d, time(0, 0, 0))
            except Exception:
                lot.rejeter(numero, f"date illisible ({val_date})")
                return

        date_op = dt.date()
        heure_op = dt.time()

        val_amount = ligne[idx_amount] if idx_amount is not None and idx_amount < len(ligne) else None
        try:
            montant = parse_amount(val_amount)
        except AmountParseError as err:
            lot.rejeter(numero, f"montant illisible ({err})")
            return

        type_op = clean_text(str(ligne[idx_type])) if idx_type is not None and idx_type < len(ligne) and ligne[idx_type] is not None else "Payment"
        status_op = clean_text(str(ligne[idx_status])) if idx_status is not None and idx_status < len(ligne) and ligne[idx_status] is not None else "Successful"

        from_raw = str(ligne[idx_from]) if idx_from is not None and idx_from < len(ligne) and ligne[idx_from] is not None else ""
        from_name = clean_text(str(ligne[idx_from_name])) if idx_from_name is not None and idx_from_name < len(ligne) and ligne[idx_from_name] is not None else ""
        to_raw = str(ligne[idx_to]) if idx_to is not None and idx_to < len(ligne) and ligne[idx_to] is not None else ""

        # Compte marchand
        compte_agent = normalize_msisdn(to_raw) or to_raw.replace("FRI:", "").replace("/MM", "")
        if compte_agent:
            comptes_vus.add(compte_agent)

        # Correspondant (MSISDN)
        correspondant = normalize_msisdn(from_raw)

        # Filtrage métier : seuls les paiements clients réussis sont rapprochés
        cle_type = normalize_key(type_op)
        if cle_type in {"ADJUSTMENT", "TRANSFERT", "VIREMENT"}:
            lot.rejeter(numero, f"opération interne ({type_op}) écartée")
            return

        if montant <= ZERO:
            lot.rejeter(numero, f"montant non positif ({montant})")
            return

        dates_vues.append(date_op)
        ref = f"MOMO-{dt.strftime('%y%m%d%H%M%S')}-{numero}"

        transaction = TransactionOM(
            numero=numero,
            date_operation=date_op,
            reference=ref,
            service=type_op,
            statut=status_op,
            compte_agent=compte_agent,
            heure=heure_op,
            correspondant=correspondant,
            debit=ZERO,
            credit=montant,
            commission=ZERO,
            libelle_compte=from_name,
            operateur=MODE_MTN_MOMO,
        )
        lot.retenues.append(transaction)
