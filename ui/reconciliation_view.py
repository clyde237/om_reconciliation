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

    # --- Barre de filtres multi-critères (Phase 6) ---
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        comptes_om = ["Tous les comptes"] + sorted(
            {
                t.compte_agent
                for a in resultat.appariements
                for t in a.transactions
                if t.compte_agent
            }
            | {t.compte_agent for t in resultat.recette_du_jour if t.compte_agent}
        )
        filtre_compte = st.selectbox("Filtrer par point de vente / compte OM :", comptes_om, key="rec_filtre_compte")

    with col_f2:
        recherche_texte = st.text_input(
            "🔍 Recherche rapide (client, référence, montant...) :",
            placeholder="Tapez un nom, numéro de téléphone, référence...",
            key="rec_recherche_texte",
        )

    q = recherche_texte.lower().strip() if recherche_texte else ""

    # Filtrage des appariements
    appariements_affiches = []
    for app in resultat.appariements:
        compte_match = (
            filtre_compte == "Tous les comptes"
            or any(t.compte_agent == filtre_compte for t in app.transactions)
        )
        if not compte_match:
            continue

        if q:
            text_dans_lignes = any(
                q in l.client.lower() or q in l.reference_interne.lower() or q in str(l.montant)
                for l in app.lignes
            )
            text_dans_trans = any(
                q in t.reference.lower() or q in t.correspondant.lower() or q in str(t.montant)
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
        if q and not (q in t.reference.lower() or q in t.correspondant.lower() or q in str(t.montant)):
            continue
        recette_affichee.append(t)

    # Filtrage des arrhes sans OM
    manquants_affiches = []
    for l in resultat.arrhes_sans_om:
        if q and not (q in l.client.lower() or q in l.reference_interne.lower() or q in str(l.montant)):
            continue
        manquants_affiches.append(l)

    # Préparation du téléchargement du tableau de rapprochement
    from src.analysis.reconciliation import construire_table
    from src.matching.appariement import ResultatRapprochement
    from src.reports import generer_excel_rapprochement_colore

    est_filtre = (filtre_compte != "Tous les comptes") or bool(q)
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
            help="Exporte les 7 colonnes : Date, Client, Référence OM, Montant journal, Montant OM, Statut, Observation, avec surbrillances vert / jaune / rouge.",
            use_container_width=True,
            disabled=total_affiches == 0,
        )

    # Onglets d'affichage
    onglet_apparies, onglet_recette, onglet_manquants = st.tabs(
        [
            f"Encaissements rapprochés ({len(resultat.appariements)})",
            f"Flux OM orphelins ({len(resultat.recette_du_jour)})",
            f"Journal sans flux OM ({len(resultat.arrhes_sans_om)})",
        ]
    )

    with onglet_apparies:
        if not appariements_affiches:
            st.caption("Aucun encaissement rapproché ne correspond aux filtres sélectionnés.")
        else:
            st.dataframe(
                [
                    {
                        "Client": appariement.client,
                        "Référence OM": appariement.references_om,
                        "Montant journal": format_amount(appariement.montant_journal),
                        "Montant OM": format_amount(appariement.montant_om),
                        "Écart": format_amount(appariement.ecart),
                        "Statut": appariement.statut.value,
                        "Niveau": f"{int(appariement.niveau)} — {appariement.niveau.name.lower().replace('_', ' ')}",
                        "Score": f"{appariement.score:.0f}",
                    }
                    for appariement in appariements_affiches
                ],
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Le niveau indique la règle qui a produit la correspondance. "
                "Sur ces sources, les niveaux 1 et 3 ne trouvent rien : le journal ne "
                "porte aucune référence Orange Money et le relevé identifie le client "
                "par son numéro de téléphone."
            )

    with onglet_recette:
        if not recette_affichee:
            st.caption("Aucun encaissement de recette ne correspond aux filtres sélectionnés.")
        else:
            st.dataframe(
                [
                    {
                        "Heure": str(t.heure or ""),
                        "Référence": t.reference,
                        "Compte": t.compte_agent,
                        "Correspondant": t.correspondant,
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
                "à des flux Orange Money du relevé non identifiés dans les journaux des encaissements "
                "(recette ordinaire du jour)."
            )

    with onglet_manquants:
        if not manquants_affiches:
            st.caption("Aucune ligne du journal sans encaissement ne correspond aux filtres sélectionnés.")
        else:
            st.dataframe(
                [
                    {
                        "Ligne": ligne.ligne_source,
                        "Heure de saisie": ligne.date_operation.strftime("%H:%M"),
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
                "Encaissements enregistrés au journal sans flux Orange Money "
                "correspondant. Statut bloquant : l'export reste fermé."
            )
