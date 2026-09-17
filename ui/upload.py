"""Vue de téléversement et lancement du contrôle mensuel."""

import streamlit as st

from src.matching import ControleMensuel
from src.normalization.amounts import format_amount
from src.readers import EncaissementsReader, MomoReader, OMReader
from ui import session
from ui.components import render_header


def render_upload_view():
    """Étape 1 : déposer les journaux du mois et les relevés OM/MoMo, puis lancer le contrôle."""
    render_header(
        "📥 Importation des Fichiers",
        "Les journaux des encaissements portent les journées ; les relevés mensuels couvrent les flux OM et MoMo",
    )

    colonne_journaux, colonne_om, colonne_momo = st.columns(3)

    with colonne_journaux:
        st.subheader("1. Journaux des encaissements")
        journaux = st.file_uploader(
            "Un journal par journée ou consolidé mensuel",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key="upload_encaissements",
        )
        if journaux:
            st.caption(f"{len(journaux)} journal/journaux sélectionné(s)")

    with colonne_om:
        st.subheader("2. Relevé Orange Money")
        fichier_om = st.file_uploader(
            "Relevé mensuel Orange Money", type=["xlsx", "xls"], key="upload_om"
        )
        if fichier_om:
            st.caption(f"Sélectionné : {fichier_om.name}")

    with colonne_momo:
        st.subheader("3. Relevé MTN MoMo")
        fichier_momo = st.file_uploader(
            "Relevé mensuel MTN Mobile Money (optionnel)",
            type=["xlsx", "xls"],
            key="upload_momo",
            help="Permet de vérifier les flux MoMo et de détecter les inversions de saisie de l'opérateur (OM ➔ MoMo).",
        )
        if fichier_momo:
            st.caption(f"Sélectionné : {fichier_momo.name}")

    st.markdown("---")

    manquants = []
    if not journaux:
        manquants.append("au moins un journal des encaissements")
    if fichier_om is None:
        manquants.append("le relevé Orange Money")
    if manquants:
        st.info(f"Il manque {' et '.join(manquants)} pour lancer le contrôle.")

    if st.button(
        "🚀 Lancer l'analyse et le rapprochement",
        type="primary",
        disabled=bool(manquants),
    ):
        _lancer(journaux, fichier_om, fichier_momo)

    if session.erreur():
        st.error(session.erreur())
    elif session.mensuel() is not None:
        _rapport_import()


def _lancer(journaux, fichier_om, fichier_momo=None) -> None:
    with st.status("Contrôle en cours…", expanded=True) as etat:
        try:
            st.write(f"Lecture de {len(journaux)} journal/journaux…")
            lectures, illisibles = [], []
            barre = st.progress(0.0)
            for rang, fichier in enumerate(journaux, start=1):
                try:
                    with session.fichier_temporaire(fichier) as chemin:
                        lectures.append(EncaissementsReader(chemin).read())
                except Exception as erreur:  # noqa: BLE001
                    illisibles.append((fichier.name, str(erreur)))
                barre.progress(rang / len(journaux))

            if not lectures:
                raise ValueError(
                    "Aucun journal n'a pu être lu. "
                    + " ".join(f"{nom} : {motif}" for nom, motif in illisibles)
                )
            for nom, motif in illisibles:
                st.warning(f"{nom} ignoré — {motif}")

            st.write("Lecture du relevé Orange Money…")
            with session.fichier_temporaire(fichier_om) as chemin:
                releve_om = OMReader(chemin).read()
            st.write(f"{len(releve_om.comptes)} compte(s) OM, {len(releve_om.transactions)} transaction(s)")

            releve_momo = None
            if fichier_momo is not None:
                st.write("Lecture du relevé MTN Mobile Money…")
                with session.fichier_temporaire(fichier_momo) as chemin:
                    releve_momo = MomoReader(chemin).read()
                st.write(f"MoMo : {len(releve_momo.transactions)} transaction(s) lue(s)")

            st.write("Rapprochement combiné en cours…")
            mensuel = ControleMensuel().run(lectures, releve_om, releve_momo=releve_momo)
            session.enregistrer(lectures, releve_om, mensuel, releve_momo=releve_momo)

            etat.update(
                label=f"Contrôle terminé — {mensuel.nb_journees_deposees} journée(s) sur "
                f"{mensuel.periode.libelle}",
                state="complete",
                expanded=False,
            )
        except Exception as erreur:  # noqa: BLE001 — remonté tel quel à l'utilisateur
            session.signaler_erreur(f"Le contrôle a échoué : {erreur}")
            etat.update(label="Contrôle interrompu", state="error")


def _rapport_import() -> None:
    """Ce qui a été lu, ce qui a été écarté, et ce qui manque à l'appel."""
    mensuel, releve_om = session.mensuel(), session.releve()
    releve_momo = session.releve_momo()

    st.success(
        f"{mensuel.nb_journees_deposees} journée(s) contrôlée(s) sur {mensuel.periode.libelle} — "
        f"{format_amount(mensuel.total_om_controle)} FCFA rapprochés, "
        f"couverture {mensuel.taux_couverture:.1f} % des relevés."
    )

    if mensuel.doublons_de_journee:
        for jour, fichiers in mensuel.doublons_de_journee.items():
            st.error(
                f"La journée du {jour:%d/%m/%Y} a été déposée plusieurs fois "
                f"({', '.join(fichiers)}). Seul le premier journal a été retenu."
            )
    if mensuel.hors_releve:
        jours = ", ".join(jour.strftime("%d/%m/%Y") for jour in mensuel.hors_releve)
        st.warning(f"Journaux hors des relevés déposés : {jours}.")

    nb_cols = 3 if releve_momo else 2
    cols = st.columns(nb_cols)

    with cols[0]:
        st.markdown("**Journaux des encaissements**")
        journaux = session.journaux()
        total_om_lu = sum((lecture.total_om for lecture in journaux), 0)
        total_momo_lu = sum((lecture.total_momo for lecture in journaux), 0)
        st.write(
            f"- {len(journaux)} journal/journaux lu(s)\n"
            f"- {sum(len(l.mouvements) for l in journaux)} mouvement(s) mobile money\n"
            f"- total Orange Money : {format_amount(total_om_lu)} FCFA\n"
            f"- total MTN MoMo : {format_amount(total_momo_lu)} FCFA"
        )
        ecarts = [l for l in journaux if l.ecart_au_recapitulatif()]
        if ecarts:
            st.error(
                "Lecture incomplète (OM) : "
                + ", ".join(
                    f"{l.source} (écart {format_amount(l.ecart_au_recapitulatif())})"
                    for l in ecarts
                )
            )
        else:
            st.caption("Chaque journal est conforme au récapitulatif OM qu'il annonce.")

    with cols[1]:
        st.markdown("**Relevé Orange Money**")
        st.write(
            f"- {releve_om.lot.resume()}\n"
            f"- {len(releve_om.commissions)} ligne(s) de commission isolée(s)\n"
            f"- période déclarée : "
            f"{releve_om.periode_declaree.libelle if releve_om.periode_declaree else 'non indiquée'}"
        )
        with st.expander(f"{len(releve_om.comptes)} sous-relevé(s)"):
            for compte in releve_om.comptes:
                nombre = sum(1 for t in releve_om.transactions if t.compte_agent == compte.numero)
                st.caption(f"{compte.numero} — {compte.point_de_vente} ({nombre} transactions)")

    if releve_momo and nb_cols == 3:
        with cols[2]:
            st.markdown("**Relevé MTN MoMo**")
            total_momo = sum((t.montant for t in releve_momo.transactions), 0)
            st.write(
                f"- {releve_momo.lot.resume()}\n"
                f"- total paiements : {format_amount(total_momo)} FCFA\n"
                f"- période déclarée : "
                f"{releve_momo.periode_declaree.libelle if releve_momo.periode_declaree else 'non indiquée'}"
            )

    if mensuel.non_couvertes:
        st.markdown("---")
        st.warning(
            f"**{len(mensuel.non_couvertes)} journée(s) du relevé sans journal déposé** — "
            f"{format_amount(mensuel.total_om_non_controle)} FCFA échappent au contrôle."
        )
        st.dataframe(
            [
                {
                    "Journée": non.jour.strftime("%d/%m/%Y"),
                    "Transactions": non.nb_transactions,
                    "Montant": format_amount(non.total),
                }
                for non in mensuel.non_couvertes
            ],
            hide_index=True,
            width="stretch",
        )
