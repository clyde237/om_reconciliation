"""Nettoyage et standardisation des libellés et chaînes de caractères."""

import re
import unicodedata
from typing import Any

#: Espaces exotiques produits par les exports Excel et les copier-coller.
_ESPACES = re.compile(r"[\s\xa0  ]+")

#: Caractères de contrôle, sauf ceux que ``_ESPACES`` traite déjà.
_CONTROLES = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

#: Remplacements typographiques sans équivalent ASCII par décomposition.
_EQUIVALENTS_ASCII = {
    "œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE",
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "€": "EUR", "°": "o",
}


def clean_text(value: Any) -> str:
    """Normalise les espaces et retire les caractères de contrôle.

    La casse et les accents sont **conservés** : cette fonction sert à produire des
    libellés lisibles. Pour comparer deux chaînes, utiliser :func:`normalize_key` ;
    pour un export PNM, :func:`to_ascii`.
    """
    if value is None:
        return ""
    texte = _CONTROLES.sub(" ", str(value))
    return _ESPACES.sub(" ", texte).strip()


def to_ascii(value: Any) -> str:
    """Réduit une chaîne à l'ASCII imprimable, comme l'exige le format PNM.

    Les quatre échantillons Sage ne contiennent aucun octet au-delà de 127 : ils
    écrivent « Achats matieres », jamais « Achats matières ». Un accent laissé dans
    un libellé ferait échouer l'import.
    """
    texte = clean_text(value)
    for source, cible in _EQUIVALENTS_ASCII.items():
        texte = texte.replace(source, cible)
    decompose = unicodedata.normalize("NFKD", texte)
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return "".join(c for c in sans_accents if 32 <= ord(c) < 127)


def normalize_key(value: Any) -> str:
    """Forme canonique d'une chaîne destinée à être comparée.

    Sans accents, en majuscules, espaces réduits : deux libellés qui ne diffèrent que
    par leur typographie produisent la même clé.
    """
    return to_ascii(value).upper()


def truncate(value: Any, longueur: int, marqueur: str = "") -> str:
    """Tronque à ``longueur`` caractères, sans jamais le faire silencieusement.

    L'appelant reste responsable de tracer la troncature : comparer le résultat à
    l'entrée suffit à la détecter.
    """
    texte = clean_text(value)
    if len(texte) <= longueur:
        return texte
    if marqueur and longueur > len(marqueur):
        return texte[: longueur - len(marqueur)].rstrip() + marqueur
    return texte[:longueur].rstrip()
