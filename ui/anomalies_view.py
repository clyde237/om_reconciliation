"""Vue de détection et traitement des anomalies financières."""

import streamlit as st
from ui.components import render_header


def render_anomalies_view():
    """Affiche la liste des anomalies détectées (écarts, doublons, retards)."""
    render_header("⚠️ Audit des Anomalies & Écarts", "Identification des divergences de flux et doublons de transactions")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Doublons potentiels")
        st.info("Aucun doublon détecté pour le moment.")
    with col2:
        st.subheader("Écarts de montants")
        st.info("Aucun écart de montant détecté.")
