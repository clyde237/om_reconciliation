"""Tests du modèle canonique du domaine."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from src.models import LigneJournal, LotImport, Periode, TransactionOM

JOUR = date(2026, 4, 16)


def arrhe(montant="90200", mode="Orange Money", heure=13):
    return LigneJournal(
        ligne_source=4,
        date_operation=datetime(2026, 4, 16, heure, 16),
        client="Monsieur DONGHO DONGMO Thierry",
        mode_paiement=mode,
        montant=Decimal(montant),
    )


def transaction(service="Merchant Payment", statut="Succès", credit="90200"):
    return TransactionOM(
        numero=65,
        date_operation=JOUR,
        heure=time(13, 11, 20),
        reference="MP260416.1311.A17517",
        service=service,
        statut=statut,
        compte_agent="656009773",
        correspondant="694697652",
        credit=Decimal(credit),
        commission=Decimal("-902"),
    )


# --- Periode -------------------------------------------------------------------


def test_une_journee_est_une_periode():
    """Le journal des arrhes se tire par journée : c'est le cas nominal."""
    periode = Periode.journee(JOUR)
    assert periode.est_journee
    assert periode.libelle == "16/04/2026"
    assert list(periode) == [JOUR]


def test_la_periode_filtre_le_releve_mensuel():
    """Le relevé couvre le mois ; seule la journée contrôlée entre dans le périmètre."""
    periode = Periode.journee(JOUR)
    assert periode.contient(JOUR)
    assert periode.contient(datetime(2026, 4, 16, 23, 59))
    assert not periode.contient(date(2026, 4, 15))
    assert not periode.contient(date(2026, 4, 17))
    assert not periode.contient(None)


def test_periode_sur_plusieurs_jours():
    periode = Periode(debut=date(2026, 4, 1), fin=date(2026, 4, 30))
    assert not periode.est_journee
    assert periode.libelle == "du 01/04/2026 au 30/04/2026"
    assert len(list(periode)) == 30
    assert periode.contient(JOUR)


def test_periode_inversee_refusee():
    with pytest.raises(ValueError):
        Periode(debut=date(2026, 4, 30), fin=date(2026, 4, 1))


# --- LigneJournal --------------------------------------------------------------


def test_le_mode_de_paiement_delimite_le_perimetre():
    assert arrhe().est_orange_money
    assert not arrhe(mode="Espèces").est_orange_money
    assert not arrhe(mode="Virement Bancaire").est_orange_money


def test_le_mode_de_paiement_tolere_la_typographie():
    assert arrhe(mode="orange money").est_orange_money
    assert arrhe(mode="  ORANGE  MONEY ").est_orange_money


# --- TransactionOM -------------------------------------------------------------


def test_seul_un_paiement_marchand_reussi_est_un_encaissement_client():
    assert transaction().est_encaissement_client
    assert not transaction(statut="Echec").est_encaissement_client
    assert not transaction(service="C2C Transfer").est_encaissement_client
    assert not transaction(credit="0").est_encaissement_client


def test_les_virements_internes_sont_hors_perimetre():
    """Onze lignes du relevé d'avril transfèrent entre comptes du groupe."""
    interne = transaction(service="C2C Transfer", credit="5000000")
    assert interne.est_transfert_interne
    assert not interne.est_encaissement_client


def test_les_commissions_sont_identifiees():
    """Le relevé les écrit avec des espaces de tête : « ␣␣Commissions »."""
    assert transaction(service="  Commissions").est_commission
    assert not transaction().est_commission


def test_le_credit_est_l_encaissement():
    assert transaction().montant == Decimal("90200")


def test_cles_de_comparaison():
    t = transaction()
    assert t.cle_reference == "MP260416.1311.A17517"
    assert t.cle_correspondant == "694697652"


# --- LotImport -----------------------------------------------------------------


def test_le_lot_conserve_le_motif_de_chaque_rejet():
    """Un rapport d'import doit justifier chaque ligne absente."""
    lot = LotImport()
    lot.retenues.extend([arrhe(), arrhe()])
    lot.rejeter(11, "sous-total des arrhes antérieures")
    lot.rejeter(16, "bloc Récapitulatif")
    assert lot.nb_lues == 4
    assert lot.resume() == "2 ligne(s) retenue(s), 2 écartée(s)"
    assert lot.rejets[0] == (11, "sous-total des arrhes antérieures")


# --- Règle du résidu : les encaissements non appariés sont la recette du jour ------


def test_le_residu_n_est_pas_un_manquant():
    """Arbitrage du 16/09/2026 : le résidu du rapprochement est la recette du jour.

    Le relevé porte tous les encaissements du point de vente, le journal des arrhes
    seulement les arrhes. Sans cette règle, les recettes ordinaires seraient classées
    en MANQUANT_JOURNAL — un statut bloquant — et le verrou d'export se déclencherait
    chaque jour sur des opérations normales.
    """
    from config.matching_config import BLOCKING_STATUSES, MatchStatus, STATUT_RESIDU_OM

    assert STATUT_RESIDU_OM is MatchStatus.RECETTE_JOUR
    assert STATUT_RESIDU_OM not in BLOCKING_STATUSES
    assert MatchStatus.MANQUANT_JOURNAL in BLOCKING_STATUSES


def test_l_invariant_de_la_journee_du_16_04():
    """Sur la journée réelle : 6 encaissements OM = 3 arrhes + 3 recettes."""
    encaissements = [Decimal(m) for m in ("90200", "110200", "90200", "1500", "6000", "10500")]
    arrhes_journal = [Decimal(m) for m in ("90200", "110200", "90200")]

    reste = list(encaissements)
    rapprochees = []
    for montant in arrhes_journal:
        reste.remove(montant)  # consommation : une ligne appariée ne l'est qu'une fois
        rapprochees.append(montant)

    assert sum(rapprochees) == Decimal("290600")
    assert sum(reste) == Decimal("18000")
    assert sum(rapprochees) + sum(reste) == sum(encaissements)
