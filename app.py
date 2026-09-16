"""
Application OM Reconciliation - Point d'entrée principal.

Ce module se lance avec `streamlit run app.py`, jamais avec `python app.py` :
Streamlit a besoin de son propre exécuteur pour disposer d'un contexte de session.
Lancé directement, le script afficherait une page vide et des dizaines
d'avertissements « missing ScriptRunContext ».
"""

import sys

import streamlit as st
from config.settings import APP_TITLE, APP_VERSION
from ui.dashboard import render_dashboard
from ui.upload import render_upload_view
from ui.reconciliation_view import render_reconciliation_view
from ui.anomalies_view import render_anomalies_view
from ui.sage_export_view import render_sage_export_view


def init_session_state():
    """Initialise l'état global de la session Streamlit."""
    if "df_om" not in st.session_state:
        st.session_state["df_om"] = None
    if "df_arrhes" not in st.session_state:
        st.session_state["df_arrhes"] = None
    if "reconciliation_result" not in st.session_state:
        st.session_state["reconciliation_result"] = None


def main():
    st.set_page_config(
        page_title=f"{APP_TITLE} v{APP_VERSION}",
        page_icon="💳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    st.sidebar.title("💳 OM Reconciliation")
    st.sidebar.caption(f"Version {APP_VERSION}")

    menu_options = [
        "📊 Tableau de bord",
        "📥 Importation & Données",
        "⚖️ Rapprochement",
        "⚠️ Anomalies & Écarts",
        "📑 Export Comptable Sage",
    ]

    choice = st.sidebar.radio("Navigation", menu_options, index=0)

    st.sidebar.markdown("---")
    st.sidebar.info(
        "Module d'audit et de rapprochement financier : "
        "Flux Orange Money vs Journal des Arrhes & Intégration Sage."
    )

    if choice == "📊 Tableau de bord":
        render_dashboard()
    elif choice == "📥 Importation & Données":
        render_upload_view()
    elif choice == "⚖️ Rapprochement":
        render_reconciliation_view()
    elif choice == "⚠️ Anomalies & Écarts":
        render_anomalies_view()
    elif choice == "📑 Export Comptable Sage":
        render_sage_export_view()


def _lance_par_streamlit() -> bool:
    """Vrai si le script tourne bien sous `streamlit run`."""
    try:
        from streamlit.runtime import exists

        return exists()
    except ImportError:  # version de Streamlit sans cette API
        return True


if __name__ == "__main__":
    if not _lance_par_streamlit():
        commande = f"{sys.executable.replace('/python', '/streamlit')} run {__file__}"
        print(
            "OM Reconciliation est une application Streamlit : elle ne se lance pas\n"
            "avec python, qui ne lui fournit aucun contexte de session.\n\n"
            f"    {commande}\n\n"
            "ou, plus court, depuis la racine du projet :\n\n"
            "    make run\n",
            file=sys.stderr,
        )
        raise SystemExit(1)
    main()
