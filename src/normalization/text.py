"""Nettoyage et standardisation des libellés et chaînes de caractères."""

import unicodedata
import re


def clean_text(text: str) -> str:
    """Supprime les accents, caractères de contrôle et espaces superflus."""
    if not text or not isinstance(text, str):
        return ""

    nfkd_form = unicodedata.normalize("NFKD", text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    cleaned = re.sub(r"\s+", " ", only_ascii).strip().upper()
    return cleaned
