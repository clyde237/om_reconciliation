"""Vue des anomalies : ce qui bloque l'export."""

import streamlit as st

from config.matching_config import BLOCKING_STATUSES
from src.normalization.amounts import format_amount
from ui import session
from ui.components import render_header


def render_anomalies_view():
    render_header(
        "⚠️ Anomalies & Écarts",
        "Les opérations qui exigent une décision avant toute comptabilisation",
    )

    resultat = session.exige_un_controle("la liste des anomalies")
    if resultat is None:
        return

    if resultat.export_possible:
        st.success(
            f"Journée du {resultat.periode.libelle} : aucune anomalie bloquante. "
            "L'export comptable est ouvert."
        )
    else:
        detail = ", ".join(
            f"{nombre} {statut.value}" for statut, nombre in resultat.anomalies_bloquantes.items()
        )
        st.error(f"Export bloqué — {detail}.")

    st.caption(
        "Statuts bloquants : "
        + ", ".join(sorted(statut.value for statut in BLOCKING_STATUSES))
    )
    st.markdown("---")

    gauche, droite = st.columns(2)

    with gauche:
        st.subheader("Écarts de montant")
        ecarts = [a for a in resultat.appariements if a.ecart]
        if not ecarts:
            st.info("Aucun écart de montant sur cette journée.")
        else:
            st.dataframe(
                [
                    {
                        "Client": a.client,
                        "Journal": format_amount(a.montant_journal),
                        "OM": format_amount(a.montant_om),
                        "Écart": format_amount(a.ecart),
                    }
                    for a in ecarts
                ],
                hide_index=True,
                width="stretch",
            )

    with droite:
        st.subheader("Doublons potentiels")
        if not resultat.doublons_journal and not resultat.doublons_om:
            st.info("Aucun doublon détecté.")
        else:
            for ligne in resultat.doublons_journal:
                st.caption(
                    f"Journal ligne {ligne.ligne_source} — {ligne.client}, "
                    f"{format_amount(ligne.montant)} FCFA"
                )
            for transaction in resultat.doublons_om:
                st.caption(
                    f"Relevé {transaction.reference} — {format_amount(transaction.montant)} FCFA"
                )
            st.warning(
                "Le doublon ne bloque pas l'export selon l'arbitrage retenu : "
                "à vérifier avant comptabilisation, sous peine de deux écritures "
                "pour un seul encaissement."
            )

    st.markdown("---")
    st.subheader("Transactions non exploitables")
    if not resultat.transactions_invalides:
        st.info("Aucune transaction en échec sur cette journée.")
    else:
        st.dataframe(
            [
                {
                    "Référence": t.reference,
                    "Service": t.service,
                    "Statut": t.statut,
                    "Montant": format_amount(t.montant or t.debit),
                }
                for t in resultat.transactions_invalides
            ],
            hide_index=True,
            width="stretch",
        )
