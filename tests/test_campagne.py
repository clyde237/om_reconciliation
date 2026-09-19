"""Tests du contrôle mensuel : N journaux face à un relevé.

Le journal se tire par journée, le relevé par mois. Ces tests couvrent ce qu'aucun
rapprochement journalier ne peut voir — une journée déposée deux fois, un journal
hors du relevé, et les journées du relevé restées sans journal.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.matching import ControleMensuel
from src.readers import EncaissementsReader, OMReader

FIXTURES = Path(__file__).resolve().parent / "fixtures"
JOURNAUX = ["encaissements_12-05-2026.xlsx", "encaissements_18-05-2026.xlsx"]


@pytest.fixture(scope="module")
def releve():
    return OMReader(FIXTURES / "releve_om_exemple.xlsx").read()


def lire(*noms):
    return [EncaissementsReader(FIXTURES / nom).read() for nom in noms]


@pytest.fixture(scope="module")
def mensuel(releve):
    return ControleMensuel().run(lire(*JOURNAUX), releve)


def test_chaque_journal_est_rapproche_avec_sa_journee(mensuel):
    assert mensuel.nb_journees_deposees == 2
    assert [j.periode.libelle for j in mensuel.journees] == ["12/05/2026", "18/05/2026"]
    assert all(journee.invariant_respecte() for journee in mensuel.journees)


def test_le_regroupement_opere_sur_donnees_realistes(mensuel):
    """Deux factures de 2 000 et 1 500 réglées en un seul encaissement de 3 500."""
    douze_mai = mensuel.journees[0]
    groupes = [a for a in douze_mai.appariements if a.est_groupe]
    assert len(groupes) == 1
    assert groupes[0].montant_om == Decimal("3500")
    assert len(groupes[0].lignes) == 2


def test_la_journee_se_rapproche_entierement(mensuel):
    douze_mai = mensuel.journees[0]
    assert len(douze_mai.appariements) == 5
    assert not douze_mai.recette_du_jour
    assert not douze_mai.arrhes_sans_om
    assert douze_mai.total_rapproche == Decimal("286000")


def test_les_journees_sans_journal_sont_signalees(mensuel):
    """Sans ce contrôle, des encaissements échapperaient au contrôle sans bruit."""
    assert not mensuel.complet
    assert len(mensuel.non_couvertes) == 1
    manquante = mensuel.non_couvertes[0]
    assert manquante.jour == date(2026, 5, 20)
    assert manquante.total == Decimal("45000")
    assert mensuel.total_om_non_controle == Decimal("45000")


def test_le_taux_de_couverture_mesure_le_perimetre_reellement_controle(mensuel):
    assert mensuel.total_om_controle == Decimal("295000")
    assert 0 < mensuel.taux_couverture < 100
    assert mensuel.taux_rapprochement == 100.0


def test_une_journee_deposee_deux_fois_est_signalee(releve):
    """Jamais écrasée en silence : un doublon de dépôt est une erreur d'opérateur."""
    resultat = ControleMensuel().run(lire(JOURNAUX[0], JOURNAUX[0]), releve)
    assert date(2026, 5, 12) in resultat.doublons_de_journee
    assert resultat.nb_journees_deposees == 1
    assert not resultat.complet


def test_un_journal_hors_du_releve_est_signale(releve, tmp_path):
    """Un journal de juin déposé avec le relevé de mai : l'erreur doit se voir."""
    from tests.fixtures.generer_fixtures import journal_des_encaissements, _mouvement

    chemin = tmp_path / "encaissements_03-06-2026.xlsx"
    journal_des_encaissements(
        "03/06/2026",
        [_mouvement("KOT-9999 5 000 FCFA T 1", 5000, Orange_Money=5000)],
        [("Total période *", 5000, 5000)],
    ).save(chemin)

    resultat = ControleMensuel().run([EncaissementsReader(chemin).read()], releve)
    assert resultat.hors_releve == [date(2026, 6, 3)]
    # Sans contrepartie possible, l'encaissement du journal reste sans OM.
    assert len(resultat.journees[0].arrhes_sans_om) == 1
    assert not resultat.export_possible


def test_un_seul_jour_bloquant_ferme_l_export_du_mois(releve, tmp_path):
    from tests.fixtures.generer_fixtures import journal_des_encaissements, _mouvement

    chemin = tmp_path / "encaissements_19-05-2026.xlsx"
    journal_des_encaissements(
        "19/05/2026",
        [_mouvement("BAL-4444 7 700 FCFA MB 2", 7700, Orange_Money=7700)],
        [("Total période *", 7700, 7700)],
    ).save(chemin)

    lectures = lire(*JOURNAUX) + [EncaissementsReader(chemin).read()]
    resultat = ControleMensuel().run(lectures, releve)

    assert not resultat.export_possible
    assert [j.periode.libelle for j in resultat.journees_bloquantes] == ["19/05/2026"]


def test_aucun_journal_depose(releve):
    with pytest.raises(ValueError, match="Aucun journal"):
        ControleMensuel().run([], releve)


def test_consolider_mensuel(mensuel):
    """Vérifie que la consolidation regroupe tous les appariements et flux de toutes les journées."""
    consolide = mensuel.consolider()
    assert len(consolide.appariements) == sum(len(j.appariements) for j in mensuel.journees)
    assert len(consolide.recette_du_jour) == sum(len(j.recette_du_jour) for j in mensuel.journees)
    assert len(consolide.arrhes_sans_om) == sum(len(j.arrhes_sans_om) for j in mensuel.journees)
    assert consolide.total_rapproche == sum((j.total_rapproche for j in mensuel.journees), Decimal("0"))


def test_journal_consolide_mois_complet(releve, tmp_path):
    """Un seul journal déposé couvrant tout le mois (du 01/05 au 31/05).
    
    Il ventile automatiquement par jour et ne marque pas comme non couvertes
    les journées du mois qui n'ont pas eu de ventes au journal.
    """
    from openpyxl import Workbook

    chemin = tmp_path / "journal_mai_consolide.xlsx"
    wb = Workbook()
    ws = wb.active
    ws["B1"] = "Journal des encaissements\nPériode du 01/05/2026 au 31/05/2026 Facturé et encaissé\nHOTEL EXEMPLE SA"
    ws.append([])
    ws.append(["Date", "Mouvement", "Total", "Orange Money"])
    # Journée du 12 mai (facture 12 000)
    ws.append(["12/05/2026", "BAL-3001 12 000 FCFA MB 4", 12000, 12000])
    # Journée du 18 mai (facture 9 000)
    ws.append(["18/05/2026", "BAL-3002 9 000 FCFA MB 1", 9000, 9000])
    ws.append(["TOTAL PERIODE *", None, 21000, 21000])
    wb.save(chemin)

    lecture = EncaissementsReader(chemin).read()
    resultat = ControleMensuel().run([lecture], releve)

    # 12 et 18 mai ont été traités
    dates_journees = {j.periode.debut for j in resultat.journees}
    assert date(2026, 5, 12) in dates_journees
    assert date(2026, 5, 18) in dates_journees
    # Le 20 mai (dans le relevé avec 45 000) est couvert par la période du mois,
    # donc il a sa propre journée (recette du jour) et n'est PAS dans non_couvertes !
    assert date(2026, 5, 20) in dates_journees
    assert not resultat.non_couvertes


def test_decalage_date_tolerance_2_jours(tmp_path):
    """Encaissement saisi le 10/05 au journal mais payé le 12/05 sur le relevé OM (2 jours de décalage)."""
    from openpyxl import Workbook
    from config.matching_config import MatchLevel, MatchStatus
    from src.readers.om_reader import LectureOM

    # 1. Journal avec encaissement le 10/05
    chemin_j = tmp_path / "encaissement_10-05-2026.xlsx"
    wb_j = Workbook()
    ws_j = wb_j.active
    ws_j["B1"] = "Journal des encaissements\nPériode du 10/05/2026 au 10/05/2026\nHOTEL EXEMPLE SA"
    ws_j.append([])
    ws_j.append(["Mouvement", "Total", "Orange Money"])
    ws_j.append(["Réservation N°8888 15/05/26 TOTO Arrhes", 50000, 50000])
    ws_j.append(["TOTAL PERIODE *", 50000, 50000])
    wb_j.save(chemin_j)

    # 2. Relevé OM avec transaction payée le 12/05
    from tests.fixtures.generer_fixtures import releve_orange_money
    chemin_om = tmp_path / "releve_decalage.xlsx"
    wb_om = releve_orange_money()
    # Remplacer la transaction de 75 000 du 12/05 par 50 000
    ws_om = wb_om["Channel User Transaction Report"]
    # Chercher la ligne de 75 000 et mettre 50 000
    for row in ws_om.iter_rows():
        for cell in row:
            if cell.value == 75000:
                cell.value = 50000
                break
    wb_om.save(chemin_om)

    lecture_j = EncaissementsReader(chemin_j).read()
    lecture_om = OMReader(chemin_om).read()

    resultat = ControleMensuel().run([lecture_j], lecture_om)
    jour_10 = resultat.journees[0]
    assert jour_10.periode.debut == date(2026, 5, 10)
    # L'appariement a été trouvé par tolérance de date !
    assert len(jour_10.appariements) == 1
    app = jour_10.appariements[0]
    assert app.niveau is MatchLevel.MONTANT_DATE_TOLERANCE
    assert app.statut is MatchStatus.PAIEMENT_POSTERIEUR_A_SAISIE
    assert app.lignes[0].jour == date(2026, 5, 10)
    assert app.transactions[0].date_operation == date(2026, 5, 12)
    # Observation détaillée
    from src.analysis.observations import observer_appariement
    obs = observer_appariement(app)
    assert "décalage de 2 jours" in obs
    assert "Journal : 10/05/2026" in obs
    assert "OM : 12/05/2026" in obs
    from src.normalization.amounts import format_amount
    assert f"{format_amount(50000)} FCFA" in obs
    assert "Contrôle obligatoire avant export" in obs


def test_decalage_date_hors_tolerance_reste_non_rapproche(tmp_path):
    """Un décalage de 5 jours (> tolérance par défaut de 3 jours) ne doit pas être apparié."""
    from openpyxl import Workbook
    from src.readers.om_reader import OMReader
    from tests.fixtures.generer_fixtures import releve_orange_money

    chemin_j = tmp_path / "encaissement_05-05-2026.xlsx"
    wb_j = Workbook()
    ws_j = wb_j.active
    ws_j["B1"] = "Journal des encaissements\nPériode du 05/05/2026 au 05/05/2026\nHOTEL EXEMPLE SA"
    ws_j.append([])
    ws_j.append(["Mouvement", "Total", "Orange Money"])
    ws_j.append(["Réservation N°7777 Arrhes", 50000, 50000])
    ws_j.append(["TOTAL PERIODE *", 50000, 50000])
    wb_j.save(chemin_j)

    chemin_om = tmp_path / "releve_hors_tolerance.xlsx"
    wb_om = releve_orange_money()
    # Transaction le 12/05 (écart = 7 jours > 3)
    ws_om = wb_om["Channel User Transaction Report"]
    for row in ws_om.iter_rows():
        for cell in row:
            if cell.value == 75000:
                cell.value = 50000
                break
    wb_om.save(chemin_om)

    lecture_j = EncaissementsReader(chemin_j).read()
    lecture_om = OMReader(chemin_om).read()

    resultat = ControleMensuel().run([lecture_j], lecture_om)
    jour_05 = resultat.journees[0]
    assert len(jour_05.appariements) == 0
    assert len(jour_05.arrhes_sans_om) == 1


def test_rapprochement_combine_om_momo_meme_jour(tmp_path):
    """Contrôle simultané : une ligne OM et une ligne MoMo le même jour."""
    from openpyxl import Workbook
    from src.models import LotImport, Periode, TransactionOM, MODE_MTN_MOMO, MODE_ORANGE_MONEY
    from src.readers.om_reader import LectureOM
    from config.matching_config import MatchStatus

    # Journal avec 1 flux OM et 1 flux MoMo
    chemin_j = tmp_path / "encaissement_15-05-2026.xlsx"
    wb_j = Workbook()
    ws_j = wb_j.active
    ws_j["B1"] = "Journal des encaissements\nPériode du 15/05/2026 au 15/05/2026\nHOTEL EXEMPLE SA"
    ws_j.append([])
    ws_j.append(["Mouvement", "Total", "Orange Money", "MTN Mobile Money"])
    ws_j.append(["Réservation N°1001 ALICE Arrhes", 25000, 25000, None])
    ws_j.append(["Réservation N°1002 BOB Arrhes", 35000, None, 35000])
    ws_j.append(["TOTAL PERIODE *", 60000, 25000, 35000])
    wb_j.save(chemin_j)

    # Relevé OM
    lot_om = LotImport()
    lot_om.retenues.append(
        TransactionOM(
            numero=1,
            date_operation=date(2026, 5, 15),
            reference="MP260515.0001.A00001",
            service="Merchant Payment",
            statut="Succès",
            compte_agent="656000001",
            credit=Decimal("25000"),
            operateur=MODE_ORANGE_MONEY,
        )
    )
    releve_om = LectureOM(lot=lot_om)

    # Relevé MoMo
    lot_momo = LotImport()
    lot_momo.retenues.append(
        TransactionOM(
            numero=1,
            date_operation=date(2026, 5, 15),
            reference="MOMO-260515100000-1",
            service="Payment",
            statut="Successful",
            compte_agent="83588336",
            credit=Decimal("35000"),
            libelle_compte="BOB",
            operateur=MODE_MTN_MOMO,
        )
    )
    releve_momo = LectureOM(lot=lot_momo)

    lecture_j = EncaissementsReader(chemin_j).read()
    assert len(lecture_j.mouvements) == 2
    assert lecture_j.total_om == Decimal("25000")
    assert lecture_j.total_momo == Decimal("35000")

    resultat = ControleMensuel().run([lecture_j], releve_om, releve_momo=releve_momo)
    jour = resultat.journees[0]
    assert len(jour.appariements) == 2
    assert len(jour.arrhes_sans_om) == 0
    assert all(a.statut == MatchStatus.CONFORME for a in jour.appariements)


def test_inversion_operateur_saisie_croisee(tmp_path):
    """Inversion de saisie : caissier a saisi OM au lieu de MoMo."""
    from openpyxl import Workbook
    from src.models import LotImport, TransactionOM, MODE_MTN_MOMO, MODE_ORANGE_MONEY
    from src.readers.om_reader import LectureOM
    from config.matching_config import MatchStatus
    from src.analysis.observations import observer_appariement

    chemin_j = tmp_path / "encaissement_16-05-2026.xlsx"
    wb_j = Workbook()
    ws_j = wb_j.active
    ws_j["B1"] = "Journal des encaissements\nPériode du 16/05/2026 au 16/05/2026\nHOTEL EXEMPLE SA"
    ws_j.append([])
    ws_j.append(["Mouvement", "Total", "Orange Money", "MTN Mobile Money"])
    # Erreur de saisie : enregistré dans la colonne OM
    ws_j.append(["Réservation N°2001 DUPONT Arrhes", 40000, 40000, None])
    ws_j.append(["TOTAL PERIODE *", 40000, 40000, 0])
    wb_j.save(chemin_j)

    # Relevé OM vide (aucun paiement sur OM)
    releve_om = LectureOM(lot=LotImport())

    # Relevé MoMo portant le paiement réel
    lot_momo = LotImport()
    lot_momo.retenues.append(
        TransactionOM(
            numero=1,
            date_operation=date(2026, 5, 16),
            reference="MOMO-260516100000-1",
            service="Payment",
            statut="Successful",
            compte_agent="83588336",
            credit=Decimal("40000"),
            libelle_compte="DUPONT",
            operateur=MODE_MTN_MOMO,
        )
    )
    releve_momo = LectureOM(lot=lot_momo)

    lecture_j = EncaissementsReader(chemin_j).read()
    resultat = ControleMensuel().run([lecture_j], releve_om, releve_momo=releve_momo)
    jour = resultat.journees[0]

    assert len(jour.appariements) == 1
    app = jour.appariements[0]
    # Statut probable (croisement à valider par le contrôleur)
    assert app.statut == MatchStatus.CORRESPONDANCE_PROBABLE
    obs = observer_appariement(app)
    assert "Croisement d'opérateur" in obs
    assert "Orange Money" in obs
    assert "MTN Mobile Money" in obs


def test_inversion_operateur_avec_decalage_date(tmp_path):
    """Inversion d'opérateur avec décalage de date (saisi MoMo le 17, encaissé OM le 19)."""
    from openpyxl import Workbook
    from src.models import LotImport, TransactionOM, MODE_MTN_MOMO, MODE_ORANGE_MONEY
    from src.readers.om_reader import LectureOM
    from config.matching_config import MatchStatus
    from src.analysis.observations import observer_appariement

    chemin_j = tmp_path / "encaissement_17-05-2026.xlsx"
    wb_j = Workbook()
    ws_j = wb_j.active
    ws_j["B1"] = "Journal des encaissements\nPériode du 17/05/2026 au 17/05/2026\nHOTEL EXEMPLE SA"
    ws_j.append([])
    ws_j.append(["Mouvement", "Total", "Orange Money", "MTN Mobile Money"])
    ws_j.append(["Réservation N°3001 Arrhes", 60000, None, 60000])
    ws_j.append(["TOTAL PERIODE *", 60000, 0, 60000])
    wb_j.save(chemin_j)

    # Relevé OM avec encaissement le 19/05 (décalage de 2 jours)
    lot_om = LotImport()
    lot_om.retenues.append(
        TransactionOM(
            numero=1,
            date_operation=date(2026, 5, 19),
            reference="MP260519.0001.A00001",
            service="Merchant Payment",
            statut="Succès",
            compte_agent="656000001",
            credit=Decimal("60000"),
            operateur=MODE_ORANGE_MONEY,
        )
    )
    releve_om = LectureOM(lot=lot_om)
    releve_momo = LectureOM(lot=LotImport())

    lecture_j = EncaissementsReader(chemin_j).read()
    resultat = ControleMensuel().run([lecture_j], releve_om, releve_momo=releve_momo)
    jour = resultat.journees[0]

    assert len(jour.appariements) == 1
    app = jour.appariements[0]
    assert app.statut == MatchStatus.PAIEMENT_POSTERIEUR_A_SAISIE
    obs = observer_appariement(app)
    assert "Croisement d'opérateur" in obs
    assert "décalage de 2 jours" in obs



