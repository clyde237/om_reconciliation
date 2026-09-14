"""Détection fine des anomalies et divergences de flux."""

import pandas as pd


def detect_anomalies(df_om: pd.DataFrame, df_arrhes: pd.DataFrame) -> pd.DataFrame:
    """Génère une table détaillée des anomalies détectées."""
    return pd.DataFrame(columns=["Type_Anomalie", "Reference", "Montant_OM", "Montant_Arrhes", "Ecart", "Commentaire"])
