"""Normalisation des identifiants et références de transactions."""

import re
from typing import Any

from .text import to_ascii

#: Caractères conservés dans une référence. Le point en fait partie : les références
#: Orange Money sont de la forme ``MP260416.1311.A17517``, le retirer les mutilerait.
_NON_REFERENCE = re.compile(r"[^A-Z0-9._\-/]")

#: Indicatif pays du Cameroun, présent ou non selon les exports.
INDICATIF_CAMEROUN = "237"

#: Longueur d'un numéro camerounais sans indicatif.
LONGUEUR_MSISDN = 9


def normalize_reference(value: Any) -> str:
    """Ramène une référence à sa forme comparable : majuscules, sans espace ni parasite."""
    if value is None:
        return ""
    texte = to_ascii(value).upper().replace(" ", "")
    return _NON_REFERENCE.sub("", texte)


def normalize_msisdn(value: Any) -> str:
    """Ramène un numéro de téléphone à ses neuf chiffres nationaux.

    Le relevé Orange Money identifie le correspondant par son numéro ; selon les
    exports il est préfixé ou non de l'indicatif. ``+237 694 697 652``,
    ``237694697652`` et ``694697652`` doivent produire la même clé.
    """
    if value is None:
        return ""
    chiffres = re.sub(r"\D", "", str(value))
    if (
        len(chiffres) == LONGUEUR_MSISDN + len(INDICATIF_CAMEROUN)
        and chiffres.startswith(INDICATIF_CAMEROUN)
    ):
        chiffres = chiffres[len(INDICATIF_CAMEROUN):]
    return chiffres


def extract_reference_om(value: Any) -> str:
    """Isole une référence Orange Money dans un texte libre.

    Les références du relevé suivent ``<2 lettres><AAMMJJ>.<HHMM>.<6 alphanum>``.
    Renvoie une chaîne vide si le texte n'en contient aucune — ce qui est le cas de
    toutes les colonnes du journal des arrhes, lequel n'en porte aucune.
    """
    if value is None:
        return ""
    trouve = re.search(r"\b[A-Z]{2}\d{6}\.\d{4}\.[A-Z0-9]{6}\b", to_ascii(value).upper())
    return trouve.group(0) if trouve else ""
