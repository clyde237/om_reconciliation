"""Lecteur du journal des arrhes.

L'export n'est pas une table : une cellule d'en-tête porte la société et la période,
la table démarre en deuxième ligne, et elle est suivie de sous-totaux, d'une note de
bas de page, d'une pagination et d'un bloc « Récapitulatif ». Tout cela doit être
écarté, et chaque ligne écartée justifiée.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from openpyxl import load_workbook

from config.settings import JOURNAL_COLUMN_ALIASES
from src.models import LigneJournal, LotImport, Periode
from src.normalization.amounts import AmountParseError, ZERO, parse_amount
from src.normalization.dates import DateParseError, parse_date, parse_datetime
from src.normalization.text import clean_text, normalize_key

#: « Période du 16/04/2026 au 16/04/2026 », dans le bloc d'en-tête.
_PERIODE = re.compile(
    r"P[ée]riode\s+du\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+au\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)

#: « Réservation N°8207 », en deuxième ligne de la colonne compte.
_RESERVATION = re.compile(r"R[ée]servation\s+N[°o]\s*(\d+)", re.IGNORECASE)

#: Lignes de pied de table, reconnues à leur libellé.
_MOTIFS_REJET = (
    ("SOUS-TOTAL", "sous-total"),
    ("TOTAL", "ligne de total"),
    ("RECAPITULATIF", "bloc Récapitulatif"),
    ("SOLDE AU", "bloc Récapitulatif"),
    ("LES LIGNES DE DETAIL", "note de bas de page"),
)

#: Nombre de lignes explorées pour trouver l'en-tête de la table.
PROFONDEUR_ENTETE = 10


@dataclass
class LectureJournal:
    """Résultat de la lecture : la période contrôlée et les lignes retenues."""

    periode: Periode
    lot: LotImport = field(default_factory=LotImport)
    periode_deduite: bool = False

    @property
    def lignes(self) -> list[LigneJournal]:
        return self.lot.retenues

    @property
    def lignes_orange_money(self) -> list[LigneJournal]:
        """Le périmètre du rapprochement : la colonne « Encaissement » fait le tri."""
        return [ligne for ligne in self.lignes if ligne.est_orange_money]

    @property
    def total_orange_money(self):
        return sum((ligne.montant for ligne in self.lignes_orange_money), ZERO)


class JournalReader:
    """Charge le journal des arrhes et en extrait la période et les encaissements."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        self._dans_recapitulatif = False

    def read(self) -> LectureJournal:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable : {self.filepath}")

        classeur = load_workbook(self.filepath, read_only=True, data_only=True)
        try:
            feuille = classeur[classeur.sheetnames[0]]
            lignes = [tuple(ligne) for ligne in feuille.iter_rows(values_only=True)]
        finally:
            classeur.close()

        rang_entete, colonnes = self._trouver_entete(lignes)
        lot = LotImport()
        self._dans_recapitulatif = False
        for numero, ligne in enumerate(lignes[rang_entete + 1:], start=rang_entete + 2):
            self._traiter(numero, ligne, colonnes, lot)

        periode, deduite = self._periode(lignes[:rang_entete], lot)
        return LectureJournal(periode=periode, lot=lot, periode_deduite=deduite)

    # --- en-tête ---------------------------------------------------------------

    def _trouver_entete(self, lignes: list[tuple]) -> tuple[int, dict[str, int]]:
        """Localise la ligne d'en-tête et associe chaque alias à son index de colonne."""
        for rang, ligne in enumerate(lignes[:PROFONDEUR_ENTETE]):
            colonnes = self._mapper(ligne)
            if "date" in colonnes and "montant" in colonnes:
                return rang, colonnes
        raise ValueError(
            f"En-tête introuvable dans les {PROFONDEUR_ENTETE} premières lignes "
            f"de {self.filepath.name} : ni colonne date ni colonne montant reconnues."
        )

    @staticmethod
    def _mapper(ligne: Iterable[Any]) -> dict[str, int]:
        colonnes: dict[str, int] = {}
        for index, cellule in enumerate(ligne):
            cle = normalize_key(cellule)
            if not cle:
                continue
            for champ, alias in JOURNAL_COLUMN_ALIASES.items():
                if champ not in colonnes and cle in alias:
                    colonnes[champ] = index
        return colonnes

    # --- lignes ----------------------------------------------------------------

    def _traiter(
        self, numero: int, ligne: tuple, colonnes: dict[str, int], lot: LotImport
    ) -> None:
        if not any(cellule not in (None, "") for cellule in ligne):
            return  # ligne vide : ni retenue, ni signalée

        brut_date = self._cellule(ligne, colonnes, "date")
        try:
            date_operation = parse_datetime(brut_date)
        except DateParseError:
            lot.rejeter(numero, self._motif(ligne, colonnes))
            return

        try:
            montant = parse_amount(self._cellule(ligne, colonnes, "montant"))
        except AmountParseError as err:
            lot.rejeter(numero, f"montant illisible ({err})")
            return

        compte = clean_text(self._cellule(ligne, colonnes, "compte"))
        lot.retenues.append(
            LigneJournal(
                ligne_source=numero,
                date_operation=date_operation,
                client=self._client(compte),
                mode_paiement=clean_text(self._cellule(ligne, colonnes, "mode_paiement")),
                montant=montant,
                reference_interne=self._reservation(compte),
                libelle=clean_text(self._cellule(ligne, colonnes, "reintegration")),
                montant_reintegre=self._montant_optionnel(ligne, colonnes, "montant_reintegre"),
            )
        )

    @staticmethod
    def _cellule(ligne: tuple, colonnes: dict[str, int], champ: str) -> Any:
        index = colonnes.get(champ)
        if index is None or index >= len(ligne):
            return None
        return ligne[index]

    def _montant_optionnel(self, ligne: tuple, colonnes: dict[str, int], champ: str):
        from src.normalization.amounts import normalize_amount

        return normalize_amount(self._cellule(ligne, colonnes, champ))

    @staticmethod
    def _client(compte: str) -> str:
        """La colonne compte est multi-ligne : le nom du client en occupe la première."""
        return compte.split("Réservation")[0].strip(" -–") if compte else ""

    @staticmethod
    def _reservation(compte: str) -> str:
        trouve = _RESERVATION.search(compte or "")
        return trouve.group(1) if trouve else ""

    def _motif(self, ligne: tuple, colonnes: dict[str, int]) -> str:
        """Nomme la raison du rejet, pour que le rapport d'import soit lisible."""
        texte = normalize_key(self._cellule(ligne, colonnes, "date") or "")
        if not texte:
            texte = normalize_key(next((c for c in ligne if c not in (None, "")), ""))
        for marqueur, motif in _MOTIFS_REJET:
            if marqueur in texte:
                if motif == "bloc Récapitulatif":
                    self._dans_recapitulatif = True
                return motif
        if re.fullmatch(r"\d+\s*/\s*\d+", texte):
            return "pagination"
        # Une fois le récapitulatif entamé, tout ce qui suit lui appartient : le
        # nommer ligne par ligne produirait un rapport d'import illisible.
        if self._dans_recapitulatif:
            return "bloc Récapitulatif"
        return f"date illisible ({texte[:40]})" if texte else "ligne hors table"

    # --- période ---------------------------------------------------------------

    def _periode(self, entete: list[tuple], lot: LotImport) -> tuple[Periode, bool]:
        """La période se lit dans l'en-tête ; elle fait foi et définit le périmètre."""
        for ligne in entete:
            for cellule in ligne:
                trouve = _PERIODE.search(str(cellule)) if cellule else None
                if trouve:
                    return Periode(parse_date(trouve.group(1)), parse_date(trouve.group(2))), False

        if not lot.retenues:
            raise ValueError(
                f"Période introuvable dans l'en-tête de {self.filepath.name} "
                "et aucune ligne datée pour la déduire."
            )
        jours = [ligne.jour for ligne in lot.retenues]
        return Periode(min(jours), max(jours)), True
