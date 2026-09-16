"""État partagé de la session Streamlit.

Le résultat du contrôle est calculé une fois, à l'import, et toutes les vues le
lisent ici. Aucune vue ne relit un fichier ni ne relance un rapprochement.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import streamlit as st

from src.matching import ResultatRapprochement
from src.readers import LectureJournal, LectureOM

CLE_JOURNAL = "lecture_journal"
CLE_RELEVE = "lecture_releve"
CLE_RESULTAT = "resultat_rapprochement"
CLE_ERREUR = "erreur_import"


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
    for cle in (CLE_JOURNAL, CLE_RELEVE, CLE_RESULTAT, CLE_ERREUR):
        st.session_state.pop(cle, None)


def enregistrer(journal: LectureJournal, releve: LectureOM, resultat: ResultatRapprochement) -> None:
    st.session_state[CLE_JOURNAL] = journal
    st.session_state[CLE_RELEVE] = releve
    st.session_state[CLE_RESULTAT] = resultat
    st.session_state.pop(CLE_ERREUR, None)


def journal() -> Optional[LectureJournal]:
    return st.session_state.get(CLE_JOURNAL)


def releve() -> Optional[LectureOM]:
    return st.session_state.get(CLE_RELEVE)


def resultat() -> Optional[ResultatRapprochement]:
    return st.session_state.get(CLE_RESULTAT)


def erreur() -> Optional[str]:
    return st.session_state.get(CLE_ERREUR)


def signaler_erreur(message: str) -> None:
    st.session_state[CLE_ERREUR] = message
    for cle in (CLE_JOURNAL, CLE_RELEVE, CLE_RESULTAT):
        st.session_state.pop(cle, None)


def exige_un_controle(quoi: str = "ce rapprochement") -> Optional[ResultatRapprochement]:
    """Affiche l'invitation à importer et renvoie None si rien n'a encore été contrôlé."""
    courant = resultat()
    if courant is None:
        st.info(
            f"Aucun contrôle n'a encore été lancé. Importez le journal des arrhes et "
            f"le relevé Orange Money dans **Importation & Données** pour obtenir {quoi}."
        )
    return courant
