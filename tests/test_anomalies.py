"""Tests de détection des anomalies."""

import pandas as pd
from src.analysis.anomalies import detect_anomalies


def test_detect_anomalies():
    df_om = pd.DataFrame()
    df_arrhes = pd.DataFrame()
    anomalies = detect_anomalies(df_om, df_arrhes)
    assert isinstance(anomalies, pd.DataFrame)
