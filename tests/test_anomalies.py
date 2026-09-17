"""Tests d'extraction des anomalies, manquants et doublons."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from config.matching_config import MatchLevel, MatchStatus
from src.analysis import (
    construire_table,
    extraire_anomalies,
    extraire_doublons,
    extraire_manquants_journal,
    extraire_manquants_om,
)
from src.matching.appariement import Appariement, ResultatRapprochement
from src.models import LigneJournal, Periode, TransactionOM

JOUR = date(2026, 4, 16)
PERIODE = Periode.journee(JOUR)


def arrhe(montant: str, client: str = "Client") -> LigneJournal:
    return LigneJournal(
        ligne_source=5,
        date_operation=datetime(2026, 4, 16, 12, 0),
        client=client,
        mode_paiement="Orange Money",
        montant=Decimal(montant),
        reference_interne="REF-01",
    )


def om(montant: str, ref: str = "MP01", statut: str = "Succès") -> TransactionOM:
    return TransactionOM(
        numero=1,
        date_operation=JOUR,
        heure=time(12, 5),
        reference=ref,
        service="Merchant Payment",
        statut=statut,
        compte_agent="656009773",
        correspondant="690000000",
        credit=Decimal(montant),
        commission=Decimal("0"),
    )


def test_extraire_anomalies_ecart_montant():
    """Vérifie la détection d'une anomalie sur écart de montant."""
    l1 = arrhe("90200", "ALPHA Jean")
    t1 = om("90000", "MP001")
    app = Appariement(lignes=(l1,), transactions=(t1,), niveau=MatchLevel.DATE_MONTANT, score=100.0)

    res = ResultatRapprochement(periode=PERIODE, appariements=[app])
    anomalies = extraire_anomalies(res)

    assert len(anomalies) == 1
    assert anomalies[0].statut is MatchStatus.ECART_MONTANT
    assert anomalies[0].ecart == Decimal("200")
    assert anomalies[0].est_bloquante is True


def test_extraire_manquants():
    """Vérifie l'extraction des manquants OM et Journal."""
    l_sans_om = arrhe("35000", "Client Manquant")
    res = ResultatRapprochement(periode=PERIODE, arrhes_sans_om=[l_sans_om])

    manquants_om = extraire_manquants_om(res)
    assert len(manquants_om) == 1
    assert manquants_om[0].statut is MatchStatus.MANQUANT_OM
    assert manquants_om[0].client == "Client Manquant"


def test_extraire_doublons():
    """Vérifie l'extraction du rapport des doublons."""
    l_doublon = arrhe("50000", "Client Doublon")
    t_doublon = om("50000", "MP_DOUBLE")

    res = ResultatRapprochement(
        periode=PERIODE,
        doublons_journal=[l_doublon],
        doublons_om=[t_doublon],
    )
    rapport = extraire_doublons(res)
    assert rapport.a_des_doublons is True
    assert len(rapport.doublons_journal) == 1
    assert len(rapport.doublons_om) == 1
    assert rapport.total_occurrences == 2
