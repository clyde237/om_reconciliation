"""Le résultat d'un rapprochement : ce qui est apparié, et ce qui ne l'est pas."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from config.matching_config import (
    BLOCKING_STATUSES,
    PROBABLE_FROM_LEVEL,
    MatchLevel,
    MatchStatus,
)
from src.models import LigneJournal, Periode, TransactionOM
from src.normalization.amounts import ZERO


@dataclass(frozen=True)
class Appariement:
    """Une ou plusieurs lignes du journal face à une ou plusieurs transactions OM.

    Le cas courant est un pour un. Les tuples existent pour le niveau 5, où un
    encaissement regroupe plusieurs arrhes — ou l'inverse, un règlement fractionné.
    """

    lignes: tuple[LigneJournal, ...]
    transactions: tuple[TransactionOM, ...]
    niveau: MatchLevel
    score: float

    @property
    def montant_journal(self) -> Decimal:
        return sum((ligne.montant for ligne in self.lignes), ZERO)

    @property
    def montant_om(self) -> Decimal:
        return sum((transaction.montant for transaction in self.transactions), ZERO)

    @property
    def ecart(self) -> Decimal:
        return self.montant_journal - self.montant_om

    @property
    def est_groupe(self) -> bool:
        return len(self.lignes) > 1 or len(self.transactions) > 1
    
    @property
    def paiement_posterieur_a_saisie(self) -> bool:
        """Vrai si un paiement OM intervient après la saisie/facturation."""
        return any(
            ligne.jour is not None
            and transaction.date_operation is not None
            and transaction.date_operation > ligne.jour
            for ligne in self.lignes
            for transaction in self.transactions
        )

    @property
    def statut(self) -> MatchStatus:
        """Le statut porté par cet appariement.

        Un paiement effectué après la date de saisie/facturation est une
        anomalie bloquante, même si le montant correspond exactement.
        """
        if self.paiement_posterieur_a_saisie:
            return MatchStatus.PAIEMENT_POSTERIEUR_A_SAISIE

        if self.ecart != ZERO:
            return MatchStatus.ECART_MONTANT

        if self.est_groupe:
            return MatchStatus.CORRESPONDANCE_GROUPEE

        if self.niveau >= PROBABLE_FROM_LEVEL:
            return MatchStatus.CORRESPONDANCE_PROBABLE
        if self.lignes and self.transactions:
            from src.normalization.text import normalize_key
            mode_j = normalize_key(self.lignes[0].mode_paiement)
            mode_t = normalize_key(getattr(self.transactions[0], "operateur", "Orange Money"))
            if mode_j and mode_t and mode_j != mode_t:
                return MatchStatus.CORRESPONDANCE_PROBABLE
        return MatchStatus.CONFORME

    @property
    def client(self) -> str:
        return " + ".join(ligne.client for ligne in self.lignes if ligne.client)

    @property
    def references_om(self) -> str:
        return " + ".join(t.reference for t in self.transactions if t.reference)


@dataclass
class ResultatRapprochement:
    """Ce que produit le moteur pour une journée."""

    periode: Periode
    appariements: list[Appariement] = field(default_factory=list)
    #: Arrhes du journal sans encaissement OM correspondant.
    arrhes_sans_om: list[LigneJournal] = field(default_factory=list)
    #: Encaissements OM sans arrhe : la recette du jour, pas des manquants.
    recette_du_jour: list[TransactionOM] = field(default_factory=list)
    doublons_journal: list[LigneJournal] = field(default_factory=list)
    doublons_om: list[TransactionOM] = field(default_factory=list)
    transactions_invalides: list[TransactionOM] = field(default_factory=list)

    # --- totaux ----------------------------------------------------------------

    @property
    def total_journal(self) -> Decimal:
        rapproche = sum((a.montant_journal for a in self.appariements), ZERO)
        return rapproche + sum((l.montant for l in self.arrhes_sans_om), ZERO)

    @property
    def total_om(self) -> Decimal:
        rapproche = sum((a.montant_om for a in self.appariements), ZERO)
        return rapproche + sum((t.montant for t in self.recette_du_jour), ZERO)

    @property
    def total_rapproche(self) -> Decimal:
        return sum((a.montant_om for a in self.appariements), ZERO)

    @property
    def total_recette_du_jour(self) -> Decimal:
        return sum((t.montant for t in self.recette_du_jour), ZERO)

    @property
    def total_ecarts(self) -> Decimal:
        return sum((abs(a.ecart) for a in self.appariements), ZERO)

    @property
    def total_commissions(self) -> Decimal:
        commissions_app = sum((t.commission for a in self.appariements for t in a.transactions), ZERO)
        commissions_recette = sum((t.commission for t in self.recette_du_jour), ZERO)
        return commissions_app + commissions_recette

    # --- statuts ---------------------------------------------------------------

    def par_statut(self) -> dict[MatchStatus, int]:
        compte: dict[MatchStatus, int] = {}
        for appariement in self.appariements:
            compte[appariement.statut] = compte.get(appariement.statut, 0) + 1
        for statut, lignes in (
            (MatchStatus.MANQUANT_OM, self.arrhes_sans_om),
            (MatchStatus.RECETTE_JOUR, self.recette_du_jour),
            (MatchStatus.STATUT_OM_INVALIDE, self.transactions_invalides),
        ):
            if lignes:
                compte[statut] = len(lignes)
        doublons = len(self.doublons_journal) + len(self.doublons_om)
        if doublons:
            compte[MatchStatus.DOUBLON] = doublons
        return compte

    @property
    def anomalies_bloquantes(self) -> dict[MatchStatus, int]:
        """Ce qui interdit l'export tant que le contrôleur ne l'a pas validé."""
        return {s: n for s, n in self.par_statut().items() if s in BLOCKING_STATUSES}

    @property
    def export_possible(self) -> bool:
        return not self.anomalies_bloquantes

    @property
    def taux_rapprochement(self) -> float:
        """Part des arrhes du journal effectivement rapprochées."""
        total = len(self.appariements) + len(self.arrhes_sans_om)
        return 100.0 * len(self.appariements) / total if total else 0.0

    def invariant_respecte(self) -> bool:
        """Encaissements OM du jour = rapprochés + recette du jour."""
        return self.total_rapproche + self.total_recette_du_jour == self.total_om
