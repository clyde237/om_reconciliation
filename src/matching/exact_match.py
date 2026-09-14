"""Rapprochement exact sur référence et montant."""

from typing import Tuple
import pandas as pd


def match_exact(df_om: pd.DataFrame, df_arrhes: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Recherche les correspondances 100% identiques sur la référence et le montant."""
    # Squelette de matching exact
    matched = pd.DataFrame()
    remaining_om = df_om.copy()
    remaining_arrhes = df_arrhes.copy()
    return matched, remaining_om, remaining_arrhes
