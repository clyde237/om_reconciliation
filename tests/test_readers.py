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

from config.settings import JOURNAL_ARRHES_DIR, RELEVES_OM_DIR
from src.models import Periode
from src.readers import JournalReader, OMReader

FIXTURES = Path(__file__).resolve().parent / "fixtures"
JOURNAL = FIXTURES / "journal_arrhes_exemple.xlsx"
RELEVE = FIXTURES / "releve_om_exemple.xlsx"
JOURNEE = date(2026, 5, 12)


@pytest.fixture(scope="module")
def journal():
    return JournalReader(JOURNAL).read()


@pytest.fixture(scope="module")
def releve():
    return OMReader(RELEVE).read()


# --- Journal des arrhes --------------------------------------------------------


def test_la_periode_est_lue_dans_l_entete(journal):
    """Elle fait foi : c'est elle qui définit le périmètre du contrôle."""
    assert journal.periode == Periode.journee(JOURNEE)
    assert journal.periode.est_journee
    assert not journal.periode_deduite


def test_la_table_ne_commence_pas_a_la_premiere_ligne(journal):
    """La ligne 1 porte le bloc société ; les en-têtes sont en ligne 2."""
    assert [ligne.ligne_source for ligne in journal.lignes] == [3, 4, 5, 6, 7]


def test_chaque_ligne_ecartee_porte_son_motif(journal):
    """Un rapport d'import doit justifier toute ligne absente."""
    motifs = dict(journal.lot.rejets)
    assert motifs[8] == "sous-total"
    assert motifs[10] == "ligne de total"
    assert motifs[11] == "note de bas de page"
    assert motifs[12] == "pagination"
    assert motifs[13] == "bloc Récapitulatif"
    # Le récapitulatif s'étend sur plusieurs lignes ; les nommer une à une
    # produirait un rapport illisible.
    assert motifs[17] == "bloc Récapitulatif"
    assert journal.lot.nb_lues == 18


def test_le_mode_d_encaissement_delimite_le_perimetre(journal):
    """Espèces et virement sont lus, mais ne concernent pas le rapprochement."""
    assert len(journal.lignes) == 5
    retenues = journal.lignes_orange_money
    assert len(retenues) == 3
    assert journal.total_orange_money == Decimal("270500")
    assert {ligne.mode_paiement for ligne in retenues} == {"Orange Money"}


def test_le_client_et_la_reservation_sont_extraits(journal):
    """La colonne compte est multi-ligne : nom du client, puis numéro de réservation."""
    ligne = journal.lignes_orange_money[0]
    assert ligne.client == "Monsieur ALPHA Jean"
    assert ligne.reference_interne == "9001"
    assert ligne.montant == Decimal("75000")
    assert ligne.date_operation.hour == 11


def test_le_journal_ne_porte_aucune_reference_orange_money(journal):
    """Constat qui écarte le niveau 1 de la cascade de rapprochement."""
    from src.normalization.references import extract_reference_om

    for ligne in journal.lignes_orange_money:
        assert extract_reference_om(ligne.libelle) == ""
        assert extract_reference_om(ligne.client) == ""


def test_fichier_absent():
    with pytest.raises(FileNotFoundError):
        JournalReader(FIXTURES / "inexistant.xlsx").read()


def test_entete_introuvable(tmp_path):
    from openpyxl import Workbook

    chemin = tmp_path / "sans_entete.xlsx"
    classeur = Workbook()
    classeur.active.append(["rien", "ici", "ne", "ressemble", "a", "un", "entete"])
    classeur.save(chemin)
    with pytest.raises(ValueError, match="En-tête introuvable"):
        JournalReader(chemin).read()


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
    assert len(du_second) == 2
    assert du_second[0].reference == "MP260512.1920.G00007"
    assert du_second[0].credit == Decimal("12000")


def test_les_lignes_de_solde_et_de_total_ne_sont_pas_des_transactions(releve):
    assert len(releve.transactions) == 8
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

    assert len(tout_le_mois) == 6  # dont le 18/05, hors de la journée contrôlée
    assert len(du_jour) == 5
    assert all(journal.periode.contient(t.date_operation) for t in du_jour)


def test_arrhes_et_recette_du_jour(journal, releve):
    """Invariant : encaissements OM du jour = arrhes rapprochées + recette du jour."""
    encaissements = releve.encaissements(journal.periode)
    total_om = sum(t.montant for t in encaissements)

    reste = [t.montant for t in encaissements]
    rapprochees = []
    for arrhe in journal.lignes_orange_money:
        reste.remove(arrhe.montant)  # consommation : une ligne n'est appariée qu'une fois
        rapprochees.append(arrhe.montant)

    assert sum(rapprochees) == journal.total_orange_money == Decimal("270500")
    assert sum(reste) == Decimal("15500")
    assert sum(rapprochees) + sum(reste) == total_om


# --- Fichiers réels, si présents -----------------------------------------------


def _fichier_reel(dossier: Path) -> Path | None:
    if not dossier.exists():
        return None
    return next(iter(sorted(dossier.glob("*.xlsx"))), None)


@pytest.mark.skipif(
    _fichier_reel(JOURNAL_ARRHES_DIR) is None or _fichier_reel(RELEVES_OM_DIR) is None,
    reason="fichiers client absents de data/input (exclu du dépôt)",
)
def test_sur_les_fichiers_reels():
    """Contrôle de non-régression quand les fichiers client sont présents localement."""
    journal = JournalReader(_fichier_reel(JOURNAL_ARRHES_DIR)).read()
    releve = OMReader(_fichier_reel(RELEVES_OM_DIR)).read()

    assert journal.periode == Periode.journee(date(2026, 4, 16))
    assert journal.total_orange_money == Decimal("290600")  # récapitulatif du fichier
    assert len(releve.comptes) == 4
    assert len(releve.transactions) + len(releve.commissions) == 177
    assert len(releve.encaissements(journal.periode)) == 6
