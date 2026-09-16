"""Vue détaillée des appariements de la journée."""

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

    onglet_apparies, onglet_recette, onglet_manquants = st.tabs(
        [
            f"Arrhes rapprochées ({len(resultat.appariements)})",
            f"Recette du jour ({len(resultat.recette_du_jour)})",
            f"Arrhes sans encaissement ({len(resultat.arrhes_sans_om)})",
        ]
    )

    with onglet_apparies:
        if not resultat.appariements:
            st.caption("Aucune arrhe rapprochée sur cette journée.")
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
                    for appariement in resultat.appariements
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
        if not resultat.recette_du_jour:
            st.caption("Tous les encaissements de la journée correspondent à une arrhe.")
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
                    for t in resultat.recette_du_jour
                ],
                hide_index=True,
                width="stretch",
            )
            st.info(
                f"Ces {len(resultat.recette_du_jour)} encaissement(s), "
                f"{format_amount(resultat.total_recette_du_jour)} FCFA au total, ne sont pas "
                "des manquants : le journal des arrhes n'enregistre que les arrhes, "
                "le reste est la recette ordinaire du jour."
            )

    with onglet_manquants:
        if not resultat.arrhes_sans_om:
            st.caption("Toutes les arrhes de la journée ont trouvé leur encaissement.")
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
                    for ligne in resultat.arrhes_sans_om
                ],
                hide_index=True,
                width="stretch",
            )
            st.warning(
                "Arrhes enregistrées au journal sans encaissement Orange Money "
                "correspondant. Statut bloquant : l'export reste fermé."
            )
