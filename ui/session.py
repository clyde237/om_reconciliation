"""État partagé de la session Streamlit.

Le résultat du contrôle est calculé une fois, à l'import, et toutes les vues le
lisent ici. Aucune vue ne relit un fichier ni ne relance un rapprochement.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import streamlit as st

from src.matching import ResultatMensuel, ResultatRapprochement
from src.readers import LectureEncaissements, LectureOM

from src.analysis.validation import JournalDecisions

CLE_JOURNAUX = "lectures_encaissements"
CLE_RELEVE = "lecture_releve"
CLE_MENSUEL = "resultat_mensuel"
CLE_JOURNEE = "journee_selectionnee"
CLE_ERREUR = "erreur_import"
CLE_DECISIONS = "journal_decisions"


@contextmanager
def fichier_temporaire(fichier_televerse) -> Iterator[Path]:
    """Écrit un fichier téléversé sur disque, puis le supprime.

    Les lecteurs travaillent sur un chemin, et Streamlit ne fournit qu'un flux. Le
    §16 impose de ne pas laisser traîner de pièce comptable : la suppression est
    dans un `finally`, elle a donc lieu même si la lecture échoue.
    """
    suffixe = Path(fichier_televerse.name).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffixe, delete=False) as tampon:
        tampon.write(fichier_televerse.getbuffer())
        chemin = Path(tampon.name)
    try:
        yield chemin
    finally:
        chemin.unlink(missing_ok=True)


def reinitialiser() -> None:
    for cle in (CLE_JOURNAUX, CLE_RELEVE, CLE_MENSUEL, CLE_JOURNEE, CLE_ERREUR, CLE_DECISIONS):
        st.session_state.pop(cle, None)


def enregistrer(
    journaux: list[LectureEncaissements],
    releve: LectureOM,
    mensuel: ResultatMensuel,
) -> None:
    st.session_state[CLE_JOURNAUX] = journaux
    st.session_state[CLE_RELEVE] = releve
    st.session_state[CLE_MENSUEL] = mensuel
    st.session_state.pop(CLE_ERREUR, None)
    if mensuel.journees:
        st.session_state[CLE_JOURNEE] = mensuel.journees[0].periode.debut
    if CLE_DECISIONS not in st.session_state:
        st.session_state[CLE_DECISIONS] = JournalDecisions()


def decisions() -> JournalDecisions:
    """Retourne le journal des décisions partagé de la session."""
    if CLE_DECISIONS not in st.session_state:
        st.session_state[CLE_DECISIONS] = JournalDecisions()
    return st.session_state[CLE_DECISIONS]


def journaux() -> list[LectureEncaissements]:
    return st.session_state.get(CLE_JOURNAUX, [])


def mensuel() -> Optional[ResultatMensuel]:
    return st.session_state.get(CLE_MENSUEL)


def releve() -> Optional[LectureOM]:
    return st.session_state.get(CLE_RELEVE)


def resultat() -> Optional[ResultatRapprochement]:
    """Le rapprochement de la journée sélectionnée, ou de toutes les journées consolidées."""
    controle = mensuel()
    if controle is None or not controle.journees:
        return None
    jour = st.session_state.get(CLE_JOURNEE)
    if jour == "TOUTES":
        return controle.consolider()
    for journee in controle.journees:
        if journee.periode.debut == jour:
            return journee
    return controle.journees[0]


def selectionner_journee(jour) -> None:
    st.session_state[CLE_JOURNEE] = jour


def journee_selectionnee():
    return st.session_state.get(CLE_JOURNEE)


def selecteur_de_journee(cle: str, autoriser_toutes: bool = False) -> None:
    """Affiche le sélecteur de journée, quand plusieurs journaux ont été déposés."""
    controle = mensuel()
    if controle is None or len(controle.journees) < 2:
        return
    jours = [journee.periode.debut for journee in controle.journees]
    options = ["TOUTES"] + jours if autoriser_toutes else jours
    courant = st.session_state.get(CLE_JOURNEE)
    idx = options.index(courant) if courant in options else 0

    def _format_jour(j):
        if j == "TOUTES":
            return "Toutes les journées"
        return j.strftime("%d/%m/%Y")

    choisi = st.selectbox(
        "Journée contrôlée",
        options,
        index=idx,
        format_func=_format_jour,
        key=cle,
    )
    selectionner_journee(choisi)


def erreur() -> Optional[str]:
    return st.session_state.get(CLE_ERREUR)


def signaler_erreur(message: str) -> None:
    st.session_state[CLE_ERREUR] = message
    for cle in (CLE_JOURNAUX, CLE_RELEVE, CLE_MENSUEL, CLE_JOURNEE):
        st.session_state.pop(cle, None)


def exige_un_controle(quoi: str = "ce rapprochement") -> Optional[ResultatRapprochement]:
    """Affiche l'invitation à importer et renvoie None si rien n'a encore été contrôlé."""
    courant = resultat()
    if courant is None:
        st.info(
            f"Aucun contrôle n'a encore été lancé. Importez les journaux des encaissements et "
            f"le relevé Orange Money dans **Importation & Données** pour obtenir {quoi}."
        )
    return courant
