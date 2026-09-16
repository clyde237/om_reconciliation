"""Tests de validation humaine et de gestion du verrou d'export (§10, §14 et §19)."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from config.matching_config import MatchLevel, MatchStatus
from src.analysis.reconciliation import construire_table
from src.analysis.validation import (
    DecisionType,
    GestionnaireVerrou,
    JournalDecisions,
    cle_ligne_rapprochement,
)
from src.matching.appariement import Appariement, ResultatRapprochement
from src.models import LigneJournal, Periode, TransactionOM

JOUR = date(2026, 4, 16)
PERIODE = Periode.journee(JOUR)


def arrhe(montant: str, client: str = "Client Alpha", ligne: int = 2) -> LigneJournal:
    return LigneJournal(
        ligne_source=ligne,
        date_operation=datetime(2026, 4, 16, 12, 0),
        client=client,
        mode_paiement="Orange Money",
        montant=Decimal(montant),
        reference_interne="REF-01",
    )


def om(montant: str, ref: str = "MP01") -> TransactionOM:
    return TransactionOM(
        numero=1,
        date_operation=JOUR,
        heure=time(12, 5),
        reference=ref,
        service="Merchant Payment",
        statut="Succès",
        compte_agent="656009773",
        correspondant="690000000",
        credit=Decimal(montant),
        commission=Decimal("0"),
    )


def test_verrou_ouvert_sans_anomalie():
    """Une journée sans aucune anomalie bloquante autorise l'export immédiatement."""
    l1 = arrhe("90200")
    t1 = om("90200")
    app = Appariement(lignes=(l1,), transactions=(t1,), niveau=MatchLevel.DATE_MONTANT, score=100.0)
    res = ResultatRapprochement(periode=PERIODE, appariements=[app])

    verrou = GestionnaireVerrou.evaluer(res)
    assert verrou.export_autorise is True
    assert verrou.nb_anomalies_totales == 0
    assert verrou.nb_anomalies_en_attente == 0

    eligibles = GestionnaireVerrou.lignes_eligibles_export(res)
    assert len(eligibles) == 1
    assert eligibles[0].statut is MatchStatus.CONFORME


def test_verrou_bloque_sur_anomalie_non_validee():
    """Une anomalie bloquante non instruite interdit l'export comptable."""
    l1 = arrhe("90200", client="Client Écart")
    t1 = om("85000", ref="MP_ECART")  # Écart de 5 200 FCFA
    app = Appariement(lignes=(l1,), transactions=(t1,), niveau=MatchLevel.DATE_MONTANT, score=100.0)
    res = ResultatRapprochement(periode=PERIODE, appariements=[app])

    journal = JournalDecisions()
    verrou = GestionnaireVerrou.evaluer(res, journal)

    assert verrou.export_autorise is False
    assert verrou.nb_anomalies_totales == 1
    assert verrou.nb_anomalies_en_attente == 1
    assert "Export bloqué" in verrou.motif_blocage
    assert "ECART_MONTANT" in verrou.motif_blocage

    # Les lignes éligibles sont vides tant que le verrou est actif
    eligibles = GestionnaireVerrou.lignes_eligibles_export(res, journal)
    assert len(eligibles) == 0


def test_validation_anomalie_deverrouille_export():
    """La validation formelle par le contrôleur lève le verrou et intègre la ligne."""
    l1 = arrhe("90200", client="Client Écart")
    t1 = om("85000", ref="MP_ECART")
    app = Appariement(lignes=(l1,), transactions=(t1,), niveau=MatchLevel.DATE_MONTANT, score=100.0)
    res = ResultatRapprochement(periode=PERIODE, appariements=[app])

    table = construire_table(res)
    ligne_anomalie = table[0]

    journal = JournalDecisions()
    journal.valider(ligne_anomalie, auteur="Contrôleur Dupont", motif="Écart justifié par frais annexes")

    verrou = GestionnaireVerrou.evaluer(res, journal)
    assert verrou.export_autorise is True
    assert verrou.nb_anomalies_validees == 1
    assert verrou.nb_anomalies_en_attente == 0

    eligibles = GestionnaireVerrou.lignes_eligibles_export(res, journal)
    assert len(eligibles) == 1
    assert eligibles[0].client == "Client Écart"


def test_rejet_anomalie_exclut_la_ligne():
    """Une ligne rejetée ne doit JAMAIS apparaître dans les écritures comptables."""
    l1 = arrhe("90200", client="Client Conforme")
    t1 = om("90200")
    app_conforme = Appariement(lignes=(l1,), transactions=(t1,), niveau=MatchLevel.DATE_MONTANT, score=100.0)

    l2 = arrhe("30000", client="Client Orphelin", ligne=5)
    res = ResultatRapprochement(
        periode=PERIODE,
        appariements=[app_conforme],
        arrhes_sans_om=[l2],  # MANQUANT_OM bloquant
    )

    table = construire_table(res)
    anomalie = [l for l in table if l.statut is MatchStatus.MANQUANT_OM][0]

    journal = JournalDecisions()
    journal.rejeter(anomalie, auteur="Contrôleur Dupont", motif="Erreur de saisie dans le journal, ne pas comptabiliser")

    verrou = GestionnaireVerrou.evaluer(res, journal)
    assert verrou.export_autorise is True
    assert verrou.nb_anomalies_rejetees == 1
    assert verrou.nb_anomalies_en_attente == 0

    eligibles = GestionnaireVerrou.lignes_eligibles_export(res, journal)
    # Seule la ligne conforme est transmise, l'anomalie rejetée est exclue
    assert len(eligibles) == 1
    assert eligibles[0].statut is MatchStatus.CONFORME
    assert eligibles[0].client == "Client Conforme"


def test_validation_groupee_toute_la_periode():
    """La validation groupée traite l'ensemble des anomalies en un appel."""
    l1 = arrhe("10000", client="C1", ligne=1)
    l2 = arrhe("20000", client="C2", ligne=2)
    res = ResultatRapprochement(periode=PERIODE, arrhes_sans_om=[l1, l2])

    table = construire_table(res)
    journal = JournalDecisions()
    nb = journal.valider_toutes(table, auteur="Superviseur", motif="Validation groupée fin de journée")

    assert nb == 2
    verrou = GestionnaireVerrou.evaluer(res, journal)
    assert verrou.export_autorise is True
    assert verrou.nb_anomalies_validees == 2
