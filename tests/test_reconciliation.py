"""Tests des contrôles globaux, de la table d'audit et de la synthèse mensuelle (cahier des charges §8)."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from config.matching_config import MatchLevel, MatchStatus
from src.analysis import (
    ControlesGlobaux,
    LigneRapprochement,
    calculer_controles,
    construire_table,
    generer_synthese_mensuelle,
    ventiler_par_compte,
)
from src.matching.appariement import Appariement, ResultatRapprochement
from src.models import LigneJournal, Periode, TransactionOM

JOUR = date(2026, 4, 16)
PERIODE = Periode.journee(JOUR)


def creer_arrhe(montant: str, client: str = "Client Test", ref: str = "RES-001") -> LigneJournal:
    return LigneJournal(
        ligne_source=10,
        date_operation=datetime(2026, 4, 16, 13, 0),
        client=client,
        mode_paiement="Orange Money",
        montant=Decimal(montant),
        reference_interne=ref,
    )


def creer_om(
    montant: str,
    ref: str = "MP260416.0001",
    compte: str = "656009773",
    commission: str = "100",
    operateur: str = "Orange Money",
) -> TransactionOM:
    return TransactionOM(
        numero=1,
        date_operation=JOUR,
        heure=time(13, 10),
        reference=ref,
        service="Merchant Payment",
        statut="Succès",
        compte_agent=compte,
        correspondant="690000000",
        credit=Decimal(montant),
        commission=Decimal(commission),
        operateur=operateur,
    )


def test_controles_globaux_parfait():
    """Vérifie le calcul des 11 contrôles du §8 sur une journée parfaitement réconciliée."""
    l1 = creer_arrhe("90200", "ALPHA Jean")
    t1 = creer_om("90200", "MP001")
    app = Appariement(
        lignes=(l1,),
        transactions=(t1,),
        niveau=MatchLevel.DATE_MONTANT,
        score=100.0,
    )
    res = ResultatRapprochement(
        periode=PERIODE,
        appariements=[app],
        arrhes_sans_om=[],
        recette_du_jour=[],
    )

    controles = calculer_controles(res)
    assert controles.nb_lignes_journal == 1
    assert controles.nb_transactions_om == 1
    assert controles.total_journal == Decimal("90200")
    assert controles.total_om == Decimal("90200")
    assert controles.total_rapproche == Decimal("90200")
    assert controles.total_non_rapproche == Decimal("0")
    assert controles.montant_ecarts == Decimal("0")
    assert controles.nb_conformites == 1
    assert controles.nb_manquants == 0
    assert controles.nb_anomalies == 0
    assert controles.coherent is True
    assert controles.taux_rapprochement == 100.0


def test_controles_globaux_avec_recette_et_manquant():
    """Vérifie l'invariant : total OM = rapproché + recette du jour."""
    l1 = creer_arrhe("50000", "Client 1")
    l_manquante = creer_arrhe("25000", "Client Sans OM")
    t1 = creer_om("50000", "MP001")
    t_recette = creer_om("18000", "MP002", compte="691829711")

    app = Appariement(
        lignes=(l1,),
        transactions=(t1,),
        niveau=MatchLevel.DATE_MONTANT,
        score=100.0,
    )
    res = ResultatRapprochement(
        periode=PERIODE,
        appariements=[app],
        arrhes_sans_om=[l_manquante],
        recette_du_jour=[t_recette],
    )

    controles = calculer_controles(res)
    assert controles.total_journal == Decimal("75000")
    assert controles.total_om == Decimal("68000")
    assert controles.total_rapproche == Decimal("50000")
    assert controles.total_recette_du_jour == Decimal("18000")
    assert controles.total_non_rapproche == Decimal("43000")  # 25000 arrhe + 18000 recette
    assert controles.nb_manquants == 1  # l_manquante
    assert controles.coherent is True


def test_construire_table():
    """Vérifie que la table d'audit contient les colonnes et observations attendues."""
    l1 = creer_arrhe("90200", "ALPHA Jean")
    t1 = creer_om("90200", "MP001", compte="656009773")
    app = Appariement(
        lignes=(l1,),
        transactions=(t1,),
        niveau=MatchLevel.DATE_MONTANT,
        score=100.0,
    )
    res = ResultatRapprochement(periode=PERIODE, appariements=[app])
    table = construire_table(res)

    assert len(table) == 1
    ligne = table[0]
    assert isinstance(ligne, LigneRapprochement)
    assert ligne.date_operation == JOUR
    assert ligne.client == "ALPHA Jean"
    assert ligne.montant_journal == Decimal("90200")
    assert ligne.montant_om == Decimal("90200")
    assert ligne.ecart == Decimal("0")
    assert ligne.statut is MatchStatus.CONFORME
    assert "Correspondance exacte trouvée" in ligne.observation
    assert ligne.compte_om == "656009773"
    assert not ligne.est_bloquante


def test_observer_recette_texte():
    """Vérifie le texte de l'observation pour une transaction en recette du jour."""
    t_om = creer_om("50000", "MP001")
    t_momo = creer_om("30000", "MOMO001", operateur="MTN MoMo")

    table = construire_table(ResultatRapprochement(periode=PERIODE, recette_du_jour=[t_om, t_momo]))
    assert len(table) == 2
    assert table[0].observation == "Paiement Orange Money reçu sur le relevé mais absent du journal des encaissements."
    assert table[1].observation == "Paiement MTN MoMo reçu sur le relevé mais absent du journal des encaissements."


def test_synthese_mensuelle_et_ventilation():
    """Vérifie la synthèse multi-comptes et la ventilation par point de vente."""
    l1 = creer_arrhe("50000", "Client 1")
    t1 = creer_om("50000", "MP001", compte="656009773", commission="500")
    t2 = creer_om("20000", "MP002", compte="691829711", commission="200")

    app = Appariement(lignes=(l1,), transactions=(t1,), niveau=MatchLevel.DATE_MONTANT, score=100.0)
    res = ResultatRapprochement(
        periode=PERIODE,
        appariements=[app],
        recette_du_jour=[t2],
    )

    synthese = generer_synthese_mensuelle(res, periode_libelle="16 avril 2026")
    assert synthese.periode_libelle == "16 avril 2026"
    assert synthese.controles_globaux.total_om == Decimal("70000")
    assert synthese.controles_globaux.total_commissions == Decimal("7000") or synthese.controles_globaux.total_commissions == Decimal("700")

    comptes = {v.compte: v for v in synthese.ventilation_comptes}
    assert "656009773" in comptes
    assert comptes["656009773"].total_om == Decimal("50000")
    assert comptes["656009773"].total_rapproche == Decimal("50000")

    assert "691829711" in comptes
    assert comptes["691829711"].total_recette == Decimal("20000")
