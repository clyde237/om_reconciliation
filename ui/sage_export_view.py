"""Vue de génération et d'export des écritures Sage."""

import streamlit as st

from config.sage_config import DEFAULT_SAGE_CONFIG
from src.normalization.amounts import format_amount
from ui import session
from ui.components import render_header


def render_sage_export_view():
    render_header(
        "📑 Export Comptable Sage 100",
        "La comptabilisation ne suit le contrôle qu'une fois les anomalies levées",
    )

    resultat = session.exige_un_controle("l'écriture comptable")
    if resultat is None:
        return

    session.selecteur_de_journee("journee_sage_export")
    resultat = session.resultat()

    from src.analysis.validation import GestionnaireVerrou
    journal_dec = session.decisions()
    verrou = GestionnaireVerrou.evaluer(resultat, journal_dec)

    if verrou.export_autorise:
        st.success(
            f"Journée du {resultat.periode.libelle} : aucune anomalie bloquante. "
            "L'export sera ouvert dès que la génération sera disponible."
        )
    else:
        st.error(
            f"**Export bloqué** — {verrou.motif_blocage}. Une opération du journal ne devient pas une "
            "écriture comptable du seul fait qu'elle existe : elle doit être rapprochée, "
            "contrôlée, puis validée."
        )

    st.markdown("---")
    st.subheader("Écritures qui seront générées")
    st.caption(
        "Trois natures selon le journal des encaissements : les arrhes individuelles "
        "(compte 41910000), les factures directes (compte 41110000) et les flux OM orphelins "
        "(compte 70600000)."
    )
    from src.normalization.amounts import ZERO

    nb_arrhes = sum(1 for a in resultat.appariements if any(l.est_arrhe for l in a.lignes))
    total_arrhes = sum((a.montant_journal for a in resultat.appariements if any(l.est_arrhe for l in a.lignes)), ZERO)

    nb_factures = sum(1 for a in resultat.appariements if not any(l.est_arrhe for l in a.lignes))
    total_factures = sum((a.montant_journal for a in resultat.appariements if not any(l.est_arrhe for l in a.lignes)), ZERO)

    st.dataframe(
        [
            {
                "Nature": "Arrhes individuelles",
                "Gabarit du libellé": DEFAULT_SAGE_CONFIG.label_template_arrhes,
                "Lignes": nb_arrhes,
                "Montant": format_amount(total_arrhes),
            },
            {
                "Nature": "Factures directes (Kotibé, Baleng, etc.)",
                "Gabarit du libellé": "ENCAISSEMENT FACTURE {ref}",
                "Lignes": nb_factures,
                "Montant": format_amount(total_factures),
            },
            {
                "Nature": "Recette du jour (flux OM orphelins)",
                "Gabarit du libellé": DEFAULT_SAGE_CONFIG.label_template_recette,
                "Lignes": 1 if resultat.recette_du_jour else 0,
                "Montant": format_amount(resultat.total_recette_du_jour),
            },
        ],
        hide_index=True,
        width="stretch",
    )

    st.markdown("---")
    gauche, droite = st.columns(2)
    with gauche:
        st.selectbox("Format d'export", ["PNM (format d'import Sage)", "TXT (délimité)", "Excel (.xlsx)"], disabled=True)
        st.text_input("Code journal", value=DEFAULT_SAGE_CONFIG.journal_code, disabled=True)
    with droite:
        st.text_input("Compte de transfert", value=DEFAULT_SAGE_CONFIG.transfer_account, disabled=True)
        st.text_input("Contrepartie arrhes", value=DEFAULT_SAGE_CONFIG.arrhes_account, disabled=True)

    st.button("📥 Générer l'écriture comptable", type="primary", disabled=True)
    st.info(
        "La génération n'est pas encore développée. Elle attend deux étapes : la "
        "validation humaine des anomalies, puis le mapping comptable. Le format PNM "
        "est en revanche déjà spécifié et testé sur quatre fichiers Sage réels — "
        "voir `docs/format_pnm.md`. Les valeurs ci-dessus restent à confirmer avec "
        "le comptable."
    )
