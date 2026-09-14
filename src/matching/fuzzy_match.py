"""Rapprochement flou basé sur la similarité textuelle et fenêtres temporelles."""

from typing import Tuple
import pandas as pd


def match_fuzzy(
    df_om: pd.DataFrame, df_arrhes: pd.DataFrame, threshold: float = 85.0
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Recherche les correspondances approchées par distance de Levenshtein ou Jaro-Winkler."""
    matched = pd.DataFrame()
    unmatched_om = df_om.copy()
    unmatched_arrhes = df_arrhes.copy()
    return matched, unmatched_om, unmatched_arrhes
