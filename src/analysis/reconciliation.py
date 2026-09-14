"""Calcul des métriques globales de rapprochement."""

import pandas as pd


def compute_reconciliation_summary(reconciliation_data: dict) -> dict:
    """Calcule le taux de couverture, volume rapproché, montant total OM vs Arrhes."""
    return {
        "taux_rapprochement": 0.0,
        "total_om": 0.0,
        "total_arrhes": 0.0,
        "ecart_total": 0.0,
        "nb_exact": 0,
        "nb_fuzzy": 0,
        "nb_anomalies": 0,
    }
