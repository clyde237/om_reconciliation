"""Moteur principal orchestrant les étapes de rapprochement."""

from typing import Iterable, Optional

from config.matching_config import DEFAULT_MATCHING_CONFIG, MatchingConfig
from src.matching.appariement import Appariement, ResultatRapprochement
from src.matching.duplicate_detector import doublons_journal, doublons_om
from src.matching.niveaux import CASCADE
from src.models import LigneJournal, Periode, TransactionOM


class ReconciliationMatcher:
    """Rapproche les arrhes d'une journée avec les encaissements Orange Money.

    Le périmètre est porté par le journal : une journée déposée définit la période, et
    le relevé mensuel est restreint à cette journée avant tout appariement.
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
        du_jour = [t for t in transactions_om if periode.contient(t.date_operation)]

        resultat.transactions_invalides = [t for t in du_jour if not t.est_reussie]
        encaissements = [t for t in du_jour if t.est_encaissement_client]

        resultat.doublons_journal = doublons_journal(arrhes)
        resultat.doublons_om = doublons_om(encaissements)

        # Chaque niveau consomme ce qu'il apparie ; les listes rétrécissent en place.
        restantes_journal = list(arrhes)
        restantes_om = list(encaissements)
        for niveau in CASCADE:
            resultat.appariements.extend(
                niveau(restantes_journal, restantes_om, self.config)
            )

        resultat.arrhes_sans_om = restantes_journal
        # Règle arbitrée le 16/09/2026 : le résidu est la recette du jour, pas un
        # manquant. Le relevé porte tous les encaissements du point de vente, le
        # journal des arrhes seulement les arrhes.
        resultat.recette_du_jour = restantes_om
        return resultat
