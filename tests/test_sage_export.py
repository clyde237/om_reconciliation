"""Tests des exports Sage."""

import pandas as pd
from src.sage.mapper import SageMapper


def test_sage_mapper():
    mapper = SageMapper()
    df = pd.DataFrame()
    res = mapper.map_to_sage_schema(df)
    assert "Code_Journal" in res.columns
    assert "N_Compte" in res.columns
