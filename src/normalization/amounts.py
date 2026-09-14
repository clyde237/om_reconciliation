"""Standardisation et nettoyage des montants monétaires."""

import re
from typing import Any


def normalize_amount(val: Any) -> float:
    """Convertit une chaîne ou nombre représentant un montant en valeur float positive ou signée."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    s = s.replace("\xa0", "").replace(" ", "")
    s = re.sub(r"[^0-9,.-]", "", s)
    s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return 0.0
