"""Lecteur du journal des encaissements.

C'est **la** source du rapprochement. Contrairement au journal des arrhes, qui ne
porte que les arrhes, celui-ci recense tous les encaissements de la journée — arrhes
et factures — ventilés par mode de paiement, une colonne par mode. La colonne
« Orange Money » délimite donc à elle seule le périmètre du contrôle.

Sa structure : un bloc d'en-tête portant la période, la table à partir de la deuxième
ligne, puis un bloc « RECAPITULATIF », une note de bas de page et une pagination.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from openpyxl import load_workbook

from config.settings import ENCAISSEMENTS_MODE_OM, ENCAISSEMENTS_COLONNE_LIBELLE
from src.models import LigneJournal, LotImport, Periode
from src.normalization.amounts import ZERO, AmountParseError, normalize_amount, parse_amount
from src.normalization.dates import DateParseError, parse_date
from src.normalization.text import clean_text, normalize_key

#: « Période du 16/04/2026 au 16/04/2026 », dans le bloc d'en-tête.
_PERIODE = re.compile(
    r"P[ée]riode\s+du\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+au\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)

#: « Réservation N°8207 » — identifie une arrhe et porte son numéro.
_RESERVATION = re.compile(r"R[ée]servation\s+N[°o]\s*(\d+)", re.IGNORECASE)

#: « H-7129 », « KOT-4216 », « BAL-6976 » — la référence de la facture.
_FACTURE = re.compile(r"^([A-Z]{1,4}-\d+)", re.IGNORECASE)

#: Le bloc de bas de page, à écarter.
_FIN_DE_TABLE = ("RECAPITULATIF", "RECAPITULATIF ", "TOTAL PERIODE")

PROFONDEUR_ENTETE = 6


@dataclass(frozen=True)
class MouvementEncaissement:
    """Une ligne du journal, ramenée à sa part Orange Money."""

    ligne_source: int
    libelle: str
    reference: str
    montant_om: object
    montant_total: object
    est_arrhe: bool
    date_mouvement: Optional[date] = None

    @property
    def nature(self) -> str:
        return "Arrhe" if self.est_arrhe else "Facture"


@dataclass
class LectureEncaissements:
    """Résultat de la lecture d'une journée d'encaissements."""

    periode: Periode
    lot: LotImport = field(default_factory=LotImport)
    periode_deduite: bool = False
    #: Totaux annoncés par le bloc « RECAPITULATIF », pour contrôle.
    total_declare_om: object = ZERO
    total_declare_arrhes: object = ZERO
    total_declare_factures: object = ZERO
    source: str = ""

    @property
    def mouvements(self) -> list[MouvementEncaissement]:
        return self.lot.retenues

    @property
    def lignes_orange_money(self) -> list[LigneJournal]:
        """Le périmètre du rapprochement, au format canonique attendu par le moteur."""
        from datetime import datetime

        jour_defaut = self.periode.debut
        return [
            LigneJournal(
                ligne_source=mouvement.ligne_source,
                date_operation=datetime(
                    (mouvement.date_mouvement or jour_defaut).year,
                    (mouvement.date_mouvement or jour_defaut).month,
                    (mouvement.date_mouvement or jour_defaut).day,
                ),
                client=mouvement.libelle,
                mode_paiement="Orange Money",
                montant=mouvement.montant_om,
                reference_interne=mouvement.reference,
                libelle=mouvement.libelle,
                est_arrhe=mouvement.est_arrhe,
            )
            for mouvement in self.mouvements
        ]

    def ventiler_par_jour(self) -> list["LectureEncaissements"]:
        """Ventile une lecture multi-jours en lectures journalières individuelles.

        Si la période ne couvre qu'un seul jour, renvoie [self].
        Sinon, ventile les mouvements par jour effectif.
        """
        if self.periode.debut == self.periode.fin:
            return [self]

        mouvements_par_jour: dict[date, list[MouvementEncaissement]] = {}
        for m in self.mouvements:
            j = m.date_mouvement or self.periode.debut
            mouvements_par_jour.setdefault(j, []).append(m)

        if not mouvements_par_jour:
            return [self]

        lectures: list[LectureEncaissements] = []
        for jour in sorted(mouvements_par_jour):
            lot = LotImport()
            lot.retenues = list(mouvements_par_jour[jour])
            total_om = sum((m.montant_om for m in lot.retenues), ZERO)
            total_arrhes = sum((m.montant_om for m in lot.retenues if m.est_arrhe), ZERO)
            total_factures = sum((m.montant_om for m in lot.retenues if not m.est_arrhe), ZERO)
            lectures.append(
                LectureEncaissements(
                    periode=Periode(jour, jour),
                    lot=lot,
                    periode_deduite=self.periode_deduite,
                    total_declare_om=total_om,
                    total_declare_arrhes=total_arrhes,
                    total_declare_factures=total_factures,
                    source=f"{self.source} ({jour.strftime('%d/%m/%Y')})",
                )
            )
        return lectures

    @property
    def total_om(self):
        return sum((mouvement.montant_om for mouvement in self.mouvements), ZERO)

    @property
    def total_arrhes(self):
        return sum((m.montant_om for m in self.mouvements if m.est_arrhe), ZERO)

    @property
    def total_factures(self):
        return sum((m.montant_om for m in self.mouvements if not m.est_arrhe), ZERO)

    def ecart_au_recapitulatif(self):
        """Écart entre les lignes lues et le total que le fichier annonce lui-même.

        Un écart non nul signale une lecture incomplète : le fichier porte sa propre
        vérification, autant s'en servir.
        """
        return self.total_om - self.total_declare_om


class EncaissementsReader:
    """Charge un journal des encaissements et en extrait la part Orange Money."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)

    def read(self) -> LectureEncaissements:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable : {self.filepath}")

        classeur = load_workbook(self.filepath, read_only=True, data_only=True)
        try:
            feuille = classeur[classeur.sheetnames[0]]
            lignes = [tuple(ligne) for ligne in feuille.iter_rows(values_only=True)]
        finally:
            classeur.close()

        rang_entete, colonne_om, colonne_libelle, colonne_date = self._trouver_entete(lignes)
        periode, deduite = self._periode(lignes[:rang_entete])
        est_multi_jours = (periode.debut != periode.fin)

        lot = LotImport()
        recapitulatif: dict[str, Any] = {}
        dans_recapitulatif = False
        date_section_courante: Optional[date] = None

        for numero, ligne in enumerate(lignes[rang_entete + 1:], start=rang_entete + 2):
            if not any(cellule not in (None, "") for cellule in ligne):
                continue

            libelle = clean_text(ligne[colonne_libelle] if colonne_libelle < len(ligne) else "")
            cles_ligne = [normalize_key(libelle)] + [
                normalize_key(str(c)) for c in ligne if c and isinstance(c, str)
            ]
            if any(
                cle in _FIN_DE_TABLE or cle.startswith("TOTAL PERIODE")
                for cle in cles_ligne
            ):
                dans_recapitulatif = True

            if dans_recapitulatif:
                self._collecter_recapitulatif(libelle, ligne, colonne_om, recapitulatif)
                lot.rejeter(numero, "bloc Récapitulatif")
                continue

            if est_multi_jours:
                date_section = self._extraire_date_section(ligne, colonne_om)
                if date_section:
                    date_section_courante = date_section

            self._traiter(
                numero,
                ligne,
                colonne_om,
                libelle,
                lot,
                colonne_date=colonne_date if est_multi_jours else None,
                date_fallback=date_section_courante or periode.debut if est_multi_jours else periode.debut,
                periode_limite=periode if est_multi_jours else None,
            )

        return LectureEncaissements(
            periode=periode,
            lot=lot,
            periode_deduite=deduite,
            total_declare_om=recapitulatif.get("total", ZERO),
            total_declare_arrhes=recapitulatif.get("arrhes", ZERO),
            total_declare_factures=recapitulatif.get("factures", ZERO),
            source=self.filepath.name,
        )

    # --- en-tête ---------------------------------------------------------------

    def _trouver_entete(self, lignes: list[tuple]) -> tuple[int, int, int, Optional[int]]:
        """Localise la ligne d'en-tête, la colonne OM, le libellé et l'éventuelle colonne date."""
        cible = normalize_key(ENCAISSEMENTS_MODE_OM)
        for rang, ligne in enumerate(lignes[:PROFONDEUR_ENTETE]):
            for index, cellule in enumerate(ligne):
                if normalize_key(cellule) == cible:
                    libelle = self._colonne_libelle(ligne)
                    colonne_date = self._colonne_date(ligne)
                    return rang, index, libelle, colonne_date
        raise ValueError(
            f"Colonne « {ENCAISSEMENTS_MODE_OM} » introuvable dans les "
            f"{PROFONDEUR_ENTETE} premières lignes de {self.filepath.name}. "
            "S'agit-il bien d'un journal des encaissements ?"
        )

    @staticmethod
    def _colonne_libelle(entete: tuple) -> int:
        cible = normalize_key(ENCAISSEMENTS_COLONNE_LIBELLE)
        for index, cellule in enumerate(entete):
            if normalize_key(cellule) == cible:
                return index
        return 0  # le libellé occupe la première colonne dans les exports observés

    @staticmethod
    def _colonne_date(entete: tuple) -> Optional[int]:
        cibles = {
            "date",
            "jour",
            "date operation",
            "date op",
            "date mouvement",
            "date encaissement",
            "date reglement",
            "date paiement",
        }
        for index, cellule in enumerate(entete):
            if cellule and normalize_key(str(cellule)) in cibles:
                return index
        return None

    # --- lignes ----------------------------------------------------------------

    @staticmethod
    def _extraire_date_section(ligne: tuple, colonne_om: int) -> Optional[date]:
        """Détecte une ligne de rupture/séparateur de journée dans un journal multi-jours."""
        if colonne_om < len(ligne) and ligne[colonne_om] not in (None, "", 0):
            return None
        cellules_non_vides = [c for c in ligne if c not in (None, "")]
        if not (1 <= len(cellules_non_vides) <= 3):
            return None
        for c in cellules_non_vides:
            if isinstance(c, (datetime, date)):
                return parse_date(c)
            texte = str(c).strip()
            m = re.search(
                r"(?:journ[ée]e|date|du)?\s*(?:du|:)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                texte,
                re.IGNORECASE,
            )
            if m:
                try:
                    return parse_date(m.group(1))
                except Exception:
                    pass
        return None

    @staticmethod
    def _extraire_date_mouvement(
        ligne: tuple,
        colonne_date: Optional[int],
        libelle: str,
        date_fallback: date,
        periode_limite: Optional[Periode],
    ) -> date:
        # 1. Colonne date explicite
        if colonne_date is not None and colonne_date < len(ligne):
            val = ligne[colonne_date]
            if val not in (None, ""):
                try:
                    d = parse_date(val)
                    if periode_limite is None or periode_limite.contient(d):
                        return d
                except Exception:
                    pass

        # 2. Cellule de date parmi les premières colonnes (avant les montants)
        for val in ligne[:3]:
            if isinstance(val, (datetime, date)):
                d = parse_date(val)
                if periode_limite is None or periode_limite.contient(d):
                    return d
            elif isinstance(val, str):
                m = re.match(r"^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*$", val)
                if m:
                    try:
                        d = parse_date(m.group(1))
                        if periode_limite is None or periode_limite.contient(d):
                            return d
                    except Exception:
                        pass

        # 3. Date dans le libellé si elle est dans la période du journal
        if periode_limite is not None:
            for match in re.finditer(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", libelle):
                try:
                    d = parse_date(match.group(1))
                    if periode_limite.contient(d):
                        return d
                except Exception:
                    pass

        # 4. Fallback vers la section courante ou début de période
        return date_fallback

    def _traiter(
        self,
        numero: int,
        ligne: tuple,
        colonne_om: int,
        libelle: str,
        lot: LotImport,
        colonne_date: Optional[int] = None,
        date_fallback: Optional[date] = None,
        periode_limite: Optional[Periode] = None,
    ) -> None:
        brut = ligne[colonne_om] if colonne_om < len(ligne) else None
        if brut in (None, "", 0):
            return  # ligne réglée par un autre mode : hors périmètre, pas une anomalie

        try:
            montant = parse_amount(brut)
        except AmountParseError as erreur:
            lot.rejeter(numero, f"montant Orange Money illisible ({erreur})")
            return
        if montant == ZERO:
            return

        date_mvt = None
        if date_fallback is not None:
            date_mvt = self._extraire_date_mouvement(
                ligne, colonne_date, libelle, date_fallback, periode_limite
            )

        lot.retenues.append(
            MouvementEncaissement(
                ligne_source=numero,
                libelle=libelle,
                reference=self._reference(libelle),
                montant_om=montant,
                montant_total=normalize_amount(self._total(ligne, colonne_om)),
                est_arrhe=self._est_arrhe(libelle),
                date_mouvement=date_mvt,
            )
        )

    @staticmethod
    def _total(ligne: tuple, colonne_om: int) -> Any:
        """La colonne « Total » précède les colonnes de mode dans les exports observés."""
        for index in range(colonne_om - 1, 0, -1):
            if index < len(ligne) and isinstance(ligne[index], (int, float)):
                return ligne[index]
        return None

    @staticmethod
    def _est_arrhe(libelle: str) -> bool:
        """La nature se lit dans le libellé, pas dans le résultat du rapprochement.

        C'est elle qui déterminera la nature de l'écriture comptable : une arrhe
        donne une ligne individuelle, une facture alimente la recette agrégée.
        """
        cle = normalize_key(libelle)
        return "ARRHES" in cle or bool(_RESERVATION.search(libelle))

    @staticmethod
    def _reference(libelle: str) -> str:
        reservation = _RESERVATION.search(libelle)
        if reservation:
            return reservation.group(1)
        facture = _FACTURE.match(libelle.strip())
        return facture.group(1).upper() if facture else ""

    # --- récapitulatif ---------------------------------------------------------

    @staticmethod
    def _collecter_recapitulatif(
        libelle: str, ligne: tuple, colonne_om: int, recapitulatif: dict
    ) -> None:
        """Retient les totaux que le fichier annonce, pour contrôler la lecture."""
        valeur = ligne[colonne_om] if colonne_om < len(ligne) else None
        if valeur in (None, ""):
            return
        try:
            montant = parse_amount(valeur)
        except AmountParseError:
            return

        cles = [normalize_key(libelle)] + [
            normalize_key(str(c)) for c in ligne if c and isinstance(c, str)
        ]
        for cle in cles:
            if cle.startswith("TOTAL PERIODE"):
                recapitulatif["total"] = montant
                break
            elif cle == "ENCAISSEMENT D'ARRHES":
                recapitulatif["arrhes"] = montant
                break
            elif cle == "ENCAISSEMENT DE FACTURES":
                recapitulatif["factures"] = montant
                break

    # --- période ---------------------------------------------------------------

    def _periode(self, entete: list[tuple]) -> tuple[Periode, bool]:
        for ligne in entete:
            for cellule in ligne:
                trouve = _PERIODE.search(str(cellule)) if cellule else None
                if trouve:
                    return Periode(parse_date(trouve.group(1)), parse_date(trouve.group(2))), False
        raise ValueError(
            f"Période introuvable dans l'en-tête de {self.filepath.name}. "
            "Le journal doit porter sa période : c'est elle qui définit le périmètre."
        )
