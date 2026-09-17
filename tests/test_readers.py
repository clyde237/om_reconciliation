"""Tests de lecture des deux sources.

Les classeurs d'exemple reproduisent la structure des fichiers réels — bloc d'en-tête,
table décalée, sous-totaux, récapitulatif, sous-relevés concaténés, en-têtes brouillés
par les cellules fusionnées — avec des données fabriquées. Les fichiers réels, qui
portent des noms de clients et des numéros de téléphone, restent hors du dépôt.
"""

from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest

from config.matching_config import MatchStatus
from config.settings import JOURNAUX_ENCAISSEMENTS_DIR, RELEVES_OM_DIR
from src.models import Periode
from src.readers import EncaissementsReader, OMReader

FIXTURES = Path(__file__).resolve().parent / "fixtures"
JOURNAL = FIXTURES / "encaissements_12-05-2026.xlsx"
RELEVE = FIXTURES / "releve_om_exemple.xlsx"
JOURNEE = date(2026, 5, 12)


@pytest.fixture(scope="module")
def journal():
    return EncaissementsReader(JOURNAL).read()


@pytest.fixture(scope="module")
def releve():
    return OMReader(RELEVE).read()


# --- Relevé Orange Money -------------------------------------------------------


def test_les_sous_releves_sont_separes(releve):
    """Chaque compte a son préambule, et les étiquettes changent d'un bloc à l'autre."""
    comptes = releve.comptes_par_numero()
    assert sorted(comptes) == ["600000001", "600000002"]
    assert comptes["600000001"].point_de_vente == "RELEVE MAI 2026 ACCUEIL"
    assert comptes["600000002"].point_de_vente == "RELEVE MAI 2026 RESTAURANT"
    assert comptes["600000002"].intitule.startswith("POINT DE VENTE DEUX")


def test_les_entetes_brouilles_sont_ignores(releve):
    """Le second bloc réécrit ses en-têtes n'importe comment ; ses lignes restent lues."""
    du_second = [t for t in releve.transactions if t.compte_agent == "600000002"]
    assert len(du_second) == 3
    assert du_second[0].reference == "MP260512.1920.G00007"
    assert du_second[0].credit == Decimal("12000")


def test_les_lignes_de_solde_et_de_total_ne_sont_pas_des_transactions(releve):
    assert len(releve.transactions) == 9
    assert all(t.reference for t in releve.transactions)


def test_les_commissions_sont_isolees(releve):
    """Elles n'ont pas de date, alimentent un compte à part et ne se rapprochent pas."""
    assert len(releve.commissions) == 1
    assert releve.commissions[0].est_commission
    assert releve.commissions[0] not in releve.transactions


def test_une_transaction_en_echec_est_lue_mais_hors_perimetre(releve):
    echecs = [t for t in releve.transactions if not t.est_reussie]
    assert len(echecs) == 1
    assert not echecs[0].est_encaissement_client


def test_les_virements_internes_sont_hors_perimetre(releve):
    internes = [t for t in releve.transactions if t.est_transfert_interne]
    assert len(internes) == 1
    assert internes[0].credit == Decimal("200000")
    assert internes[0] not in releve.encaissements()


def test_la_periode_declaree_est_un_controle_pas_un_filtre(releve):
    """Le relevé annonce le mois ; c'est le journal qui porte la période contrôlée."""
    assert releve.periode_declaree == Periode(date(2026, 5, 1), date(2026, 5, 31))
    assert not releve.periode_declaree.est_journee


def test_l_heure_est_lue(releve):
    transaction = next(t for t in releve.transactions if t.numero == 2)
    assert transaction.heure == time(11, 10, 44)


# --- Les deux sources ensemble -------------------------------------------------


def test_le_releve_est_filtre_sur_la_periode_du_journal(journal, releve):
    """La règle de périmètre : une journée déposée, le relevé restreint à cette journée."""
    tout_le_mois = releve.encaissements()
    du_jour = releve.encaissements(journal.periode)

    assert len(tout_le_mois) == 7  # dont les 18/05 et 20/05, hors de la journée
    assert len(du_jour) == 5
    assert all(journal.periode.contient(t.date_operation) for t in du_jour)


def test_le_journal_couvre_tous_les_encaissements_du_jour(journal, releve):
    """Le journal des encaissements porte arrhes et factures : il doit tout couvrir.

    C'est ce qui le distingue du journal des arrhes, qui n'en portait qu'une part et
    laissait un résidu à requalifier.
    """
    du_jour = releve.encaissements(journal.periode)
    assert sum(t.montant for t in du_jour) == journal.total_om == Decimal("286000")
    assert journal.total_arrhes == Decimal("270500")
    assert journal.total_factures == Decimal("15500")


# --- Fichiers réels, si présents -----------------------------------------------


def _fichier_reel(dossier: Path) -> Path | None:
    if not dossier.exists():
        return None
    return next(iter(sorted(dossier.glob("*.xlsx"))), None)


@pytest.mark.skipif(
    _fichier_reel(JOURNAUX_ENCAISSEMENTS_DIR) is None or _fichier_reel(RELEVES_OM_DIR) is None,
    reason="fichiers client absents de data/input (exclu du dépôt)",
)
def test_sur_les_fichiers_reels():
    """Contrôle de non-régression quand les fichiers client sont présents localement."""
    from src.matching import ReconciliationMatcher

    journal = EncaissementsReader(_fichier_reel(JOURNAUX_ENCAISSEMENTS_DIR)).read()
    releve = OMReader(_fichier_reel(RELEVES_OM_DIR)).read()

    assert journal.periode == Periode.journee(date(2026, 4, 16))
    # Le fichier annonce ses propres totaux : la lecture doit tomber dessus.
    assert journal.total_om == journal.total_declare_om == Decimal("308600")
    assert journal.total_arrhes == Decimal("290600")
    assert journal.total_factures == Decimal("18000")
    assert journal.ecart_au_recapitulatif() == 0

    assert len(releve.comptes) == 4
    assert len(releve.transactions) + len(releve.commissions) == 177
    assert len(releve.encaissements(journal.periode)) == 6

    resultat = ReconciliationMatcher().run(
        journal.periode, journal.lignes_orange_money, releve.transactions
    )

    # Sept mouvements du journal pour six transactions OM : deux factures Kotibé
    # de 8 000 et 2 500 se règlent en un seul encaissement de 10 500.
    assert len(resultat.appariements) == 6
    assert sum(1 for a in resultat.appariements if a.est_groupe) == 1
    assert resultat.taux_rapprochement == 100.0
    assert resultat.total_rapproche == Decimal("308600")
    assert not resultat.recette_du_jour
    assert not resultat.arrhes_sans_om
    assert resultat.invariant_respecte()
    assert resultat.export_possible
