"""Rapprochement sur égalité de montant dans une tolérance définie."""

import pandas as pd


def match_by_amount(df_om: pd.DataFrame, df_arrhes: pd.DataFrame, tolerance: float = 0.0) -> pd.DataFrame:
    """Identifie les transactions ayant le même montant à une tolérance près."""
    return pd.DataFrame()
