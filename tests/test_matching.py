"""Tests du moteur de rapprochement (cahier des charges §4)."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from config.matching_config import MatchLevel, MatchStatus, MatchingConfig
from src.matching import ReconciliationMatcher, doublons_journal, doublons_om
from src.models import LigneJournal, Periode, TransactionOM

JOUR = date(2026, 4, 16)
PERIODE = Periode.journee(JOUR)


def arrhe(montant, client="Monsieur ALPHA Jean", heure=13, jour=JOUR, reference="", mode="Orange Money"):
    return LigneJournal(
        ligne_source=0,
        date_operation=datetime(jour.year, jour.month, jour.day, heure, 0),
        client=client,
        mode_paiement=mode,
        montant=Decimal(str(montant)),
        reference_interne=reference,
    )


def encaissement(montant, reference="MP260416.1311.A00001", jour=JOUR, statut="Succès",
                 service="Merchant Payment", correspondant="690000001", commission="0"):
    return TransactionOM(
        numero=1,
        date_operation=jour,
        heure=time(13, 11, 20),
        reference=reference,
        service=service,
        statut=statut,
        compte_agent="656009773",
        correspondant=correspondant,
        credit=Decimal(str(montant)),
        commission=Decimal(commission),
    )


def rapprocher(arrhes, encaissements, config=None):
    moteur = ReconciliationMatcher(config) if config else ReconciliationMatcher()
    return moteur.run(PERIODE, arrhes, encaissements)


# --- Les niveaux de la cascade -------------------------------------------------


def test_niveau_2_date_et_montant():
    resultat = rapprocher([arrhe(90200)], [encaissement(90200)])
    assert len(resultat.appariements) == 1
    appariement = resultat.appariements[0]
    assert appariement.niveau is MatchLevel.DATE_MONTANT
    assert appariement.statut is MatchStatus.CONFORME
    assert appariement.ecart == 0


def test_niveau_1_reference_exacte():
    """Inopérant sur les sources actuelles, mais correct quand une référence existe."""
    reference = "MP260416.1311.A00001"
    resultat = rapprocher([arrhe(90200, reference=reference)], [encaissement(90200, reference)])
    assert resultat.appariements[0].niveau is MatchLevel.REFERENCE_MONTANT
    assert resultat.appariements[0].score == 100.0


def test_l_heure_n_est_pas_un_critere():
    """Le journal horodate la saisie, pas l'encaissement : jusqu'à plus d'une heure d'écart."""
    resultat = rapprocher([arrhe(90200, heure=16)], [encaissement(90200)])
    assert len(resultat.appariements) == 1


def test_niveau_4_tolerance_de_dates():
    veille = date(2026, 4, 15)
    resultat = rapprocher([arrhe(90200)], [encaissement(90200, jour=veille)])
    assert not resultat.appariements  # hors de la journée contrôlée, donc hors périmètre

    periode_large = Periode(veille, JOUR)
    resultat = ReconciliationMatcher().run(
        periode_large, [arrhe(90200)], [encaissement(90200, jour=veille)]
    )
    assert resultat.appariements[0].niveau is MatchLevel.MONTANT_DATE_TOLERANCE
    assert resultat.appariements[0].score < 100


def test_la_tolerance_de_dates_est_bornee():
    lointain = date(2026, 4, 1)
    config = MatchingConfig(tolerance_days=3)
    resultat = ReconciliationMatcher(config).run(
        Periode(lointain, JOUR), [arrhe(90200)], [encaissement(90200, jour=lointain)]
    )
    assert not resultat.appariements
    assert len(resultat.arrhes_sans_om) == 1


def test_niveau_5_regroupement():
    """Deux arrhes du même jour réglées en un seul encaissement."""
    resultat = rapprocher([arrhe(50000), arrhe(40000, client="Madame BETA")], [encaissement(90000)])
    assert len(resultat.appariements) == 1
    appariement = resultat.appariements[0]
    assert appariement.niveau is MatchLevel.COMBINAISON_LIGNES
    assert appariement.est_groupe
    assert appariement.statut is MatchStatus.CORRESPONDANCE_GROUPEE
    assert appariement.montant_journal == appariement.montant_om == Decimal("90000")


def test_le_regroupement_est_borne():
    """Trois lignes ne se regroupent pas si le plafond est à deux."""
    config = MatchingConfig(max_group_size=2)
    resultat = rapprocher(
        [arrhe(10000), arrhe(20000, client="B"), arrhe(30000, client="C")],
        [encaissement(60000)],
        config=config,
    )
    assert not resultat.appariements
    assert len(resultat.arrhes_sans_om) == 3


# --- La consommation des lignes ------------------------------------------------


def test_deux_montants_identiques_le_meme_jour():
    """Le cas réel du 16/04/2026 : deux arrhes de 90 200 et deux encaissements de 90 200.

    Aucune règle ne peut les distinguer. Seule la consommation garantit un
    appariement un pour un, plutôt que deux arrhes pointant sur le même encaissement.
    """
    arrhes = [arrhe(90200, client="DONGHO"), arrhe(90200, client="DONGZE")]
    encaissements = [
        encaissement(90200, "MP260416.1311.A17517"),
        encaissement(90200, "MP260416.1523.A41832"),
    ]
    resultat = rapprocher(arrhes, encaissements)

    assert len(resultat.appariements) == 2
    references = {a.references_om for a in resultat.appariements}
    assert references == {"MP260416.1311.A17517", "MP260416.1523.A41832"}
    assert not resultat.recette_du_jour
    assert not resultat.arrhes_sans_om


def test_une_transaction_n_est_appariee_qu_une_fois():
    arrhes = [arrhe(90200, client="A"), arrhe(90200, client="B")]
    resultat = rapprocher(arrhes, [encaissement(90200)])
    assert len(resultat.appariements) == 1
    assert len(resultat.arrhes_sans_om) == 1


# --- Périmètre -----------------------------------------------------------------


def test_seules_les_arrhes_orange_money_entrent():
    resultat = rapprocher(
        [arrhe(90200), arrhe(146400, client="YOSSA", mode="Espèces")], [encaissement(90200)]
    )
    assert len(resultat.appariements) == 1
    assert not resultat.arrhes_sans_om


def test_les_virements_internes_et_les_echecs_sont_ecartes():
    resultat = rapprocher(
        [arrhe(90200)],
        [
            encaissement(90200),
            encaissement(5000000, "PP260416.1155.C00002", service="C2C Transfer"),
            encaissement(6000, "MP260416.2124.C75779", statut="Echec"),
        ],
    )
    assert len(resultat.appariements) == 1
    assert not resultat.recette_du_jour
    assert len(resultat.transactions_invalides) == 1


def test_le_releve_est_filtre_sur_la_journee():
    resultat = rapprocher(
        [arrhe(90200)], [encaissement(90200), encaissement(11000, "MP260424.0842.C95587", jour=date(2026, 4, 24))]
    )
    assert len(resultat.appariements) == 1
    assert not resultat.recette_du_jour  # le 24/04 est hors périmètre, pas une recette


# --- Résidu, statuts et invariant ----------------------------------------------


def test_le_residu_est_la_recette_du_jour():
    resultat = rapprocher(
        [arrhe(90200)],
        [encaissement(90200), encaissement(1500, "MP260416.2036.B26053"),
         encaissement(10500, "MP260416.2133.B86992")],
    )
    assert len(resultat.recette_du_jour) == 2
    assert resultat.total_recette_du_jour == Decimal("12000")
    assert MatchStatus.RECETTE_JOUR in resultat.par_statut()
    assert resultat.export_possible  # une recette ne bloque pas


def test_ecart_de_montant_bloque_l_export():
    config = MatchingConfig(amount_tolerance=1000.0)
    resultat = rapprocher([arrhe(90200)], [encaissement(90000)], config=config)
    appariement = resultat.appariements[0]
    assert appariement.statut is MatchStatus.ECART_MONTANT
    assert appariement.ecart == Decimal("200")
    assert not resultat.export_possible
    assert MatchStatus.ECART_MONTANT in resultat.anomalies_bloquantes


def test_arrhe_sans_encaissement_bloque_l_export():
    resultat = rapprocher([arrhe(90200)], [])
    assert len(resultat.arrhes_sans_om) == 1
    assert not resultat.export_possible
    assert resultat.anomalies_bloquantes == {MatchStatus.MANQUANT_OM: 1}


def test_invariant_de_la_journee():
    resultat = rapprocher(
        [arrhe(90200), arrhe(110200, client="NKEN")],
        [encaissement(90200), encaissement(110200, "MP260416.1339.B43686"),
         encaissement(6000, "MP260416.2124.C75779")],
    )
    assert resultat.invariant_respecte()
    assert resultat.total_rapproche == Decimal("200400")
    assert resultat.total_recette_du_jour == Decimal("6000")
    assert resultat.total_om == Decimal("206400")
    assert resultat.taux_rapprochement == 100.0


def test_le_resultat_est_reproductible():
    arrhes = [arrhe(90200, client="A"), arrhe(90200, client="B")]
    encaissements = [encaissement(90200, "MP260416.1311.A17517"), encaissement(90200, "MP260416.1523.A41832")]
    premier = rapprocher(arrhes, encaissements)
    second = rapprocher(arrhes, encaissements)
    assert [a.references_om for a in premier.appariements] == [a.references_om for a in second.appariements]


# --- Doublons ------------------------------------------------------------------


def test_doublon_journal_exige_le_meme_client():
    """Deux arrhes de 90 200 le même jour pour deux clients différents sont normales."""
    assert not doublons_journal([arrhe(90200, client="DONGHO"), arrhe(90200, client="DONGZE")])
    doubles = doublons_journal([arrhe(90200, client="DONGHO"), arrhe(90200, client="DONGHO")])
    assert len(doubles) == 2


def test_doublon_om_sur_la_reference():
    reference = "MP260416.1311.A17517"
    assert not doublons_om([encaissement(90200, reference), encaissement(90200, "MP260416.1523.A41832")])
    assert len(doublons_om([encaissement(90200, reference), encaissement(90200, reference)])) == 2


def test_les_doublons_ne_bloquent_pas_l_export():
    """Conséquence directe de l'arbitrage sur les statuts bloquants."""
    resultat = rapprocher(
        [arrhe(90200, client="DONGHO"), arrhe(90200, client="DONGHO")],
        [encaissement(90200, "MP260416.1311.A17517"), encaissement(90200, "MP260416.1523.A41832")],
    )
    assert len(resultat.doublons_journal) == 2
    assert resultat.par_statut()[MatchStatus.DOUBLON] == 2
    assert resultat.export_possible
