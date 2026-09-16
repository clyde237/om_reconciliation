"""Vue des anomalies et interface de validation humaine (§10, §14 et §19)."""

import streamlit as st

from config.matching_config import BLOCKING_STATUSES, MatchStatus
from src.analysis.anomalies import extraire_anomalies
from src.analysis.monthly_summary import INTITULES_COMPTES_OM
from src.analysis.reconciliation import LigneRapprochement, construire_table
from src.analysis.validation import (
    DecisionType,
    GestionnaireVerrou,
    JournalDecisions,
    cle_ligne_rapprochement,
)
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

    journal_dec = session.decisions()
    verrou = GestionnaireVerrou.evaluer(resultat, journal_dec)

    if verrou.export_autorise:
        st.success(
            f"Journée du {resultat.periode.libelle} : aucune anomalie bloquante. "
            "L'export comptable est ouvert."
        )
    else:
        st.error(
            f"**Export bloqué** — {verrou.motif_blocage} "
            "Chaque anomalie doit être instruite (validée ou rejetée) avant comptabilisation."
        )

    st.caption(
        "Statuts bloquants par défaut : "
        + ", ".join(sorted(statut.value for statut in BLOCKING_STATUSES))
    )
    st.markdown("---")

    # --- Filtres de recherche ---
    table_complete = construire_table(resultat)
    toutes_anomalies = extraire_anomalies(table_complete)

    if toutes_anomalies:
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            statuts_dispos = ["Tous"] + sorted({a.statut.value for a in toutes_anomalies})
            filtre_statut = st.selectbox("Filtrer par statut", statuts_dispos, key="filtre_ano_statut")
        with col_f2:
            comptes_dispos = ["Tous"] + sorted({a.compte_om for a in toutes_anomalies if a.compte_om})
            filtre_compte = st.selectbox("Filtrer par compte OM", comptes_dispos, key="filtre_ano_compte")
        with col_f3:
            recherche = st.text_input("🔍 Recherche rapide (client, référence...)", key="filtre_ano_recherche")

        anomalies_filtrees = toutes_anomalies
        if filtre_statut != "Tous":
            anomalies_filtrees = [a for a in anomalies_filtrees if a.statut.value == filtre_statut]
        if filtre_compte != "Tous":
            anomalies_filtrees = [a for a in anomalies_filtrees if a.compte_om == filtre_compte]
        if recherche:
            q = recherche.lower().strip()
            anomalies_filtrees = [
                a
                for a in anomalies_filtrees
                if q in a.client.lower() or q in a.reference.lower() or q in a.observation.lower()
            ]
    else:
        anomalies_filtrees = []

    # --- Vue par nature ---
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

    # --- SECTION DE VALIDATION HUMAINE (§14 & §19) ---
    st.markdown("---")
    st.subheader("📝 Instruction & Validation Humaine des Anomalies")
    st.caption(
        "Application du principe fondamental : une anomalie n'entre pas en comptabilité "
        "sans validation explicite et motivée par le contrôleur."
    )

    if not toutes_anomalies:
        st.success("Aucune anomalie à instruire sur cette journée.")
        return

    # Tableau synthétique avec état des décisions
    lignes_tableau = []
    for a in anomalies_filtrees:
        dec = journal_dec.obtenir(a)
        decision_txt = "⏳ EN ATTENTE"
        auteur_txt = "-"
        motif_txt = "-"
        if dec:
            if dec.decision is DecisionType.VALIDE:
                decision_txt = "✅ VALIDÉ"
            elif dec.decision is DecisionType.REJETE:
                decision_txt = "❌ REJETÉ"
            auteur_txt = dec.auteur
            motif_txt = dec.motif

        lignes_tableau.append(
            {
                "Client": a.client,
                "Référence": a.reference,
                "Statut": a.statut.value,
                "Écart": format_amount(a.ecart),
                "Décision": decision_txt,
                "Auteur": auteur_txt,
                "Motif": motif_txt,
            }
        )

    st.dataframe(lignes_tableau, hide_index=True, width="stretch")

    # Formulaire d'instruction individuelle
    st.markdown("#### Arbitrer une anomalie")
    options_anomalies = {
        f"{a.client} ({a.statut.value}, écart: {format_amount(a.ecart)} FCFA) - {a.reference}": a
        for a in toutes_anomalies
    }

    choix_cle = st.selectbox("Sélectionner l'opération à instruire :", list(options_anomalies.keys()))
    anomalie_choisie = options_anomalies[choix_cle]

    col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
    with col_act1:
        action_choisie = st.radio("Action", ["Valider l'anomalie", "Rejeter l'anomalie"])
    with col_act2:
        auteur_input = st.text_input("Auteur / Contrôleur", value="Contrôleur de gestion")
    with col_act3:
        motif_input = st.text_input("Motif / Justification", placeholder="Ex: Écart justifié par frais...")

    col_btn1, col_btn2 = st.columns([2, 2])
    with col_btn1:
        if st.button("💾 Enregistrer la décision", type="primary"):
            if action_choisie == "Valider l'anomalie":
                journal_dec.valider(anomalie_choisie, auteur=auteur_input, motif=motif_input)
                st.toast(f"Anomalie validée pour {anomalie_choisie.client}")
            else:
                journal_dec.rejeter(anomalie_choisie, auteur=auteur_input, motif=motif_input)
                st.toast(f"Anomalie rejetée pour {anomalie_choisie.client}")
            st.rerun()

    with col_btn2:
        if st.button("⚡ Valider toutes les anomalies restantes de la période"):
            nb = journal_dec.valider_toutes(
                toutes_anomalies,
                auteur=auteur_input,
                motif=motif_input or "Validation groupée de la période",
            )
            st.toast(f"{nb} anomalie(s) validée(s) !")
            st.rerun()
