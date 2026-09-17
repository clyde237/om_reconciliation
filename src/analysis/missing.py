"""Identification des opérations orphelines et manquants.

Deux natures de manquants :
1. Manquants OM : arrhes du journal sans aucun flux Orange Money correspondant (défaillance
   d'encaissement ou mauvaise imputation de mode de paiement).
2. Manquants Journal : transactions OM sans écriture comptable dans le journal des arrhes
   (recettes non enregistrées ou arrhes oubliées par la réception).
"""

from typing import Sequence, Union

from config.matching_config import MatchStatus
from src.analysis.reconciliation import LigneRapprochement, construire_table
from src.matching.appariement import ResultatRapprochement


def extraire_manquants_om(
    source: Union[ResultatRapprochement, Sequence[LigneRapprochement]],
) -> list[LigneRapprochement]:
    """Retourne les arrhes du journal introuvables sur le relevé Orange Money."""
    table = construire_table(source) if isinstance(source, ResultatRapprochement) else list(source)
    return [ligne for ligne in table if ligne.statut is MatchStatus.MANQUANT_OM]


def extraire_manquants_journal(
    source: Union[ResultatRapprochement, Sequence[LigneRapprochement]],
) -> list[LigneRapprochement]:
    """Retourne les flux Orange Money sans écriture d'arrhe au journal."""
    table = construire_table(source) if isinstance(source, ResultatRapprochement) else list(source)
    return [ligne for ligne in table if ligne.statut is MatchStatus.MANQUANT_JOURNAL]
