"""Paramètres et seuils pour les algorithmes de rapprochement."""

from dataclasses import dataclass
from enum import Enum


class MatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    FUZZY_MATCH = "FUZZY_MATCH"
    AMOUNT_ONLY = "AMOUNT_ONLY"
    UNMATCHED_OM = "UNMATCHED_OM"
    UNMATCHED_ARRHES = "UNMATCHED_ARRHES"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class MatchingConfig:
    tolerance_days: int = 3
    amount_tolerance: float = 0.0
    fuzzy_similarity_threshold: float = 85.0
    auto_validate_exact: bool = True
    consider_fees: bool = True


DEFAULT_MATCHING_CONFIG = MatchingConfig()
