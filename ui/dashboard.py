"""Vue Tableau de bord & indicateurs du contrôle."""

import streamlit as st

from config.matching_config import MatchStatus
from src.normalization.amounts import format_amount
from ui import session
from ui.components import render_header, render_kpi_card


def _bandeau_mensuel() -> None:
    """Ce qu'aucune journée prise isolément ne montre : la couverture du mois."""
    mensuel = session.mensuel()
    if mensuel is None:
        return

    st.markdown(f"#### Contrôle du mois — {mensuel.periode.libelle}")
    a, b, c = st.columns(3)
    with a:
        render_kpi_card(
            "Journées contrôlées",
            str(mensuel.nb_journees_deposees),
            f"{len(mensuel.non_couvertes)} sans journal déposé",
        )
    with b:
        render_kpi_card(
            "Couverture du relevé",
            f"{mensuel.taux_couverture:.1f} %",
            f"{format_amount(mensuel.total_om_controle)} FCFA contrôlés",
        )
    with c:
        render_kpi_card(
            "Hors contrôle",
            f"{format_amount(mensuel.total_om_non_controle)} FCFA",
            "encaissements sans journal",
        )

    if not mensuel.complet:
        st.warning(
            f"{len(mensuel.non_couvertes)} journée(s) du relevé n'ont pas reçu leur journal. "
            "Le contrôle du mois est partiel."
        )
    if not mensuel.export_possible:
        jours = ", ".join(j.periode.libelle for j in mensuel.journees_bloquantes)
        st.error(f"Export du mois bloqué par : {jours}.")
    st.markdown("---")


def render_dashboard():
    render_header(
        "📊 Tableau de Bord Financier",
        "Résultat du contrôle de la journée : encaissements rapprochés, recette et anomalies",
    )

    resultat = session.exige_un_controle("les indicateurs de la journée")
    if resultat is None:
        return

    _bandeau_mensuel()
    session.selecteur_de_journee("journee_dashboard")
    resultat = session.resultat()
    st.caption(f"Journée contrôlée : **{resultat.periode.libelle}**")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            "Taux de rapprochement",
            f"{resultat.taux_rapprochement:.1f} %",
            f"{len(resultat.appariements)} encaissement(s) rapproché(s)",
        )
    with c2:
        render_kpi_card(
            "Encaissements OM",
            f"{format_amount(resultat.total_om)} FCFA",
            f"{len(resultat.appariements) + len(resultat.recette_du_jour)} opération(s)",
        )
    with c3:
        render_kpi_card(
            "Encaissements rapprochés",
            f"{format_amount(resultat.total_rapproche)} FCFA",
            "journal des encaissements",
        )
    with c4:
        render_kpi_card(
            "Recette du jour",
            f"{format_amount(resultat.total_recette_du_jour)} FCFA",
            f"{len(resultat.recette_du_jour)} flux OM orphelin(s)",
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

    from src.reports.excel_report import ExcelReportGenerator

    st.markdown("---")
    st.subheader("📑 Livrable d'Audit")
    controle_mois = session.mensuel()
    if controle_mois and len(controle_mois.journees) > 1:
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 Rapport mensuel consolidé (.xlsx)",
                data=ExcelReportGenerator().generate_bytes(controle_mois),
                file_name=f"Rapprochement_OM_Mensuel_{controle_mois.periode.libelle.replace(' ', '_').replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                help="Génère le classeur Excel consolidé à 7 feuilles pour toutes les journées déposées.",
            )
        with col_dl2:
            st.download_button(
                label=f"📥 Rapport journée du {resultat.periode.libelle} (.xlsx)",
                data=ExcelReportGenerator().generate_bytes(resultat),
                file_name=f"Rapprochement_OM_{resultat.periode.libelle.replace(' ', '_').replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Génère le classeur Excel à 7 feuilles pour la seule journée sélectionnée.",
            )
    else:
        st.download_button(
            label="📥 Télécharger le rapport d'audit complet (.xlsx)",
            data=ExcelReportGenerator().generate_bytes(resultat),
            file_name=f"Rapprochement_OM_{resultat.periode.libelle.replace(' ', '_').replace('/', '-')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            help="Génère le classeur Excel à 7 feuilles conforme au cahier des charges.",
        )
