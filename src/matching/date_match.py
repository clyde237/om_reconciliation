"""Filtrage et validation de fenêtres temporelles entre opérations."""

import pandas as pd


def is_within_date_window(date1: pd.Timestamp, date2: pd.Timestamp, max_days: int = 3) -> bool:
    """Vérifie si deux dates se situent dans la fenêtre de tolérance autorisée."""
    if pd.isna(date1) or pd.isna(date2):
        return False
    delta = abs((date1 - date2).days)
    return delta <= max_days
