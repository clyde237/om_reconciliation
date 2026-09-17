"""Tests unitaires du lecteur de relevé MTN Mobile Money."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.models import MODE_MTN_MOMO
from src.readers.momo_reader import MomoReader

FICHIER_MOMO_REEL = Path("/home/blackcode/Documents/COMPTABILITE/004 RELEVE MOMO AVRIL 2026.xlsx")


@pytest.mark.skipif(not FICHIER_MOMO_REEL.exists(), reason="Fichier réel non disponible")
def test_lecture_releve_momo_reel():
    reader = MomoReader(FICHIER_MOMO_REEL)
    lecture = reader.read()

    # 58 paiements clients + 3 rejets (ajustements internes) = 61 lignes exploitables
    assert len(lecture.lot.retenues) == 58
    assert len(lecture.lot.rejets) == 3

    # Somme exacte des paiements clients
    total = sum(t.montant for t in lecture.transactions)
    assert total == Decimal("3019150")

    # Vérification des propriétés de la première transaction
    t0 = lecture.transactions[0]
    assert t0.date_operation == date(2026, 4, 28)
    assert t0.montant == Decimal("19200")
    assert t0.correspondant == "678850220"
    assert t0.libelle_compte == "ERIC STEPHANE DOHO WOUAFO"
    assert t0.operateur == MODE_MTN_MOMO
    assert t0.est_reussie is True
    assert t0.est_encaissement_client is True

    # Période couverte
    assert lecture.periode_declaree is not None
    assert lecture.periode_declaree.debut == date(2026, 4, 1)
    assert lecture.periode_declaree.fin == date(2026, 4, 28)
