"""Vue de téléversement et validation des fichiers sources."""

import streamlit as st
from ui.components import render_header


def render_upload_view():
    """Interface de chargement des fichiers Relevés OM et Journal Arrhes."""
    render_header("📥 Importation des Fichiers", "Téléversez les relevés Orange Money et le Journal comptable des Arrhes")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Relevé Orange Money")
        om_file = st.file_uploader("Fichier OM (Excel ou CSV)", type=["xlsx", "xls", "csv"], key="upload_om")
        if om_file:
            st.success(f"Fichier OM chargé: {om_file.name}")

    with col2:
        st.subheader("2. Journal des Arrhes")
        arrhes_file = st.file_uploader("Fichier Arrhes (Excel ou CSV)", type=["xlsx", "xls", "csv"], key="upload_arrhes")
        if arrhes_file:
            st.success(f"Fichier Arrhes chargé: {arrhes_file.name}")

    st.markdown("---")
    if st.button("🚀 Lancer l'analyse et le rapprochement", type="primary"):
        st.warning("Veuillez charger les deux fichiers pour débuter le traitement automatique.")
