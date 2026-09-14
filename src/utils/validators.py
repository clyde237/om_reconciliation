"""Validateurs de structure et contenu des DataFrames."""

from typing import List
import pandas as pd


def validate_columns(df: pd.DataFrame, expected_columns: List[str]) -> bool:
    """Vérifie la présence de toutes les colonnes obligatoires dans un DataFrame."""
    missing = [col for col in expected_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes obligatoires manquantes: {missing}")
    return True
