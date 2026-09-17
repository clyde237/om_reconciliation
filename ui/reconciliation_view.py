"""Vue détaillée des appariements de la journée avec filtres et recherche multi-critères."""

import streamlit as st

from src.normalization.amounts import format_amount
from ui import session
from ui.components import render_header


def render_reconciliation_view():
    render_header(
        "⚖️ Rapprochement",
        "Une ligne par opération, avec la règle qui l'a produite",
    )

    resultat = session.exige_un_controle("le détail du rapprochement")
    if resultat is None:
        return

    session.selecteur_de_journee("journee_rapprochement", autoriser_toutes=True)
    resultat = session.resultat()

    # --- Barre de filtres multi-critères (Phase 6 & MoMo) ---
    from src.normalization.text import normalize_key

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        filtre_operateur = st.selectbox(
            "Filtrer par opérateur :",
            ["Tous les opérateurs", "Orange Money", "MTN Mobile Money"],
            key="rec_filtre_operateur",
        )

    with col_f2:
        comptes_om = ["Tous les comptes"] + sorted(
            {
                t.compte_agent
                for a in resultat.appariements
                for t in a.transactions
                if t.compte_agent
            }
            | {t.compte_agent for t in resultat.recette_du_jour if t.compte_agent}
        )
        filtre_compte = st.selectbox("Point de vente / compte :", comptes_om, key="rec_filtre_compte")

    with col_f3:
        recherche_texte = st.text_input(
            "🔍 Recherche rapide (client, référence, montant...) :",
            placeholder="Tapez un nom, numéro de téléphone, référence...",
            key="rec_recherche_texte",
        )

    q = recherche_texte.lower().strip() if recherche_texte else ""

    def _match_op(demande: str, element: str) -> bool:
        if demande == "Tous les opérateurs":
            return True
        return normalize_key(demande) in normalize_key(element)

    # Filtrage des appariements
    appariements_affiches = []
    for app in resultat.appariements:
        compte_match = (
            filtre_compte == "Tous les comptes"
            or any(t.compte_agent == filtre_compte for t in app.transactions)
        )
        if not compte_match:
            continue

        mode_j = app.lignes[0].mode_paiement if app.lignes else ""
        mode_t = getattr(app.transactions[0], "operateur", "Orange Money") if app.transactions else ""
        if filtre_operateur != "Tous les opérateurs":
            if not (_match_op(filtre_operateur, mode_j) or _match_op(filtre_operateur, mode_t)):
                continue

        if q:
            text_dans_lignes = any(
                q in l.client.lower() or q in l.reference_interne.lower() or q in str(l.montant)
                for l in app.lignes
            )
            text_dans_trans = any(
                q in t.reference.lower() or q in t.correspondant.lower() or q in str(t.montant) or q in t.libelle_compte.lower()
                for t in app.transactions
            )
            if not (text_dans_lignes or text_dans_trans):
                continue
        appariements_affiches.append(app)

    # Filtrage de la recette du jour
    recette_affichee = []
    for t in resultat.recette_du_jour:
        if filtre_compte != "Tous les comptes" and t.compte_agent != filtre_compte:
            continue
        op_t = getattr(t, "operateur", "Orange Money")
        if not _match_op(filtre_operateur, op_t):
            continue
        if q and not (q in t.reference.lower() or q in t.correspondant.lower() or q in str(t.montant) or q in t.libelle_compte.lower()):
            continue
        recette_affichee.append(t)

    # Filtrage des arrhes sans OM
    manquants_affiches = []
    for l in resultat.arrhes_sans_om:
        op_j = getattr(l, "mode_paiement", "Orange Money")
        if not _match_op(filtre_operateur, op_j):
            continue
        if q and not (q in l.client.lower() or q in l.reference_interne.lower() or q in str(l.montant)):
            continue
        manquants_affiches.append(l)

    # Préparation du téléchargement du tableau de rapprochement
    from src.analysis.reconciliation import construire_table
    from src.matching.appariement import ResultatRapprochement
    from src.reports import generer_excel_rapprochement_colore

    est_filtre = (filtre_compte != "Tous les comptes") or (filtre_operateur != "Tous les opérateurs") or bool(q)
    if est_filtre:
        res_export = ResultatRapprochement(
            periode=resultat.periode,
            appariements=appariements_affiches,
            recette_du_jour=recette_affichee,
            arrhes_sans_om=manquants_affiches,
        )
        lignes_export = construire_table(res_export)
    else:
        lignes_export = resultat

    total_affiches = len(appariements_affiches) + len(recette_affichee) + len(manquants_affiches)
    jour_choisi = session.journee_selectionnee()
    if jour_choisi == "TOUTES":
        nom_fichier = f"Rapprochement_Toutes_Journees_{resultat.periode.libelle.replace(' ', '_').replace('/', '-')}.xlsx"
        caption_texte = (
            f"📅 **Toutes les journées ({resultat.periode.libelle})** — **{total_affiches}** opération(s) affichée(s) "
            f"({len(appariements_affiches)} rapprochée(s), "
            f"{len(recette_affichee)} orpheline(s), "
            f"{len(manquants_affiches)} non retrouvée(s))"
        )
    else:
        nom_fichier = f"Rapprochement_{resultat.periode.libelle.replace(' ', '_').replace('/', '-')}.xlsx"
        caption_texte = (
            f"📅 Journée du **{resultat.periode.libelle}** — **{total_affiches}** opération(s) affichée(s) "
            f"({len(appariements_affiches)} rapprochée(s), "
            f"{len(recette_affichee)} orpheline(s), "
            f"{len(manquants_affiches)} non retrouvée(s))"
        )

    col_info, col_dl = st.columns([3, 2])
    with col_info:
        st.caption(caption_texte)
    with col_dl:
        st.download_button(
            label="📥 Télécharger le rapprochement Excel (.xlsx)",
            data=generer_excel_rapprochement_colore(lignes_export),
            file_name=nom_fichier,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            help="Exporte les 8 colonnes : Date, Client, Opérateur, Référence OM/MoMo, Montant journal, Montant Relevé, Statut, Observation, avec surbrillances vert / jaune / rouge.",
            use_container_width=True,
            disabled=total_affiches == 0,
        )

    # Onglets d'affichage
    onglet_apparies, onglet_recette, onglet_manquants = st.tabs(
        [
            f"Encaissements rapprochés ({len(resultat.appariements)})",
            f"Flux relevés orphelins ({len(resultat.recette_du_jour)})",
            f"Journal sans flux relevé ({len(resultat.arrhes_sans_om)})",
        ]
    )

    with onglet_apparies:
        if not appariements_affiches:
            st.caption("Aucun encaissement rapproché ne correspond aux filtres sélectionnés.")
        else:
            table_app = []
            for appariement in appariements_affiches:
                mj = appariement.lignes[0].mode_paiement if appariement.lignes else ""
                mt = (
                    getattr(appariement.transactions[0], "operateur", "Orange Money")
                    if appariement.transactions
                    else ""
                )
                op_lib = mj if normalize_key(mj) == normalize_key(mt) else f"{mj} ➔ {mt}"
                table_app.append(
                    {
                        "Client": appariement.client,
                        "Opérateur": op_lib,
                        "Référence": appariement.references_om,
                        "Montant journal": format_amount(appariement.montant_journal),
                        "Montant Relevé": format_amount(appariement.montant_om),
                        "Écart": format_amount(appariement.ecart),
                        "Statut": appariement.statut.value,
                        "Niveau": f"{int(appariement.niveau)} — {appariement.niveau.name.lower().replace('_', ' ')}",
                        "Score": f"{appariement.score:.0f}",
                    }
                )
            st.dataframe(
                table_app,
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Le niveau indique la règle qui a produit la correspondance. "
                "Les inversions de mode de paiement (OM ➔ MoMo ou MoMo ➔ OM) sont identifiées et signalées pour validation."
            )

    with onglet_recette:
        if not recette_affichee:
            st.caption("Aucun encaissement de recette ne correspond aux filtres sélectionnés.")
        else:
            st.dataframe(
                [
                    {
                        "Opérateur": getattr(t, "operateur", "Orange Money"),
                        "Heure": str(t.heure or ""),
                        "Référence": t.reference,
                        "Compte": t.compte_agent,
                        "Client / Numéro": t.libelle_compte or t.correspondant,
                        "Montant": format_amount(t.montant),
                        "Commission": format_amount(t.commission),
                    }
                    for t in recette_affichee
                ],
                hide_index=True,
                width="stretch",
            )
            st.info(
                f"Ces {len(resultat.recette_du_jour)} encaissement(s), "
                f"{format_amount(resultat.total_recette_du_jour)} FCFA au total, correspondent "
                "à des flux du relevé non identifiés dans les journaux des encaissements "
                "(recette ordinaire du jour)."
            )

    with onglet_manquants:
        if not manquants_affiches:
            st.caption("Aucune ligne du journal sans encaissement ne correspond aux filtres sélectionnés.")
        else:
            st.dataframe(
                [
                    {
                        "Opérateur": getattr(ligne, "mode_paiement", "Orange Money"),
                        "Ligne": ligne.ligne_source,
                        "Date": ligne.date_operation.strftime("%d/%m/%Y"),
                        "Client": ligne.client,
                        "Réservation": ligne.reference_interne,
                        "Montant": format_amount(ligne.montant),
                    }
                    for ligne in manquants_affiches
                ],
                hide_index=True,
                width="stretch",
            )
            st.warning(
                "Encaissements enregistrés au journal sans flux sur le relevé "
                "correspondant. Statut bloquant : l'export reste fermé."
            )
