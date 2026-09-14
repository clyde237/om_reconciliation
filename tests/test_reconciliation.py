"""Tests des calculs de réconciliation."""

from src.analysis.reconciliation import compute_reconciliation_summary


def test_compute_reconciliation_summary():
    data = {}
    summary = compute_reconciliation_summary(data)
    assert "taux_rapprochement" in summary
    assert "ecart_total" in summary
