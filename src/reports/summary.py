"""Création des tableaux de synthèse pour reporting financier."""

import pandas as pd


def build_summary_table(metrics: dict) -> pd.DataFrame:
    """Construit un tableau récapitulatif formaté des métriques financières."""
    return pd.DataFrame(list(metrics.items()), columns=["Indicateur", "Valeur"])
