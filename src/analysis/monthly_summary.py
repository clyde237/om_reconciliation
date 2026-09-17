"""Synthèse mensuelle et ventilation des flux par point de vente / compte Orange Money.

Le fichier de relevé Orange Money regroupe quatre points de vente / comptes distincts :
- 698186110 : AGREGATEUR INTERNE OM
- 656009773 : RELAIS DJELEN — RECEPTION
- 691829711 : HOTEL ZINGANA SA — KOTIBE
- 696948928 : HOTEL ZINGANA SA — RESTAURANT BALENG

Ce module agrège les résultats de rapprochement par mois et ventile l'activité par compte.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Sequence, Union

from config.matching_config import MatchStatus
from src.analysis.reconciliation import (
    ControlesGlobaux,
    LigneRapprochement,
    calculer_controles,
    construire_table,
)
from src.matching.appariement import ResultatRapprochement
from src.normalization.amounts import ZERO

INTITULES_COMPTES_OM: dict[str, str] = {
    "698186110": "AGREGATEUR INTERNE OM",
    "656009773": "RELAIS DJELEN — RECEPTION",
    "691829711": "HOTEL ZINGANA SA — KOTIBE",
    "696948928": "HOTEL ZINGANA SA — RESTAURANT BALENG",
}


@dataclass(frozen=True)
class VentilationCompteOM:
    """Ventilation des flux pour un point de vente / compte Orange Money donné."""

    compte: str
    intitule: str
    nb_transactions: int
    total_om: Decimal
    total_rapproche: Decimal
    total_recette: Decimal
    total_commissions: Decimal = ZERO

    @property
    def taux_rapprochement(self) -> float:
        if not self.total_om:
            return 0.0
        return 100.0 * float(self.total_rapproche) / float(self.total_om)


@dataclass(frozen=True)
class SyntheseJournaliere:
    """Ligne récapitulative d'une journée contrôlée."""

    jour: date
    nb_arrhes: int
    total_arrhes: Decimal
    nb_om: int
    total_om: Decimal
    total_rapproche: Decimal
    total_recette: Decimal
    total_ecarts: Decimal
    statut_global: str


@dataclass
class SyntheseMensuelle:
    """Synthèse périodique consolidée pour le rapport d'audit et la direction."""

    periode_libelle: str
    controles_globaux: ControlesGlobaux
    ventilation_comptes: list[VentilationCompteOM] = field(default_factory=list)
    details_journaliers: list[SyntheseJournaliere] = field(default_factory=list)


def ventiler_par_compte(
    resultat: Union[ResultatRapprochement, Sequence[ResultatRapprochement]],
) -> list[VentilationCompteOM]:
    """Calcule la ventilation par compte Orange Money à partir d'un ou plusieurs résultats."""
    resultats = [resultat] if isinstance(resultat, ResultatRapprochement) else list(resultat)

    donnees_comptes: dict[str, dict] = {
        compte: {
            "intitule": intitule,
            "nb_transactions": 0,
            "total_om": ZERO,
            "total_rapproche": ZERO,
            "total_recette": ZERO,
            "total_commissions": ZERO,
        }
        for compte, intitule in INTITULES_COMPTES_OM.items()
    }

    def _get_entry(compte_id: str) -> dict:
        cid = compte_id.strip() if compte_id else "AUTRE"
        if cid not in donnees_comptes:
            donnees_comptes[cid] = {
                "intitule": INTITULES_COMPTES_OM.get(cid, f"Compte {cid}"),
                "nb_transactions": 0,
                "total_om": ZERO,
                "total_rapproche": ZERO,
                "total_recette": ZERO,
                "total_commissions": ZERO,
            }
        return donnees_comptes[cid]

    for res in resultats:
        for app in res.appariements:
            for t in app.transactions:
                entry = _get_entry(t.compte_agent)
                entry["nb_transactions"] += 1
                entry["total_om"] += t.montant
                entry["total_rapproche"] += t.montant
                entry["total_commissions"] += t.commission

        for t in res.recette_du_jour:
            entry = _get_entry(t.compte_agent)
            entry["nb_transactions"] += 1
            entry["total_om"] += t.montant
            entry["total_recette"] += t.montant
            entry["total_commissions"] += t.commission

        for t in res.transactions_invalides:
            entry = _get_entry(t.compte_agent)
            entry["nb_transactions"] += 1
            entry["total_commissions"] += t.commission

    ventilations: list[VentilationCompteOM] = []
    for c_id, vals in donnees_comptes.items():
        if vals["nb_transactions"] > 0 or vals["total_om"] > ZERO or c_id in INTITULES_COMPTES_OM:
            ventilations.append(
                VentilationCompteOM(
                    compte=c_id,
                    intitule=vals["intitule"],
                    nb_transactions=vals["nb_transactions"],
                    total_om=vals["total_om"],
                    total_rapproche=vals["total_rapproche"],
                    total_recette=vals["total_recette"],
                    total_commissions=vals["total_commissions"],
                )
            )

    return sorted(ventilations, key=lambda v: (v.compte != "698186110", v.compte))


def generer_synthese_mensuelle(
    resultats: Union[ResultatRapprochement, Sequence[ResultatRapprochement], Any],
    periode_libelle: str = "",
) -> SyntheseMensuelle:
    """Génère la synthèse mensuelle consolidée."""
    non_couvertes = []
    if hasattr(resultats, "journees") and hasattr(resultats, "non_couvertes"):
        liste_res = list(resultats.journees)
        if not periode_libelle:
            periode_libelle = resultats.periode.libelle
        non_couvertes = list(resultats.non_couvertes)
    elif isinstance(resultats, ResultatRapprochement):
        liste_res = [resultats]
    else:
        liste_res = list(resultats)

    if not liste_res and not non_couvertes:
        raise ValueError("Au moins un ResultatRapprochement est requis pour générer la synthèse.")

    if not periode_libelle:
        periode_libelle = liste_res[0].periode.libelle

    # Construction des contrôles globaux agrégés
    if len(liste_res) == 1:
        controles = calculer_controles(liste_res[0])
    else:
        # Agrégation multi-jours
        controles_jours = [calculer_controles(r) for r in liste_res]
        controles = ControlesGlobaux(
            nb_lignes_journal=sum(c.nb_lignes_journal for c in controles_jours),
            nb_transactions_om=sum(c.nb_transactions_om for c in controles_jours),
            total_journal=sum((c.total_journal for c in controles_jours), ZERO),
            total_om=sum((c.total_om for c in controles_jours), ZERO),
            total_rapproche=sum((c.total_rapproche for c in controles_jours), ZERO),
            total_non_rapproche=sum((c.total_non_rapproche for c in controles_jours), ZERO),
            montant_ecarts=sum((c.montant_ecarts for c in controles_jours), ZERO),
            nb_conformites=sum(c.nb_conformites for c in controles_jours),
            nb_manquants=sum(c.nb_manquants for c in controles_jours),
            nb_doublons=sum(c.nb_doublons for c in controles_jours),
            nb_anomalies=sum(c.nb_anomalies for c in controles_jours),
            total_commissions=sum((c.total_commissions for c in controles_jours), ZERO),
            total_recette_du_jour=sum((c.total_recette_du_jour for c in controles_jours), ZERO),
        )

    # Détails par journée
    details_journaliers: list[SyntheseJournaliere] = []
    for r in liste_res:
        c_j = calculer_controles(r)
        statut_global = "CONFORME" if c_j.nb_anomalies == 0 else "À CONTRÔLER"
        details_journaliers.append(
            SyntheseJournaliere(
                jour=r.periode.debut,
                nb_arrhes=c_j.nb_lignes_journal,
                total_arrhes=c_j.total_journal,
                nb_om=c_j.nb_transactions_om,
                total_om=c_j.total_om,
                total_rapproche=c_j.total_rapproche,
                total_recette=c_j.total_recette_du_jour,
                total_ecarts=c_j.montant_ecarts,
                statut_global=statut_global,
            )
        )
    for nc in non_couvertes:
        details_journaliers.append(
            SyntheseJournaliere(
                jour=nc.jour,
                nb_arrhes=0,
                total_arrhes=ZERO,
                nb_om=nc.nb_transactions,
                total_om=nc.total,
                total_rapproche=ZERO,
                total_recette=nc.total,
                total_ecarts=ZERO,
                statut_global="NON COUVERTE (SANS JOURNAL)",
            )
        )

    details_journaliers.sort(key=lambda d: d.jour)
    ventilation = ventiler_par_compte(liste_res)

    return SyntheseMensuelle(
        periode_libelle=periode_libelle,
        controles_globaux=controles,
        ventilation_comptes=ventilation,
        details_journaliers=details_journaliers,
    )
