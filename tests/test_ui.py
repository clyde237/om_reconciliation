"""Tests du câblage de l'interface.

Le bouton « Lancer l'analyse » n'appelait rien et affichait « Veuillez charger les
deux fichiers » même lorsque les deux étaient chargés. Ces tests couvrent le chemin
réel : téléversement de plusieurs journaux, lecture, rapprochement journée par
journée face au relevé du mois, restitution dans chaque vue.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.matching import ControleMensuel
from src.readers import EncaissementsReader, OMReader
from ui import session

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RACINE = Path(__file__).resolve().parent.parent
JOURNAUX = ["encaissements_12-05-2026.xlsx", "encaissements_18-05-2026.xlsx"]


class FichierTeleverse:
    """Ce que Streamlit passe à la vue : un nom et un tampon d'octets."""

    def __init__(self, chemin: Path):
        self.name = chemin.name
        self._octets = chemin.read_bytes()

    def getbuffer(self):
        return memoryview(self._octets)


def test_le_fichier_temporaire_est_supprime_apres_lecture():
    """Le §16 interdit de laisser traîner une pièce comptable sur le disque."""
    televerse = FichierTeleverse(FIXTURES / JOURNAUX[0])
    with session.fichier_temporaire(televerse) as chemin:
        assert chemin.exists()
        assert chemin.suffix == ".xlsx"
        lecture = EncaissementsReader(chemin).read()
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


def _controle():
    lectures = [EncaissementsReader(FIXTURES / nom).read() for nom in JOURNAUX]
    releve = OMReader(FIXTURES / "releve_om_exemple.xlsx").read()
    return lectures, releve, ControleMensuel().run(lectures, releve)


def test_le_parcours_complet_produit_un_resultat_exploitable():
    """Ce que le bouton déclenche, de bout en bout."""
    lectures, _, mensuel = _controle()

    assert mensuel.nb_journees_deposees == 2
    assert [j.periode.libelle for j in mensuel.journees] == ["12/05/2026", "18/05/2026"]
    assert all(j.invariant_respecte() for j in mensuel.journees)
    assert mensuel.export_possible
    # Une journée du relevé n'a pas reçu son journal : le contrôle du mois est partiel.
    assert not mensuel.complet
    assert len(mensuel.non_couvertes) == 1


def _app(vue: str) -> AppTest:
    """Lance l'application sur une vue, avec un contrôle déjà en session."""
    lectures, releve, mensuel = _controle()
    app = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30)
    app.session_state[session.CLE_JOURNAUX] = lectures
    app.session_state[session.CLE_RELEVE] = releve
    app.session_state[session.CLE_MENSUEL] = mensuel
    app.session_state[session.CLE_JOURNEE] = mensuel.journees[0].periode.debut
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


def test_le_tableau_de_bord_affiche_le_mois_et_la_journee():
    app = _app("📊 Tableau de bord")
    assert not app.exception
    contenu = _texte(app)
    assert "12/05/2026" in contenu
    assert "Journées contrôlées" in contenu
    assert "Couverture du relevé" in contenu
    assert "Invariant vérifié" in contenu


def test_le_tableau_de_bord_signale_les_journees_sans_journal():
    """Ce qu'aucune journée prise isolément ne peut montrer."""
    app = _app("📊 Tableau de bord")
    contenu = _texte(app)
    assert "n'ont pas reçu leur journal" in contenu
    assert "45" in contenu  # les 45 000 FCFA du 20/05 échappent au contrôle


def test_le_selecteur_de_journee_change_le_detail():
    app = _app("⚖️ Rapprochement")
    assert not app.exception
    assert app.selectbox, "un sélecteur de journée est proposé dès deux journaux"
    onglets = [tab.label for tab in app.tabs]
    assert any("(5)" in libelle for libelle in onglets)  # 12/05 : cinq appariements


def test_reconciliation_option_toutes_les_journees():
    """Vérifie que le sélecteur de la vue rapprochement propose 'TOUTES' (Toutes les journées)."""
    app = _app("⚖️ Rapprochement")
    assert not app.exception
    selecteurs = [sb for sb in app.selectbox if sb.label == "Journée contrôlée"]
    assert len(selecteurs) == 1
    assert "Toutes les journées" in selecteurs[0].options

    # Sélectionner Toutes les journées et exécuter
    selecteurs[0].select("Toutes les journées").run()
    assert not app.exception
    contenu = _texte(app)
    assert "Toutes les journées" in contenu


def test_le_tableau_de_bord_invite_a_importer_quand_rien_n_a_ete_lance():
    app = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert "Aucun contrôle n'a encore été lancé" in _texte(app)


def test_la_vue_anomalies_annonce_l_etat_du_verrou():
    app = _app("⚠️ Anomalies & Écarts")
    assert not app.exception
    assert "aucune anomalie bloquante" in _texte(app).lower()


def test_la_vue_export_reste_fermee():
    """La génération n'existe pas encore : la vue doit le dire, pas le laisser croire."""
    app = _app("📑 Export Comptable Sage")
    assert not app.exception
    assert any(bouton.disabled for bouton in app.button)


def test_upload_avec_archive_zip(tmp_path):
    """Vérifie que l'interface accepte et déballe une archive ZIP de journaux."""
    import io
    import zipfile

    # Créer un zip contenant les deux fixtures de journaux
    tampon_zip = io.BytesIO()
    with zipfile.ZipFile(tampon_zip, "w") as zf:
        for nom in JOURNAUX:
            zf.writestr(nom, (FIXTURES / nom).read_bytes())

    app = AppTest.from_file(str(RACINE / "app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("📥 Importation & Données").run()

    # Téléverser l'archive zip et le relevé OM
    app.file_uploader(key="upload_encaissements").upload("journaux.zip", tampon_zip.getvalue()).run()
    app.file_uploader(key="upload_om").upload(
        "releve_om_exemple.xlsx", (FIXTURES / "releve_om_exemple.xlsx").read_bytes()
    ).run()

    assert not app.exception
    btn = [b for b in app.button if "Lancer" in b.label][0]
    assert not btn.disabled
    btn.click().run()

    assert not app.exception
    contenu = _texte(app)
    assert "2 journée(s) contrôlée(s)" in contenu

