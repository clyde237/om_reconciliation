"""Identification des opérations orphelines (manquantes)."""

import pandas as pd


def find_missing_in_arrhes(unmatched_om: pd.DataFrame) -> pd.DataFrame:
    """Retourne les encaissements Orange Money absents du journal comptable des arrhes."""
    return unmatched_om


def find_missing_in_om(unmatched_arrhes: pd.DataFrame) -> pd.DataFrame:
    """Retourne les écritures d'arrhes non retrouvées dans le relevé Orange Money."""
    return unmatched_arrhes
