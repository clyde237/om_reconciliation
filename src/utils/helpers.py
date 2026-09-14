"""Fonctions utilitaires diverses."""

import math


def safe_float(val, default: float = 0.0) -> float:
    """Convertit en toute sécurité une valeur en float."""
    try:
        f = float(val)
        return 0.0 if math.isnan(f) else f
    except (ValueError, TypeError):
        return default
