"""Tests de normalisation des dates."""

import pandas as pd
from src.normalization.dates import normalize_dates, format_sage_date


def test_normalize_dates():
    s = pd.Series(["14/09/2026", "2026-09-14", "invalid_date"])
    res = normalize_dates(s)
    assert not pd.isna(res[0])
    assert not pd.isna(res[1])
    assert pd.isna(res[2])


def test_format_sage_date():
    ts = pd.Timestamp("2026-09-14")
    assert format_sage_date(ts) == "140926"
    assert format_sage_date(None) == ""
