"""Paramètres et seuils pour les algorithmes de rapprochement."""

from dataclasses import dataclass
from enum import Enum


class MatchStatus(str, Enum):
    """Les neuf statuts métier du rapprochement (cahier des charges §6)."""

    CONFORME = "CONFORME"
    ECART_MONTANT = "ECART_MONTANT"
    MANQUANT_OM = "MANQUANT_OM"
    MANQUANT_JOURNAL = "MANQUANT_JOURNAL"
    DOUBLON = "DOUBLON"
    CORRESPONDANCE_PROBABLE = "CORRESPONDANCE_PROBABLE"
    CORRESPONDANCE_GROUPEE = "CORRESPONDANCE_GROUPEE"
    STATUT_OM_INVALIDE = "STATUT_OM_INVALIDE"
    A_CONTROLER = "A_CONTROLER"


#: Statuts qui bloquent l'export Sage tant qu'ils ne sont pas validés manuellement.
#: Arbitrage du 15/09/2026 : écart de montant, manquants (des deux côtés), à contrôler.
BLOCKING_STATUSES: frozenset[MatchStatus] = frozenset({
    MatchStatus.ECART_MONTANT,
    MatchStatus.MANQUANT_OM,
    MatchStatus.MANQUANT_JOURNAL,
    MatchStatus.A_CONTROLER,
})


class MatchLevel(int, Enum):
    """Niveaux de la cascade de rapprochement (§4), du plus sûr au plus faible."""

    REFERENCE_MONTANT = 1
    DATE_MONTANT = 2
    DATE_MONTANT_CLIENT = 3
    MONTANT_DATE_TOLERANCE = 4
    COMBINAISON_LIGNES = 5


#: Niveaux au-delà desquels une correspondance est soumise à validation humaine.
PROBABLE_FROM_LEVEL = MatchLevel.DATE_MONTANT_CLIENT


@dataclass(frozen=True)
class MatchingConfig:
    tolerance_days: int = 3
    amount_tolerance: float = 0.0
    fuzzy_similarity_threshold: float = 85.0
    auto_validate_exact: bool = True
    consider_fees: bool = True
    #: Nombre maximal de lignes du journal regroupées sur une seule opération OM (niveau 5).
    max_group_size: int = 3


DEFAULT_MATCHING_CONFIG = MatchingConfig()
