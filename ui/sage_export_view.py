"""Vue de génération et d'export des écritures Sage."""

import streamlit as st
from ui.components import render_header


def render_sage_export_view():
    """Génération des fichiers d'intégration Sage (PNM, TXT, Excel)."""
    render_header("📑 Export Comptable Sage 100", "Paramétrage et téléchargement des écritures prêtes pour l'intégration")

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Format d'export", ["PNM (Paramétrable Sage)", "TXT (Délimité)", "Excel (.xlsx)"])
        st.text_input("Code Journal Sage", value="BQ_OM")
    with col2:
        st.text_input("Compte Trésorerie OM", value="512100")
        st.text_input("Compte Arrhes / Acomptes", value="419100")

    st.markdown("---")
    st.button("📥 Générer le fichier d'import Sage", type="primary")
