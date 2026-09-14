"""Normalisation des identifiants et références de transactions."""

import re


def normalize_reference(ref: str) -> str:
    """Nettoie une référence (suppression espaces, mise en majuscules, retrait de préfixes)."""
    if not ref or not isinstance(ref, str):
        return ""
    cleaned = ref.strip().upper()
    cleaned = re.sub(r"[^A-Z0-9_-]", "", cleaned)
    return cleaned
