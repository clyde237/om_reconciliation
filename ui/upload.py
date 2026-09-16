"""Vue de téléversement et lancement du contrôle."""

import streamlit as st

from src.matching import ReconciliationMatcher
from src.normalization.amounts import format_amount
from src.readers import JournalReader, OMReader
from ui import session
from ui.components import render_header


def render_upload_view():
    """Étape 1 : importer les deux sources et lancer le contrôle de la journée."""
    render_header(
        "📥 Importation des Fichiers",
        "Le journal des arrhes porte la période ; le relevé mensuel est filtré dessus",
    )

    colonne_journal, colonne_om = st.columns(2)

    with colonne_journal:
        st.subheader("1. Journal des Arrhes")
        fichier_journal = st.file_uploader(
            "Export du journal (une journée)", type=["xlsx", "xls"], key="upload_arrhes"
        )
        if fichier_journal:
            st.caption(f"Sélectionné : {fichier_journal.name}")

    with colonne_om:
        st.subheader("2. Relevé Orange Money")
        fichier_om = st.file_uploader(
            "Relevé mensuel Orange Money", type=["xlsx", "xls"], key="upload_om"
        )
        if fichier_om:
            st.caption(f"Sélectionné : {fichier_om.name}")

    st.markdown("---")

    manquants = [
        nom
        for nom, fichier in (("le journal des arrhes", fichier_journal), ("le relevé Orange Money", fichier_om))
        if fichier is None
    ]
    if manquants:
        st.info(f"Il manque {' et '.join(manquants)} pour lancer le contrôle.")

    if st.button(
        "🚀 Lancer l'analyse et le rapprochement",
        type="primary",
        disabled=bool(manquants),
    ):
        _lancer(fichier_journal, fichier_om)

    if session.erreur():
        st.error(session.erreur())
    elif session.resultat() is not None:
        _rapport_import()


def _lancer(fichier_journal, fichier_om) -> None:
    with st.status("Contrôle en cours…", expanded=True) as etat:
        try:
            st.write("Lecture du journal des arrhes…")
            with session.fichier_temporaire(fichier_journal) as chemin:
                journal = JournalReader(chemin).read()
            st.write(f"Période contrôlée : **{journal.periode.libelle}**")

            st.write("Lecture du relevé Orange Money…")
            with session.fichier_temporaire(fichier_om) as chemin:
                releve = OMReader(chemin).read()
            st.write(f"{len(releve.comptes)} compte(s), {len(releve.transactions)} transaction(s)")

            if releve.periode_declaree and not releve.periode_declaree.contient(journal.periode.debut):
                st.warning(
                    f"Le relevé couvre {releve.periode_declaree.libelle} et ne contient pas "
                    f"la journée {journal.periode.libelle}. Le rapprochement sera vide."
                )

            st.write("Rapprochement…")
            resultat = ReconciliationMatcher().run(
                journal.periode, journal.lignes, releve.transactions
            )
            session.enregistrer(journal, releve, resultat)
            etat.update(
                label=f"Contrôle du {journal.periode.libelle} terminé", state="complete", expanded=False
            )
        except Exception as erreur:  # noqa: BLE001 — remonté tel quel à l'utilisateur
            session.signaler_erreur(f"Le contrôle a échoué : {erreur}")
            etat.update(label="Contrôle interrompu", state="error")


def _rapport_import() -> None:
    """Ce qui a été lu, et surtout ce qui a été écarté et pourquoi."""
    journal, releve, resultat = session.journal(), session.releve(), session.resultat()

    st.success(
        f"Journée du {resultat.periode.libelle} — "
        f"{len(resultat.appariements)} arrhe(s) rapprochée(s) sur "
        f"{len(resultat.appariements) + len(resultat.arrhes_sans_om)}, "
        f"recette du jour {format_amount(resultat.total_recette_du_jour)} FCFA."
    )

    gauche, droite = st.columns(2)
    with gauche:
        st.markdown("**Journal des arrhes**")
        st.write(
            f"- {journal.lot.resume()}\n"
            f"- dont {len(journal.lignes_orange_money)} en Orange Money, "
            f"total {format_amount(journal.total_orange_money)} FCFA"
        )
        if journal.periode_deduite:
            st.warning("Période absente de l'en-tête : déduite des lignes datées.")
        if journal.lot.rejets:
            with st.expander(f"{len(journal.lot.rejets)} ligne(s) écartée(s)"):
                for numero, motif in journal.lot.rejets:
                    st.caption(f"ligne {numero} — {motif}")

    with droite:
        st.markdown("**Relevé Orange Money**")
        st.write(
            f"- {releve.lot.resume()}\n"
            f"- {len(releve.commissions)} ligne(s) de commission isolée(s)\n"
            f"- période déclarée : "
            f"{releve.periode_declaree.libelle if releve.periode_declaree else 'non indiquée'}"
        )
        with st.expander(f"{len(releve.comptes)} sous-relevé(s)"):
            for compte in releve.comptes:
                nombre = sum(1 for t in releve.transactions if t.compte_agent == compte.numero)
                st.caption(f"{compte.numero} — {compte.point_de_vente} ({nombre} transactions)")
