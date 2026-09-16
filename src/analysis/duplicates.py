"""Analyse approfondie et extraction des doublons de transactions.

Un doublon peut survenir :
- Côté Journal : même client, même montant, même jour saisi à double.
- Côté Orange Money : encaissement dédoublé avec deux références de transaction distinctes.
"""

from dataclasses import dataclass
from typing import Optional

from src.matching.appariement import ResultatRapprochement
from src.models import LigneJournal, TransactionOM


@dataclass(frozen=True)
class RapportDoublons:
    """Ensemble des doublons détectés pour une période."""

    doublons_journal: list[LigneJournal]
    doublons_om: list[TransactionOM]

    @property
    def a_des_doublons(self) -> bool:
        return bool(self.doublons_journal or self.doublons_om)

    @property
    def total_occurrences(self) -> int:
        return len(self.doublons_journal) + len(self.doublons_om)


def extraire_doublons(resultat: ResultatRapprochement) -> RapportDoublons:
    """Extrait les doublons identifiés côté journal et côté relevé OM."""
    return RapportDoublons(
        doublons_journal=list(resultat.doublons_journal),
        doublons_om=list(resultat.doublons_om),
    )
