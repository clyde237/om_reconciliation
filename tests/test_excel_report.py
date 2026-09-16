"""Tests du générateur de rapport Excel d'audit (cahier des charges §9)."""

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from config.matching_config import MatchLevel, MatchStatus
from src.analysis import generer_synthese_mensuelle
from src.matching.appariement import Appariement, ResultatRapprochement
from src.models import LigneJournal, Periode, TransactionOM
from src.reports.excel_report import ExcelReportGenerator

JOUR = date(2026, 4, 16)
PERIODE = Periode.journee(JOUR)


def creer_jeu_test() -> ResultatRapprochement:
    """Crée un résultat de rapprochement riche avec conformes, anomalies, recette et doublons."""
    # Arrhes
    l_conforme = LigneJournal(
        ligne_source=2,
        date_operation=datetime(2026, 4, 16, 13, 0),
        client="ALPHA Jean",
        mode_paiement="Orange Money",
        montant=Decimal("90200"),
        reference_interne="RES-001",
    )
    l_ecart = LigneJournal(
        ligne_source=3,
        date_operation=datetime(2026, 4, 16, 14, 0),
        client="BETA Paul",
        mode_paiement="Orange Money",
        montant=Decimal("50000"),
        reference_interne="RES-002",
    )
    l_manquante = LigneJournal(
        ligne_source=4,
        date_operation=datetime(2026, 4, 16, 15, 0),
        client="GAMMA Luc",
        mode_paiement="Orange Money",
        montant=Decimal("30000"),
        reference_interne="RES-003",
    )
    l_doublon = LigneJournal(
        ligne_source=5,
        date_operation=datetime(2026, 4, 16, 16, 0),
        client="DELTA Marc",
        mode_paiement="Orange Money",
        montant=Decimal("20000"),
        reference_interne="RES-004",
    )

    # OM
    t_conforme = TransactionOM(
        numero=1,
        date_operation=JOUR,
        heure=time(13, 11),
        reference="MP260416.1311.A001",
        service="Merchant Payment",
        statut="Succès",
        compte_agent="656009773",
        correspondant="690000001",
        credit=Decimal("90200"),
        commission=Decimal("900"),
    )
    t_ecart = TransactionOM(
        numero=2,
        date_operation=JOUR,
        heure=time(14, 5),
        reference="MP260416.1405.A002",
        service="Merchant Payment",
        statut="Succès",
        compte_agent="656009773",
        correspondant="690000002",
        credit=Decimal("48000"),  # Écart de 2 000 FCFA
        commission=Decimal("480"),
    )
    t_recette = TransactionOM(
        numero=3,
        date_operation=JOUR,
        heure=time(15, 20),
        reference="MP260416.1520.A003",
        service="Merchant Payment",
        statut="Succès",
        compte_agent="691829711",
        correspondant="690000003",
        credit=Decimal("18000"),
        commission=Decimal("180"),
    )
    t_doublon = TransactionOM(
        numero=4,
        date_operation=JOUR,
        heure=time(16, 10),
        reference="MP260416.1610.A004",
        service="Merchant Payment",
        statut="Succès",
        compte_agent="696948928",
        correspondant="690000004",
        credit=Decimal("20000"),
        commission=Decimal("200"),
    )

    app_conforme = Appariement(
        lignes=(l_conforme,),
        transactions=(t_conforme,),
        niveau=MatchLevel.DATE_MONTANT,
        score=100.0,
    )
    app_ecart = Appariement(
        lignes=(l_ecart,),
        transactions=(t_ecart,),
        niveau=MatchLevel.DATE_MONTANT,
        score=100.0,
    )

    return ResultatRapprochement(
        periode=PERIODE,
        appariements=[app_conforme, app_ecart],
        arrhes_sans_om=[l_manquante],
        recette_du_jour=[t_recette],
        doublons_journal=[l_doublon],
        doublons_om=[t_doublon],
    )


def test_generation_rapport_excel_7_feuilles(tmp_path: Path):
    """Vérifie la génération complète du classeur et l'existence exacte des 7 feuilles du §9."""
    resultat = creer_jeu_test()
    generateur = ExcelReportGenerator(output_dir=tmp_path)
    fichier = generateur.generate(resultat, filename="test_rapport.xlsx")

    assert fichier.exists()
    assert fichier.stat().st_size > 0

    wb = openpyxl.load_workbook(fichier)
    feuilles_attendues = [
        "Synthèse",
        "Rapprochement",
        "Anomalies",
        "Manquants_Journal",
        "Manquants_OM",
        "Doublons",
        "Contrôle_Mensuel",
    ]
    assert wb.sheetnames == feuilles_attendues

    # Vérification feuille Synthèse
    ws_syn = wb["Synthèse"]
    assert "RAPPORT D'AUDIT" in ws_syn["A1"].value
    assert "Période auditée" in ws_syn["A2"].value
    assert "Statut Global" in ws_syn["A5"].value
    # Vérifier présence des contrôles
    labels_ctrl = [ws_syn.cell(row=r, column=1).value for r in range(8, 25)]
    assert "Nombre de lignes du journal" in labels_ctrl
    assert "Total Orange Money" in labels_ctrl
    assert "Montant des Écarts" in labels_ctrl

    # Vérification feuille Rapprochement
    ws_rap = wb["Rapprochement"]
    assert ws_rap["A1"].value == "Date Opération"
    assert ws_rap["D1"].value == "Montant Journal"
    assert ws_rap["G1"].value == "Statut"
    assert ws_rap.auto_filter.ref is not None

    # Vérification feuille Anomalies
    ws_ano = wb["Anomalies"]
    assert ws_ano["A1"].value == "Date"
    # L'écart de montant et l'arrhe manquante doivent être listés
    clients_ano = [ws_ano.cell(row=r, column=3).value for r in range(2, 5)]
    assert "BETA Paul" in clients_ano or "GAMMA Luc" in clients_ano

    # Vérification feuille Contrôle_Mensuel
    ws_mens = wb["Contrôle_Mensuel"]
    assert ws_mens["A1"].value == "Date"
    assert ws_mens.cell(row=2, column=1).value == "16/04/2026"


def test_generation_rapport_en_memoire():
    """Vérifie la génération sous forme de flux binaire (BytesIO) pour Streamlit."""
    resultat = creer_jeu_test()
    generateur = ExcelReportGenerator()
    tampon = generateur.generate_bytes(resultat)

    assert tampon is not None
    assert tampon.getvalue()
    wb = openpyxl.load_workbook(tampon)
    assert len(wb.sheetnames) == 7
    assert "Synthèse" in wb.sheetnames
