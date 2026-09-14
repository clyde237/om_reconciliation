"""Détection des transactions dupliquées."""

from typing import List
import pandas as pd


def detect_duplicates(df: pd.DataFrame, subset_cols: List[str]) -> pd.DataFrame:
    """Détecte les doublons selon un ensemble de colonnes clés (ex: référence, montant, date)."""
    if df.empty:
        return pd.DataFrame()
    existing_cols = [c for c in subset_cols if c in df.columns]
    if not existing_cols:
        return pd.DataFrame()
    return df[df.duplicated(subset=existing_cols, keep=False)]
