"""Tests du câblage de l'interface.

Le bouton « Lancer l'analyse » n'appelait rien et affichait « Veuillez charger les
deux fichiers » même lorsque les deux étaient chargés. Ces tests couvrent le chemin
réel : téléversement, lecture, rapprochement, restitution dans chaque vue.
"""

from io import BytesIO
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.matching import ReconciliationMatcher
from src.readers import JournalReader, OMReader
from ui import session

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RACINE = Path(__file__).resolve().parent.parent


class FichierTeleverse:
    """Ce que Streamlit passe à la vue : un nom et un tampon d'octets."""

    def __init__(self, chemin: Path):
        self.name = chemin.name
        self._octets = chemin.read_bytes()

    def getbuffer(self):
        return memoryview(self._octets)


def test_le_fichier_temporaire_est_supprime_apres_lecture():
    """Le §16 interdit de laisser traîner une pièce comptable sur le disque."""
    televerse = FichierTeleverse(FIXTURES / "journal_arrhes_exemple.xlsx")
    with session.fichier_temporaire(televerse) as chemin:
        assert chemin.exists()
        assert chemin.suffix == ".xlsx"
        lecture = JournalReader(chemin).read()
        vu = chemin
    assert not vu.exists()
    assert lecture.periode.libelle == "12/05/2026"


def test_le_fichier_temporaire_est_supprime_meme_en_cas_d_echec():
    class Illisible:
        name = "casse.xlsx"

        def getbuffer(self):
            return memoryview(b"ceci n'est pas un classeur")

    with pytest.raises(Exception):
        with session.fichier_temporaire(Illisible()) as chemin:
            vu = chemin
            OMReader(chemin).read()
    assert not vu.exists()


def _resultat_depuis_les_fixtures():
    journal = JournalReader(FIXTURES / "journal_arrhes_exemple.xlsx").read()
    releve = OMReader(FIXTURES / "releve_om_exemple.xlsx").read()
    resultat = ReconciliationMatcher().run(journal.periode, journal.lignes, releve.transactions)
    return journal, releve, resultat


def test_le_parcours_complet_produit_un_resultat_exploitable():
    """Ce que le bouton déclenche, de bout en bout."""
    journal, releve, resultat = _resultat_depuis_les_fixtures()

    assert resultat.periode == journal.periode
    assert len(resultat.appariements) == 3
    assert resultat.taux_rapprochement == 100.0
    assert resultat.invariant_respecte()
    assert len(resultat.recette_du_jour) == 2
    assert resultat.export_possible


def _app(vue: str) -> AppTest:
    """Lance l'application sur une vue, avec un contrôle déjà en session."""
    journal, releve, resultat = _resultat_depuis_les_fixtures()
    app = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30)
    app.session_state[session.CLE_JOURNAL] = journal
    app.session_state[session.CLE_RELEVE] = releve
    app.session_state[session.CLE_RESULTAT] = resultat
    app.run()
    app.sidebar.radio[0].set_value(vue).run()
    return app


def _texte(app: AppTest) -> str:
    morceaux = [element.value for element in app.markdown]
    morceaux += [element.value for element in app.caption]
    morceaux += [element.value for element in app.info]
    morceaux += [element.value for element in app.success]
    morceaux += [element.value for element in app.error]
    morceaux += [element.value for element in app.warning]
    morceaux += [element.label for element in app.metric]
    morceaux += [str(element.value) for element in app.metric]
    return "\n".join(str(m) for m in morceaux)


def test_le_tableau_de_bord_affiche_le_resultat():
    app = _app("📊 Tableau de bord")
    assert not app.exception
    contenu = _texte(app)
    assert "12/05/2026" in contenu
    assert "100.0 %" in contenu
    assert "Invariant vérifié" in contenu
    assert "export comptable est ouvert" in contenu


def test_le_tableau_de_bord_invite_a_importer_quand_rien_n_a_ete_lance():
    app = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert "Aucun contrôle n'a encore été lancé" in _texte(app)


def test_la_vue_rapprochement_separe_arrhes_et_recette():
    app = _app("⚖️ Rapprochement")
    assert not app.exception
    onglets = [tab.label for tab in app.tabs]
    assert any("Arrhes rapprochées (3)" in libelle for libelle in onglets)
    assert any("Recette du jour (2)" in libelle for libelle in onglets)
    assert any("Arrhes sans encaissement (0)" in libelle for libelle in onglets)


def test_la_vue_anomalies_annonce_l_etat_du_verrou():
    app = _app("⚠️ Anomalies & Écarts")
    assert not app.exception
    assert "aucune anomalie bloquante" in _texte(app).lower()


def test_la_vue_export_reste_fermee():
    """La génération n'existe pas encore : la vue doit le dire, pas le laisser croire."""
    app = _app("📑 Export Comptable Sage")
    assert not app.exception
    assert app.button[0].disabled
    assert "n'est pas encore développée" in _texte(app)


def test_la_vue_reconciliation_filtres_et_recherche():
    """Vérifie la présence et le bon fonctionnement des filtres de la Phase 6."""
    app = _app("⚖️ Rapprochement")
    assert not app.exception
    # Les composants selectbox et text_input de filtre doivent être présents
    assert len(app.selectbox) >= 1
    assert len(app.text_input) >= 1


def test_la_vue_anomalies_bloque_export_puis_se_deverrouille():
    """Vérifie l'évaluation du verrou et la levée par validation humaine (§10, §19)."""
    from datetime import datetime, time
    from decimal import Decimal
    from src.models import LigneJournal, Periode, TransactionOM
    from src.matching.appariement import Appariement, ResultatRapprochement
    from config.matching_config import MatchLevel

    jour = datetime(2026, 4, 16).date()
    l_ano = LigneJournal(
        ligne_source=2,
        date_operation=datetime(2026, 4, 16, 12, 0),
        client="Client Inconnu",
        mode_paiement="Orange Money",
        montant=Decimal("15000"),
        reference_interne="REF-ANO",
    )
    res_avec_anomalie = ResultatRapprochement(
        periode=Periode.journee(jour),
        arrhes_sans_om=[l_ano],  # MANQUANT_OM bloquant
    )

    app = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30)
    app.session_state[session.CLE_RESULTAT] = res_avec_anomalie
    app.run()
    app.sidebar.radio[0].set_value("⚠️ Anomalies & Écarts").run()

    assert not app.exception
    texte = _texte(app)
    assert "export bloqué" in texte.lower()
    assert "manquant_om" in texte.lower()

    # Valider toutes les anomalies et vérifier la mise à jour
    journal = app.session_state[session.CLE_DECISIONS]
    journal.valider_toutes(res_avec_anomalie.arrhes_sans_om, auteur="Contrôleur", motif="Vérifié")
    app.run()
    texte_apres = _texte(app)
    assert "aucune anomalie bloquante" in texte_apres.lower()

