"""Moteur principal orchestrant les étapes de rapprochement."""

import pandas as pd
from config.matching_config import MatchingConfig, DEFAULT_MATCHING_CONFIG
from .exact_match import match_exact
from .fuzzy_match import match_fuzzy
from .duplicate_detector import detect_duplicates


class ReconciliationMatcher:
    """Coordonne les différentes passes de réconciliation (exacte, floue, montants)."""

    def __init__(self, config: MatchingConfig = DEFAULT_MATCHING_CONFIG):
        self.config = config

    def run(self, df_om: pd.DataFrame, df_arrhes: pd.DataFrame) -> dict:
        """Exécute le workflow complet de réconciliation."""
        duplicates_om = detect_duplicates(df_om, subset_cols=["Reference"])
        duplicates_arrhes = detect_duplicates(df_arrhes, subset_cols=["Reference"])

        exact_matches, remaining_om, remaining_arrhes = match_exact(df_om, df_arrhes)
        fuzzy_matches, unmatched_om, unmatched_arrhes = match_fuzzy(
            remaining_om, remaining_arrhes, threshold=self.config.fuzzy_similarity_threshold
        )

        return {
            "exact_matches": exact_matches,
            "fuzzy_matches": fuzzy_matches,
            "unmatched_om": unmatched_om,
            "unmatched_arrhes": unmatched_arrhes,
            "duplicates_om": duplicates_om,
            "duplicates_arrhes": duplicates_arrhes,
        }
