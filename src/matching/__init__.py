"""Moteur de rapprochement."""

from .appariement import Appariement, ResultatRapprochement
from .duplicate_detector import doublons_journal, doublons_om
from .matcher import ReconciliationMatcher

__all__ = [
    "Appariement",
    "ReconciliationMatcher",
    "ResultatRapprochement",
    "doublons_journal",
    "doublons_om",
]
