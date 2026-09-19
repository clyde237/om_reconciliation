"""Moteur principal orchestrant les étapes de rapprochement."""

from typing import Iterable

from config.matching_config import DEFAULT_MATCHING_CONFIG, MatchingConfig
from src.matching.appariement import Appariement, ResultatRapprochement
from src.matching.duplicate_detector import doublons_journal, doublons_om
from src.matching.niveaux import CASCADE, match_tolerance
from src.models import LigneJournal, Periode, TransactionOM


class ReconciliationMatcher:
    """Rapproche les arrhes d'une journée avec les encaissements Orange Money.

    Le périmètre est porté par le journal : une journée déposée définit la période.
    Les transactions proches de cette journée restent candidates afin de détecter
    les paiements effectués avant ou après la saisie.
    """

    def __init__(self, config: MatchingConfig = DEFAULT_MATCHING_CONFIG):
        self.config = config

    def run(
        self,
        periode: Periode,
        lignes_journal: Iterable[LigneJournal],
        transactions_om: Iterable[TransactionOM],
    ) -> ResultatRapprochement:
        resultat = ResultatRapprochement(periode=periode)

        arrhes = [l for l in lignes_journal if l.est_orange_money and periode.contient(l.jour)]
        jours_journal = {ligne.jour for ligne in arrhes}

        def est_dans_fenetre_de_matching(transaction: TransactionOM) -> bool:
            return any(
                abs((transaction.date_operation - jour).days) <= self.config.tolerance_days
                for jour in jours_journal
            )

        transactions_candidates = [
            transaction
            for transaction in transactions_om
            if periode.contient(transaction.date_operation)
            or est_dans_fenetre_de_matching(transaction)
        ]
        transactions_dans_periode = [
            transaction
            for transaction in transactions_candidates
            if periode.contient(transaction.date_operation)
        ]
        transactions_hors_periode = [
            transaction
            for transaction in transactions_candidates
            if not periode.contient(transaction.date_operation)
        ]

        resultat.transactions_invalides = [
            t for t in transactions_candidates if not t.est_reussie
        ]
        encaissements = [t for t in transactions_dans_periode if t.est_encaissement_client]
        encaissements_hors_periode = [
            t for t in transactions_hors_periode if t.est_encaissement_client
        ]

        resultat.doublons_journal = doublons_journal(arrhes)
        resultat.doublons_om = doublons_om(encaissements)

        # Chaque niveau consomme ce qu'il apparie ; les listes rétrécissent en place.
        restantes_journal = list(arrhes)
        restantes_om = list(encaissements)
        for niveau in CASCADE:
            resultat.appariements.extend(
                niveau(restantes_journal, restantes_om, self.config)
            )

        # Les transactions voisines hors période sont traitées après le flux
        # principal afin de ne pas perturber les regroupements intra-journaliers.
        if restantes_journal and encaissements_hors_periode:
            resultat.appariements.extend(
                match_tolerance(
                    restantes_journal,
                    encaissements_hors_periode,
                    self.config,
                )
            )

        resultat.arrhes_sans_om = restantes_journal
        # Règle arbitrée le 16/09/2026 : le résidu est la recette du jour, pas un
        # manquant. Le relevé porte tous les encaissements du point de vente, le
        # journal des arrhes seulement les arrhes.
        resultat.recette_du_jour = restantes_om
        return resultat
