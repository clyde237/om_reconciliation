"""Vue Tableau de bord & KPIs de rapprochement."""

import streamlit as st
from ui.components import render_kpi_card, render_header


def render_dashboard():
    """Affiche le tableau de bord principal."""
    render_header("📊 Tableau de Bord Financier", "Vue d'ensemble des réconciliations Orange Money & Journal des Arrhes")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("Taux de Réconciliation", "0.0%", "0 transactions rapprochées")
    with col2:
        render_kpi_card("Volume OM", "0 FCFA", "Total relevés Orange Money")
    with col3:
        render_kpi_card("Volume Arrhes", "0 FCFA", "Total journal comptable")
    with col4:
        render_kpi_card("Écart Non Justifié", "0 FCFA", "Différence nette globale")

    st.markdown("---")
    st.info("Veuillez téléverser les relevés OM et le journal des arrhes dans l'onglet **Importation & Données** pour lancer le rapprochement.")
