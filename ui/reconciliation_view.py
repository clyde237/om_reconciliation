"""Vue interactive du rapprochement multi-critères."""

import streamlit as st
from ui.components import render_header


def render_reconciliation_view():
    """Affiche les correspondances exactes, partielles et manuelles."""
    render_header("⚖️ Rapprochement Multi-Critères", "Examen des correspondances et ajustements manuels")

    tab1, tab2, tab3 = st.tabs(["Correspondances Exactes", "Correspondances Approchées (Fuzzy)", "Transactions Orphelines"])

    with tab1:
        st.write("Aucune donnée disponible. Veuillez importer vos fichiers.")
    with tab2:
        st.write("Aucun rapprochement flou à valider.")
    with tab3:
        st.write("Aucune opération orpheline détectée.")
