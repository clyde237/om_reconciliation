"""Table d'audit unifiée et contrôles globaux de la journée.

La table est le livrable de lecture du contrôleur : une ligne par opération, aux
colonnes du §9. Les contrôles globaux du §8 l'accompagnent et vérifient qu'elle se
tient — un total qui ne se décompose pas signale un résultat à ne pas exploiter.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from config.matching_config import BLOCKING_STATUSES, MatchStatus
from src.analysis.observations import (
    observer_appariement,
    observer_arrhe_sans_om,
    observer_invalide,
    observer_recette,
)
from src.matching.appariement import ResultatRapprochement
from src.normalization.amounts import ZERO


@dataclass(frozen=True)
class LigneRapprochement:
    """Une ligne du rapport, colonnes du §9 plus la traçabilité de la règle."""

    date_operation: Optional[date]
    reference: str
    client: str
    montant_journal: Decimal
    montant_om: Decimal
    ecart: Decimal
    statut: MatchStatus
    observation: str
    niveau: Optional[int] = None
    score: Optional[float] = None
    compte_om: str = ""
    ligne_source: Optional[int] = None
    commission: Decimal = ZERO

    @property
    def est_bloquante(self) -> bool:
        return self.statut in BLOCKING_STATUSES


def construire_table(resultat: ResultatRapprochement) -> list[LigneRapprochement]:
    """Assemble la table d'audit dans l'ordre : rapprochées, arrhes seules, recette."""
    lignes: list[LigneRapprochement] = []

    for appariement in resultat.appariements:
        premiere = appariement.lignes[0]
        lignes.append(
            LigneRapprochement(
                date_operation=premiere.jour,
                reference=appariement.references_om,
                client=appariement.client,
                montant_journal=appariement.montant_journal,
                montant_om=appariement.montant_om,
                ecart=appariement.ecart,
                statut=appariement.statut,
                observation=observer_appariement(appariement),
                niveau=int(appariement.niveau),
                score=appariement.score,
                compte_om=appariement.transactions[0].compte_agent,
                ligne_source=premiere.ligne_source,
                commission=sum((t.commission for t in appariement.transactions), ZERO),
            )
        )

    for ligne in resultat.arrhes_sans_om:
        lignes.append(
            LigneRapprochement(
                date_operation=ligne.jour,
                reference=ligne.reference_interne,
                client=ligne.client,
                montant_journal=ligne.montant,
                montant_om=ZERO,
                ecart=ligne.montant,
                statut=MatchStatus.MANQUANT_OM,
                observation=observer_arrhe_sans_om(ligne),
                ligne_source=ligne.ligne_source,
            )
        )

    for transaction in resultat.recette_du_jour:
        lignes.append(
            LigneRapprochement(
                date_operation=transaction.date_operation,
                reference=transaction.reference,
                client=transaction.correspondant,
                montant_journal=ZERO,
                montant_om=transaction.montant,
                ecart=-transaction.montant,
                statut=MatchStatus.RECETTE_JOUR,
                observation=observer_recette(transaction),
                compte_om=transaction.compte_agent,
                commission=transaction.commission,
            )
        )

    for transaction in resultat.transactions_invalides:
        lignes.append(
            LigneRapprochement(
                date_operation=transaction.date_operation,
                reference=transaction.reference,
                client=transaction.correspondant,
                montant_journal=ZERO,
                montant_om=ZERO,
                ecart=ZERO,
                statut=MatchStatus.STATUT_OM_INVALIDE,
                observation=observer_invalide(transaction),
                compte_om=transaction.compte_agent,
            )
        )

    return lignes


@dataclass(frozen=True)
class ControlesGlobaux:
    """Les onze indicateurs du §8, plus les commissions, suivies à part.

    Les commissions Orange Money sont prélevées à la transaction : elles ne sont
    jamais un écart de rapprochement, et alimentent leur propre compte comptable.
    """

    nb_lignes_journal: int
    nb_transactions_om: int
    total_journal: Decimal
    total_om: Decimal
    total_rapproche: Decimal
    total_non_rapproche: Decimal
    montant_ecarts: Decimal
    nb_conformites: int
    nb_manquants: int
    nb_doublons: int
    nb_anomalies: int
    total_commissions: Decimal = ZERO
    total_recette_du_jour: Decimal = ZERO

    def verifier(self) -> list[str]:
        """Renvoie les invariants rompus. Une liste vide signifie un résultat cohérent."""
        ruptures: list[str] = []
        if self.total_om != self.total_rapproche + self.total_recette_du_jour:
            ruptures.append(
                f"Encaissements OM ({self.total_om}) ≠ rapproché ({self.total_rapproche}) "
                f"+ recette du jour ({self.total_recette_du_jour})."
            )
        if self.total_journal < self.total_rapproche:
            ruptures.append(
                f"Total journal ({self.total_journal}) inférieur au total rapproché "
                f"({self.total_rapproche})."
            )
        if self.nb_conformites > self.nb_lignes_journal:
            ruptures.append("Plus de conformités que de lignes de journal.")
        return ruptures

    @property
    def coherent(self) -> bool:
        return not self.verifier()

    @property
    def taux_rapprochement(self) -> float:
        return (
            100.0 * float(self.total_rapproche) / float(self.total_journal)
            if self.total_journal
            else 0.0
        )


def calculer_controles(resultat: ResultatRapprochement) -> ControlesGlobaux:
    """Calcule les onze indicateurs du §8 à partir du résultat du rapprochement."""
    table = construire_table(resultat)
    manquants = sum(
        1
        for ligne in table
        if ligne.statut in {MatchStatus.MANQUANT_OM, MatchStatus.MANQUANT_JOURNAL}
    )
    return ControlesGlobaux(
        nb_lignes_journal=len(resultat.appariements) + len(resultat.arrhes_sans_om),
        nb_transactions_om=len(resultat.appariements) + len(resultat.recette_du_jour),
        total_journal=resultat.total_journal,
        total_om=resultat.total_om,
        total_rapproche=resultat.total_rapproche,
        total_non_rapproche=sum((l.montant for l in resultat.arrhes_sans_om), ZERO)
        + resultat.total_recette_du_jour,
        montant_ecarts=resultat.total_ecarts,
        nb_conformites=sum(
            1 for ligne in table if ligne.statut is MatchStatus.CONFORME
        ),
        nb_manquants=manquants,
        nb_doublons=len(resultat.doublons_journal) + len(resultat.doublons_om),
        nb_anomalies=sum(1 for ligne in table if ligne.est_bloquante),
        total_commissions=resultat.total_commissions,
        total_recette_du_jour=resultat.total_recette_du_jour,
    )
