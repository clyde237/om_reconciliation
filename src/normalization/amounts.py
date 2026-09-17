"""Standardisation et nettoyage des montants monétaires.

Tous les montants du projet transitent par ce module et en ressortent en ``Decimal``.
Le cahier des charges (§5) l'impose : un rapprochement comptable ne tolère pas les
erreurs de représentation du binaire flottant.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

#: Espaces que les exports Excel glissent dans les montants — le journal des arrhes
#: écrit « 90 200 FCFA » avec une espace insécable.
_ESPACES = "     \t"

#: Tout ce qui n'est ni chiffre, ni séparateur, ni signe : devises, symboles, lettres.
_PARASITES = re.compile(r"[^0-9,.\-+]")

ZERO = Decimal("0")

#: Séparateur de milliers à l'affichage : espace insécable, comme dans les sources.
SEPARATEUR_MILLIERS = "\u00a0"


class AmountParseError(ValueError):
    """Le texte fourni ne représente pas un montant exploitable."""


def parse_amount(value: Any) -> Decimal:
    """Convertit une valeur en ``Decimal``, ou lève ``AmountParseError``.

    À utiliser sur les colonnes obligatoires : une donnée illisible doit remonter
    comme un rejet d'import, pas se transformer silencieusement en zéro.

    Formats acceptés (§5) : ``90 200``, ``90.200``, ``90200``, ``90 200,00``,
    ``90 200 FCFA``, ainsi que les négatifs entre parenthèses ``(1 000)``.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise AmountParseError(f"booléen inexploitable comme montant : {value!r}")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # repr() du float pour éviter d'hériter du bruit binaire : Decimal(0.1)
        # vaut 0.1000000000000000055511151231257827021181583404541015625.
        return Decimal(repr(value))

    if value is None:
        raise AmountParseError("montant absent")

    texte = str(value)
    for espace in _ESPACES:
        texte = texte.replace(espace, "")
    texte = texte.strip()
    if not texte:
        raise AmountParseError("montant vide")

    # Comptabilité : un montant entre parenthèses est négatif.
    negatif = texte.startswith("(") and texte.endswith(")")
    if negatif:
        texte = texte[1:-1]

    texte = _PARASITES.sub("", texte)
    if texte.startswith("-"):
        negatif = not negatif
    texte = texte.lstrip("+-")
    if not texte:
        raise AmountParseError(f"aucun chiffre dans {value!r}")

    texte = _reduire_separateurs(texte, value)

    try:
        montant = Decimal(texte)
    except InvalidOperation as err:
        raise AmountParseError(f"montant illisible : {value!r}") from err

    return -montant if negatif else montant


def _reduire_separateurs(texte: str, origine: Any) -> str:
    """Ramène un nombre à la notation ``1234.56``, séparateurs de milliers retirés.

    Deux règles, dans l'ordre :

    1. si les deux séparateurs sont présents, **le dernier est le séparateur décimal**
       (``15.500,50`` vaut 15500,50 et ``15,500.50`` vaut la même chose) ;
    2. s'il n'y en a qu'un, il n'est décimal que s'il n'est pas suivi d'exactement trois
       chiffres — c'est ce qui distingue ``90.200`` (90 200 FCFA) de ``1827509.84``.
    """
    virgules = texte.count(",")
    points = texte.count(".")

    if virgules and points:
        decimal_sep = "," if texte.rindex(",") > texte.rindex(".") else "."
    elif virgules or points:
        sep = "," if virgules else "."
        if texte.count(sep) > 1:
            decimal_sep = ""  # répété : ce sont des séparateurs de milliers
        else:
            avant, _, apres = texte.partition(sep)
            groupe_de_milliers = len(apres) == 3 and avant.isdigit()
            decimal_sep = "" if groupe_de_milliers else sep
    else:
        return texte

    for sep in (",", "."):
        if sep != decimal_sep:
            texte = texte.replace(sep, "")
    if decimal_sep and decimal_sep != ".":
        texte = texte.replace(decimal_sep, ".")

    if texte.count(".") > 1:
        raise AmountParseError(f"montant ambigu : {origine!r}")
    return texte


def normalize_amount(value: Any, default: Decimal = ZERO) -> Decimal:
    """Variante tolérante de :func:`parse_amount` : renvoie ``default`` si illisible.

    Réservée aux colonnes facultatives. Sur une colonne obligatoire, préférer
    :func:`parse_amount` pour que la donnée fautive apparaisse dans le rapport d'import.
    """
    try:
        return parse_amount(value)
    except AmountParseError:
        return default


def format_amount(montant: Decimal, decimals: int = 0) -> str:
    """Formate un montant pour l'affichage, milliers séparés par une espace insécable."""
    quantifie = round(montant, decimals)
    entier, _, decimale = f"{abs(quantifie):.{decimals}f}".partition(".")
    groupes = f"{int(entier):,}".replace(",", SEPARATEUR_MILLIERS)
    signe = "-" if quantifie < 0 else ""
    return f"{signe}{groupes},{decimale}" if decimals else f"{signe}{groupes}"
