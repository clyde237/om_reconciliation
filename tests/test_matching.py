"""Tests du moteur de matching."""

import pandas as pd
from src.matching.matcher import ReconciliationMatcher


def test_matcher_init():
    matcher = ReconciliationMatcher()
    df_om = pd.DataFrame()
    df_arrhes = pd.DataFrame()
    results = matcher.run(df_om, df_arrhes)
    assert "exact_matches" in results
    assert "fuzzy_matches" in results
