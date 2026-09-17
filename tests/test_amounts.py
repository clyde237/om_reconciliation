"""Tests de normalisation des montants (cahier des charges §5)."""

from decimal import Decimal

import pytest

from src.normalization.amounts import (
    SEPARATEUR_MILLIERS as ESP,
    AmountParseError,
    format_amount,
    normalize_amount,
    parse_amount,
)


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [
        # Les cinq écritures citées au §5.
        ("90 200", "90200"),
        ("90.200", "90200"),
        ("90200", "90200"),
        ("90 200,00", "90200.00"),
        ("90 200 FCFA", "90200"),
        # Espace insécable : le journal des arrhes écrit « 90 200 FCFA » ainsi.
        ("90\xa0200 FCFA", "90200"),
        ("90 200", "90200"),
        # Notation mixte : le dernier séparateur est le séparateur décimal.
        ("15.500,50", "15500.50"),
        ("15,500.50", "15500.50"),
        # Décimales réelles du relevé Orange Money.
        ("1827509.84", "1827509.84"),
        ("-113496.92", "-113496.92"),
        ("2372466.81", "2372466.81"),
        # Milliers répétés.
        ("1.234.567", "1234567"),
        ("1 234 567", "1234567"),
        # Conventions comptables.
        ("(1 000)", "-1000"),
        ("- 1 000", "-1000"),
        ("+90200", "90200"),
    ],
)
def test_formats_acceptes(brut, attendu):
    assert parse_amount(brut) == Decimal(attendu)


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [(1000, "1000"), (0, "0"), (-250, "-250"), (Decimal("7.5"), "7.5")],
)
def test_valeurs_numeriques(brut, attendu):
    assert parse_amount(brut) == Decimal(attendu)


def test_un_float_ne_traine_pas_son_bruit_binaire():
    """Decimal(0.1) vaudrait 0.1000000000000000055…, ce qui fausserait un total."""
    assert parse_amount(0.1) == Decimal("0.1")
    assert parse_amount(90200.5) == Decimal("90200.5")


def test_le_resultat_est_toujours_un_decimal():
    """Le §5 l'impose : aucun flottant sur un chemin monétaire."""
    assert isinstance(parse_amount("90 200"), Decimal)
    assert isinstance(normalize_amount("illisible"), Decimal)


@pytest.mark.parametrize("brut", [None, "", "   ", "FCFA", "abc", True])
def test_valeurs_inexploitables(brut):
    with pytest.raises(AmountParseError):
        parse_amount(brut)


def test_normalize_amount_est_tolerant():
    """Variante pour les colonnes facultatives : pas d'exception, une valeur par défaut."""
    assert normalize_amount(None) == 0
    assert normalize_amount("abc") == 0
    assert normalize_amount("abc", default=Decimal("-1")) == Decimal("-1")
    assert normalize_amount("90 200") == Decimal("90200")


def test_somme_exacte_sur_les_montants_reels():
    """Les trois arrhes Orange Money du 16/04/2026 totalisent bien 290 600."""
    lignes = ["90 200", "110 200", "90 200"]
    assert sum((parse_amount(m) for m in lignes), Decimal(0)) == Decimal("290600")


def test_format_amount():
    assert format_amount(Decimal("90200")) == f"90{ESP}200"
    assert format_amount(Decimal("1827509.84"), decimals=2) == f"1{ESP}827{ESP}509,84"
    assert format_amount(Decimal("-1000")) == f"-1{ESP}000"
