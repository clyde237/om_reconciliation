"""Standardisation des formats de dates.

Les deux sources n'écrivent pas les dates de la même façon : le journal des arrhes
stocke un sérial Excel avec heure (``46128.552777777775``), le relevé Orange Money
une chaîne ``16/04/2026``. Ce module les ramène toutes au même type Python.
"""

from datetime import date, datetime, timedelta
from typing import Any, Optional

import pandas as pd

#: Origine des sérials Excel sous Windows. Le décalage de deux jours par rapport au
#: 01/01/1900 absorbe le bug historique de l'année 1900 bissextile.
EXCEL_EPOCH = datetime(1899, 12, 30)

#: Fenêtre de plausibilité d'un sérial Excel : 01/01/1990 → 01/01/2100.
#: Sans elle, un millésime saisi seul (``2026``) serait lu comme une date de 1905.
EXCEL_SERIAL_MIN = (datetime(1990, 1, 1) - EXCEL_EPOCH).days
EXCEL_SERIAL_MAX = (datetime(2100, 1, 1) - EXCEL_EPOCH).days

#: Pivot de siècle des millésimes à deux chiffres : ``26`` vaut 2026, ``85`` vaut 1985.
PIVOT_SIECLE = 70

_FORMATS = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d",
)


class DateParseError(ValueError):
    """La valeur fournie ne représente pas une date exploitable."""


def parse_datetime(value: Any) -> datetime:
    """Convertit une valeur en ``datetime``, ou lève ``DateParseError``.

    Accepte les formats du §5 — ``16/04/2026``, ``16-04-2026``, ``16/04/26``,
    ``2026-04-16`` — ainsi que les sérials Excel et les objets date natifs.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, bool):
        raise DateParseError(f"booléen inexploitable comme date : {value!r}")
    if isinstance(value, (int, float)):
        return _depuis_serial_excel(float(value))
    if value is None:
        raise DateParseError("date absente")

    texte = str(value).replace("\xa0", " ").strip()
    if not texte:
        raise DateParseError("date vide")

    for modele in _FORMATS:
        try:
            lu = datetime.strptime(texte, modele)
        except ValueError:
            continue
        return _appliquer_pivot(lu) if "%y" in modele else lu

    # Un sérial Excel peut arriver sous forme de texte depuis un CSV.
    try:
        return _depuis_serial_excel(float(texte.replace(",", ".")))
    except (ValueError, DateParseError):
        pass

    raise DateParseError(f"date illisible : {value!r}")


def parse_date(value: Any) -> date:
    """Comme :func:`parse_datetime`, mais sans l'heure.

    L'heure n'est jamais un critère de rapprochement : le journal horodate la saisie
    de l'arrhe, pas l'encaissement, avec des écarts allant jusqu'à plus d'une heure.
    """
    return parse_datetime(value).date()


def _depuis_serial_excel(serial: float) -> datetime:
    if not EXCEL_SERIAL_MIN <= serial <= EXCEL_SERIAL_MAX:
        raise DateParseError(f"hors de la fenêtre des sérials Excel : {serial!r}")
    return EXCEL_EPOCH + timedelta(days=serial)


def _appliquer_pivot(lu: datetime) -> datetime:
    """``strptime`` place déjà 69/70 de part et d'autre de 2000 ; on l'explicite ici."""
    annee = lu.year % 100
    siecle = 1900 if annee >= PIVOT_SIECLE else 2000
    return lu.replace(year=siecle + annee)


def normalize_date(value: Any, default: Optional[date] = None) -> Optional[date]:
    """Variante tolérante de :func:`parse_date` : renvoie ``default`` si illisible."""
    try:
        return parse_date(value)
    except DateParseError:
        return default


def normalize_dates(series: pd.Series, dayfirst: bool = True) -> pd.Series:
    """Normalise une colonne entière ; les valeurs illisibles deviennent ``NaT``.

    Le traitement est fait valeur par valeur : une même colonne d'export mélange
    couramment sérials Excel, dates textuelles et cellules vides, ce qu'un appel
    global à ``pd.to_datetime`` ne sait pas démêler.
    """
    del dayfirst  # les formats jour-en-tête sont déjà prioritaires dans _FORMATS
    return pd.Series(
        [pd.Timestamp(d) if (d := normalize_date(v)) is not None else pd.NaT for v in series],
        index=series.index,
        dtype="datetime64[ns]",
    )


def format_sage_date(dt: Any) -> str:
    """Formate une date au format Sage ``JJMMAA``, confirmé sur les échantillons PNM."""
    if dt is None or (isinstance(dt, float) and pd.isna(dt)) or dt is pd.NaT:
        return ""
    try:
        return parse_date(dt).strftime("%d%m%y")
    except DateParseError:
        return ""
