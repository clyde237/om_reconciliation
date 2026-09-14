"""Standardisation des formats de dates."""

from typing import Optional
import pandas as pd


def normalize_dates(series: pd.Series, dayfirst: bool = True) -> pd.Series:
    """Convertit une série de dates diverses en format datetime standardisé."""
    return pd.to_datetime(series, dayfirst=dayfirst, errors="coerce")


def format_sage_date(dt: Optional[pd.Timestamp]) -> str:
    """Formate un timestamp en format Sage (ex: JJMMAA)."""
    if pd.isna(dt) or dt is None:
        return ""
    return dt.strftime("%d%m%y")
