"""Détection fine des anomalies et divergences de flux.

Une anomalie est une opération qui nécessite une revue ou qui bloque l'export comptable :
- Écart de montant (journal ≠ OM)
- Arrhe non retrouvée dans le relevé OM (MANQUANT_OM)
- Encaissement orphelin requalifié (MANQUANT_JOURNAL)
- Transaction en échec ou service invalide (STATUT_OM_INVALIDE)
- Cas non résolu ou correspondance douteuse (A_CONTROLER)
"""

from typing import Sequence, Union

from config.matching_config import BLOCKING_STATUSES, MatchStatus
from src.analysis.reconciliation import LigneRapprochement, construire_table
from src.matching.appariement import ResultatRapprochement

STATUTS_ANOMALIES = set(BLOCKING_STATUSES) | {
    MatchStatus.STATUT_OM_INVALIDE,
    MatchStatus.ECART_MONTANT,
    MatchStatus.A_CONTROLER,
}


def extraire_anomalies(
    source: Union[ResultatRapprochement, Sequence[LigneRapprochement]],
) -> list[LigneRapprochement]:
    """Extrait toutes les lignes d'anomalies à partir d'un résultat de rapprochement ou d'une table."""
    table = construire_table(source) if isinstance(source, ResultatRapprochement) else list(source)
    return [ligne for ligne in table if ligne.statut in STATUTS_ANOMALIES or ligne.est_bloquante]


def detect_anomalies(
    source: Union[ResultatRapprochement, Sequence[LigneRapprochement]],
) -> list[LigneRapprochement]:
    """Alias rétro-compatible pour extraire_anomalies."""
    return extraire_anomalies(source)
