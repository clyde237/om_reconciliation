"""Vue Tableau de bord & indicateurs du contrôle."""

import streamlit as st

from config.matching_config import MatchStatus
from src.normalization.amounts import format_amount
from ui import session
from ui.components import render_header, render_kpi_card


def render_dashboard():
    render_header(
        "📊 Tableau de Bord Financier",
        "Résultat du contrôle de la journée : arrhes rapprochées, recette et anomalies",
    )

    resultat = session.exige_un_controle("les indicateurs de la journée")
    if resultat is None:
        return

    st.caption(f"Journée contrôlée : **{resultat.periode.libelle}**")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            "Taux de rapprochement",
            f"{resultat.taux_rapprochement:.1f} %",
            f"{len(resultat.appariements)} arrhe(s) rapprochée(s)",
        )
    with c2:
        render_kpi_card(
            "Encaissements OM",
            f"{format_amount(resultat.total_om)} FCFA",
            f"{len(resultat.appariements) + len(resultat.recette_du_jour)} opération(s)",
        )
    with c3:
        render_kpi_card(
            "Arrhes rapprochées",
            f"{format_amount(resultat.total_rapproche)} FCFA",
            "journal des arrhes",
        )
    with c4:
        render_kpi_card(
            "Recette du jour",
            f"{format_amount(resultat.total_recette_du_jour)} FCFA",
            f"{len(resultat.recette_du_jour)} encaissement(s) hors arrhes",
        )

    st.markdown("---")

    gauche, droite = st.columns([3, 2])

    with gauche:
        st.subheader("Répartition par statut")
        compte = resultat.par_statut()
        if compte:
            st.dataframe(
                [
                    {"Statut": statut.value, "Opérations": nombre}
                    for statut, nombre in sorted(compte.items(), key=lambda kv: kv[0].value)
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Aucune opération sur cette journée.")

    with droite:
        st.subheader("Contrôle d'équilibre")
        st.markdown(
            f"- Encaissements OM du jour : **{format_amount(resultat.total_om)}**\n"
            f"- Arrhes rapprochées : {format_amount(resultat.total_rapproche)}\n"
            f"- Recette du jour : {format_amount(resultat.total_recette_du_jour)}\n"
            f"- Commissions prélevées : {format_amount(resultat.total_commissions)}"
        )
        if resultat.invariant_respecte():
            st.success("Invariant vérifié : rapproché + recette = encaissements du jour.")
        else:
            st.error("Invariant rompu : le total ne se décompose pas. Résultat à ne pas exploiter.")

    st.markdown("---")
    if resultat.export_possible:
        st.success("Aucune anomalie bloquante : l'export comptable est ouvert.")
    else:
        detail = ", ".join(
            f"{nombre} {statut.value}" for statut, nombre in resultat.anomalies_bloquantes.items()
        )
        st.error(f"Export comptable bloqué — {detail}. À traiter dans **Anomalies & Écarts**.")
