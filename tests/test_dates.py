"""Tests de normalisation des dates (cahier des charges §5)."""

from datetime import date, datetime

import pandas as pd
import pytest

from src.normalization.dates import (
    DateParseError,
    format_sage_date,
    normalize_date,
    normalize_dates,
    parse_date,
    parse_datetime,
)

JOUR = date(2026, 4, 16)


@pytest.mark.parametrize(
    "brut",
    [
        "16/04/2026",   # les quatre écritures citées au §5
        "16-04-2026",
        "16/04/26",
        "2026-04-16",
        "16.04.2026",
        " 16/04/2026 ",
        datetime(2026, 4, 16, 13, 16),
        date(2026, 4, 16),
        pd.Timestamp("2026-04-16"),
    ],
)
def test_formats_acceptes(brut):
    assert parse_date(brut) == JOUR


def test_serial_excel_du_journal_des_arrhes():
    """Le journal stocke ses dates en sérial Excel avec l'heure de saisie.

    Valeur relevée dans le fichier réel : 46128.552777777775 pour le 16/04/2026.
    """
    assert parse_datetime(46128.552777777775) == datetime(2026, 4, 16, 13, 16)
    assert parse_date(46128.552777777775) == JOUR
    assert parse_date(46128) == JOUR


def test_serial_excel_du_grand_livre_sage():
    """Recoupement sur une seconde source : 46121 = 09/04/2026 dans OM SAGE.xlsx."""
    assert parse_date(46121) == date(2026, 4, 9)


def test_horodatage_du_releve_om():
    assert parse_datetime("01/05/2026 11:56:34") == datetime(2026, 5, 1, 11, 56, 34)


def test_pivot_de_siecle():
    """26 vaut 2026, 85 vaut 1985 : le pivot est explicite, pas hérité de la locale."""
    assert parse_date("16/04/26") == JOUR
    assert parse_date("16/04/85") == date(1985, 4, 16)


def test_un_millesime_seul_n_est_pas_un_serial():
    """Sans fenêtre de plausibilité, 2026 serait lu comme une date de 1905."""
    with pytest.raises(DateParseError):
        parse_date(2026)


@pytest.mark.parametrize("brut", [None, "", "   ", "invalid_date", "32/13/2026", True])
def test_valeurs_inexploitables(brut):
    with pytest.raises(DateParseError):
        parse_date(brut)


def test_normalize_date_est_tolerant():
    assert normalize_date("invalid_date") is None
    assert normalize_date("invalid_date", default=JOUR) == JOUR
    assert normalize_date("16/04/2026") == JOUR


def test_normalize_dates_melange_les_formats():
    """Une même colonne mélange sérials, textes et cellules vides."""
    serie = normalize_dates(pd.Series(["14/09/2026", "2026-09-14", "invalid_date", 46128.55, None]))
    assert serie[0] == pd.Timestamp("2026-09-14")
    assert serie[1] == pd.Timestamp("2026-09-14")
    assert pd.isna(serie[2])
    assert serie[3].date() == JOUR
    assert pd.isna(serie[4])


def test_format_sage_date():
    """JJMMAA, format confirmé sur les quatre échantillons PNM."""
    assert format_sage_date(pd.Timestamp("2026-09-14")) == "140926"
    assert format_sage_date("16/04/2026") == "160426"
    assert format_sage_date(46128) == "160426"
    assert format_sage_date(None) == ""
    assert format_sage_date("illisible") == ""
