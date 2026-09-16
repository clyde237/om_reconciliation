"""Tests de normalisation des textes et références."""

import pytest

from src.normalization.references import (
    extract_reference_om,
    normalize_msisdn,
    normalize_reference,
)
from src.normalization.text import clean_text, normalize_key, to_ascii, truncate


def test_clean_text_conserve_casse_et_accents():
    """clean_text produit un libellé lisible : il ne détruit pas l'information."""
    brut = "Monsieur DONGHO DONGMO Thierry\nRéservation N°8207 17/04/26"
    assert clean_text(brut) == "Monsieur DONGHO DONGMO Thierry Réservation N°8207 17/04/26"


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [
        ("Achats matières 19,6 %", "Achats matieres 19,6 %"),
        ("cœur", "coeur"),
        ("Réservation N°8207", "Reservation No8207"),
        ("tiret — long", "tiret - long"),
        ("90\xa0200 FCFA", "90 200 FCFA"),
        (None, ""),
    ],
)
def test_to_ascii(brut, attendu):
    """Le format PNM n'accepte aucun octet au-delà de 127."""
    assert to_ascii(brut) == attendu
    assert all(ord(c) < 128 for c in to_ascii(brut))


def test_normalize_key_rend_comparables_deux_ecritures():
    assert normalize_key(" Réservation  N°8207 ") == normalize_key("reservation no8207")


def test_truncate_ne_tronque_pas_silencieusement():
    """Le dépassement reste détectable : la sortie diffère de l'entrée."""
    libelle = "AVCE NJINI BERLINDA MUNGHI 04/04/26"
    assert len(libelle) == 35
    tronque = truncate(libelle, 25)
    assert len(tronque) == 25
    assert tronque != libelle
    assert truncate("court", 25) == "court"
    avec_marqueur = truncate(libelle, 25, marqueur="…")
    assert avec_marqueur == "AVCE NJINI BERLINDA MUNG…"
    assert len(avec_marqueur) == 25


def test_normalize_reference_conserve_les_points():
    """Les références Orange Money en contiennent : les retirer les mutilerait."""
    assert normalize_reference(" mp260416.1311.a17517 ") == "MP260416.1311.A17517"
    assert normalize_reference("Facture N°TH-7206") == "FACTURENOTH-7206"
    assert normalize_reference(None) == ""


@pytest.mark.parametrize(
    "brut", ["+237 694 697 652", "237694697652", "694697652", "694-697-652"]
)
def test_normalize_msisdn(brut):
    assert normalize_msisdn(brut) == "694697652"


def test_extract_reference_om():
    assert extract_reference_om("Paiement MP260416.1311.A17517 recu") == "MP260416.1311.A17517"
    # Le journal des arrhes n'en contient aucune : c'est le constat qui écarte le
    # niveau 1 de la cascade de rapprochement sur ces sources.
    assert extract_reference_om("Facture N°TH-7206  90 200 FCFA 19/04/2026") == ""
