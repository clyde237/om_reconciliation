"""Composants UI réutilisables pour Streamlit."""

import streamlit as st


def render_header(title: str, subtitle: str):
    """Rendu d'un en-tête de page moderne avec titre et sous-titre."""
    st.markdown(f"## {title}")
    st.caption(subtitle)
    st.markdown("---")


def render_kpi_card(title: str, value: str, subtext: str = ""):
    """Carte métrique stylisée."""
    st.metric(label=title, value=value, delta=subtext if subtext else None)
