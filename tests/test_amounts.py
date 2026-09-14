"""Tests de normalisation des montants."""

from src.normalization.amounts import normalize_amount


def test_normalize_amount_simple():
    assert normalize_amount(1000) == 1000.0
    assert normalize_amount("1000") == 1000.0


def test_normalize_amount_formatted():
    assert normalize_amount("10 000 FCFA") == 10000.0
    assert normalize_amount("15.500,50") == 15500.50
    assert normalize_amount(None) == 0.0
