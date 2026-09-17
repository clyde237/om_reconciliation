"""Contrôle d'un mois : N journaux d'encaissements face à un relevé Orange Money.

Le journal se tire par journée, le relevé par mois. Un contrôle mensuel consiste donc
à déposer les journaux de la période — une trentaine — et à rapprocher chacun avec la
journée correspondante du relevé.

Ce module orchestre cette confrontation et signale ce qu'aucun rapprochement
journalier ne peut voir : une journée déposée deux fois, un journal hors du relevé, et
surtout les journées du relevé pour lesquelles aucun journal n'a été fourni — des
encaissements Orange Money qui échappent alors au contrôle.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional, Sequence

from config.matching_config import DEFAULT_MATCHING_CONFIG, MatchingConfig
from src.matching.appariement import Appariement, ResultatRapprochement
from src.matching.duplicate_detector import doublons_journal, doublons_om
from src.matching.matcher import ReconciliationMatcher
from src.matching.niveaux import (
    match_client,
    match_date_montant,
    match_groupe,
    match_reference,
    match_tolerance,
)
from src.models import LigneJournal, LotImport, Periode, TransactionOM
from src.normalization.amounts import ZERO
from src.readers.encaissements_reader import LectureEncaissements
from src.readers.om_reader import LectureOM


@dataclass(frozen=True)
class JourneeNonCouverte:
    """Une journée du relevé pour laquelle aucun journal n'a été déposé."""

    jour: date
    nb_transactions: int
    total: Decimal


@dataclass
class ResultatMensuel:
    """Ce que produit un contrôle mensuel."""

    periode: Periode
    #: Un résultat par journée déposée, dans l'ordre chronologique.
    journees: list[ResultatRapprochement] = field(default_factory=list)
    #: Journées du relevé sans journal fourni : leurs encaissements sont incontrôlés.
    non_couvertes: list[JourneeNonCouverte] = field(default_factory=list)
    #: Journaux déposés dont la journée ne figure pas dans le relevé.
    hors_releve: list[date] = field(default_factory=list)
    #: Journées déposées plusieurs fois, avec le nom des fichiers en cause.
    doublons_de_journee: dict[date, list[str]] = field(default_factory=dict)
    sources: dict[date, str] = field(default_factory=dict)

    # --- totaux ----------------------------------------------------------------

    @property
    def total_journal(self) -> Decimal:
        return sum((j.total_journal for j in self.journees), ZERO)

    @property
    def total_om_controle(self) -> Decimal:
        return sum((j.total_om for j in self.journees), ZERO)

    @property
    def total_om_non_controle(self) -> Decimal:
        return sum((n.total for n in self.non_couvertes), ZERO)

    @property
    def total_rapproche(self) -> Decimal:
        return sum((j.total_rapproche for j in self.journees), ZERO)

    @property
    def nb_journees_deposees(self) -> int:
        return len(self.journees)

    @property
    def taux_couverture(self) -> float:
        """Part des encaissements du relevé effectivement soumis au contrôle."""
        total = self.total_om_controle + self.total_om_non_controle
        return 100.0 * float(self.total_om_controle) / float(total) if total else 0.0

    @property
    def taux_rapprochement(self) -> float:
        return (
            100.0 * float(self.total_rapproche) / float(self.total_om_controle)
            if self.total_om_controle
            else 0.0
        )

    @property
    def export_possible(self) -> bool:
        """Un seul jour bloquant suffit à fermer l'export du mois."""
        return all(journee.export_possible for journee in self.journees)

    @property
    def journees_bloquantes(self) -> list[ResultatRapprochement]:
        return [journee for journee in self.journees if not journee.export_possible]

    @property
    def complet(self) -> bool:
        """Vrai quand chaque journée du relevé a reçu son journal."""
        return not self.non_couvertes and not self.doublons_de_journee

    def consolider(self) -> ResultatRapprochement:
        """Consolide tous les résultats journaliers en un unique ResultatRapprochement."""
        return ResultatRapprochement(
            periode=self.periode,
            appariements=[a for j in self.journees for a in j.appariements],
            arrhes_sans_om=[l for j in self.journees for l in j.arrhes_sans_om],
            recette_du_jour=[t for j in self.journees for t in j.recette_du_jour],
            doublons_journal=[l for j in self.journees for l in j.doublons_journal],
            doublons_om=[t for j in self.journees for t in j.doublons_om],
            transactions_invalides=[t for j in self.journees for t in j.transactions_invalides],
        )


class ControleMensuel:
    """Rapproche une série de journaux d'encaissements avec un relevé mensuel (OM et/ou MoMo)."""

    def __init__(self, config: MatchingConfig = DEFAULT_MATCHING_CONFIG):
        self.config = config
        self.moteur = ReconciliationMatcher(config)

    def run(
        self,
        lectures: Sequence[LectureEncaissements],
        releve: LectureOM,
        releve_momo: Optional[LectureOM] = None,
    ) -> ResultatMensuel:
        if not lectures:
            raise ValueError("Aucun journal des encaissements déposé.")

        # Rassembler toutes les transactions des relevés fournis
        all_releve_transactions: list[TransactionOM] = list(releve.transactions)
        transactions_valides: list[TransactionOM] = [
            t for t in releve.transactions if t.est_encaissement_client
        ]
        if releve_momo is not None:
            all_releve_transactions.extend(releve_momo.transactions)
            transactions_valides.extend(
                [t for t in releve_momo.transactions if t.est_encaissement_client]
            )

        jours_du_releve = {t.date_operation for t in transactions_valides if t.date_operation}
        periode = self._periode(lectures, releve, releve_momo)
        resultat = ResultatMensuel(periode=periode)

        # 1. Ventiler les journaux multi-jours
        lectures_quotidiennes: list[LectureEncaissements] = []
        periodes_declarees = [l.periode for l in lectures]
        for lecture in lectures:
            lectures_quotidiennes.extend(lecture.ventiler_par_jour())

        par_jour = self._indexer(lectures_quotidiennes, resultat)

        # Si une journée du relevé est comprise dans la période d'un journal fourni
        # mais n'a eu aucun mouvement, lui attribuer une journée vide (couverte)
        for jour in sorted(jours_du_releve):
            if jour not in par_jour and any(p.contient(jour) for p in periodes_declarees):
                source_parent = next(
                    (l.source for l in lectures if l.periode.contient(jour)), "Journal consolidé"
                )
                par_jour[jour] = LectureEncaissements(
                    periode=Periode(jour, jour),
                    lot=LotImport(),
                    source=f"{source_parent} ({jour.strftime('%d/%m/%Y')})",
                )

        for jour in sorted(par_jour):
            resultat.sources[jour] = par_jour[jour].source
            if jour not in jours_du_releve:
                resultat.hors_releve.append(jour)

        # 2. Préparation des flux et des lignes de journal
        lignes_par_jour: dict[date, list[LigneJournal]] = {
            jour: list(par_jour[jour].lignes_orange_money) for jour in par_jour
        }
        tx_par_jour: dict[date, list[TransactionOM]] = {
            jour: [t for t in transactions_valides if t.date_operation == jour]
            for jour in par_jour
        }
        appariements_par_jour: dict[date, list[Appariement]] = {jour: [] for jour in par_jour}

        # 3. PASSE 1 : Rapprochement intra-journalier (même date)
        for jour in sorted(par_jour):
            lignes_jour = lignes_par_jour[jour]
            tx_jour = tx_par_jour[jour]

            # Séparation par opérateur
            lignes_om = [l for l in lignes_jour if l.est_orange_money]
            lignes_momo = [l for l in lignes_jour if l.est_momo]
            lignes_autres = [l for l in lignes_jour if not l.est_orange_money and not l.est_momo]

            tx_om = [
                t
                for t in tx_jour
                if getattr(t, "operateur", "Orange Money") != "MTN Mobile Money"
            ]
            tx_momo = [
                t
                for t in tx_jour
                if getattr(t, "operateur", "Orange Money") == "MTN Mobile Money"
            ]

            # Passe 1A : Même jour, même opérateur (OM avec OM, MoMo avec MoMo)
            appariements_par_jour[jour].extend(match_reference(lignes_om, tx_om, self.config))
            appariements_par_jour[jour].extend(match_date_montant(lignes_om, tx_om, self.config))
            appariements_par_jour[jour].extend(match_client(lignes_om, tx_om, self.config))
            appariements_par_jour[jour].extend(match_groupe(lignes_om, tx_om, self.config))

            appariements_par_jour[jour].extend(match_reference(lignes_momo, tx_momo, self.config))
            appariements_par_jour[jour].extend(match_date_montant(lignes_momo, tx_momo, self.config))
            appariements_par_jour[jour].extend(match_client(lignes_momo, tx_momo, self.config))
            appariements_par_jour[jour].extend(match_groupe(lignes_momo, tx_momo, self.config))

            # Passe 1B : Même jour, croisement d'opérateur (inversion de saisie au journal)
            # Cas 1 : Saisi OM au journal, mais payé par MoMo
            if lignes_om and tx_momo:
                appariements_par_jour[jour].extend(match_client(lignes_om, tx_momo, self.config))
                appariements_par_jour[jour].extend(match_date_montant(lignes_om, tx_momo, self.config))
            # Cas 2 : Saisi MoMo au journal, mais payé par OM
            if lignes_momo and tx_om:
                appariements_par_jour[jour].extend(match_client(lignes_momo, tx_om, self.config))
                appariements_par_jour[jour].extend(match_date_montant(lignes_momo, tx_om, self.config))

            # Mise à jour des restantes pour cette journée
            lignes_par_jour[jour] = lignes_om + lignes_momo + lignes_autres
            tx_par_jour[jour] = tx_om + tx_momo

        # 4. PASSE 2 : Tolérance de dates (décalage inter-journalier ± tolerance_days)
        # Passe 2A : Tolérance au sein du même opérateur
        restantes_j_om = [
            l for jour in sorted(par_jour) for l in lignes_par_jour[jour] if l.est_orange_money
        ]
        restantes_j_momo = [
            l for jour in sorted(par_jour) for l in lignes_par_jour[jour] if l.est_momo
        ]

        appariees_global = {
            t
            for apps in appariements_par_jour.values()
            for app in apps
            for t in app.transactions
        }
        restantes_tx_global = [t for t in transactions_valides if t not in appariees_global]
        restantes_tx_om = [
            t
            for t in restantes_tx_global
            if getattr(t, "operateur", "Orange Money") != "MTN Mobile Money"
        ]
        restantes_tx_momo = [
            t
            for t in restantes_tx_global
            if getattr(t, "operateur", "Orange Money") == "MTN Mobile Money"
        ]

        self._appliquer_tolerance(
            match_tolerance(restantes_j_om, restantes_tx_om, self.config),
            appariements_par_jour,
            lignes_par_jour,
            tx_par_jour,
        )
        self._appliquer_tolerance(
            match_tolerance(restantes_j_momo, restantes_tx_momo, self.config),
            appariements_par_jour,
            lignes_par_jour,
            tx_par_jour,
        )

        # Passe 2B : Tolérance avec croisement d'opérateur
        restantes_j_om_apres = [
            l for jour in sorted(par_jour) for l in lignes_par_jour[jour] if l.est_orange_money
        ]
        restantes_j_momo_apres = [
            l for jour in sorted(par_jour) for l in lignes_par_jour[jour] if l.est_momo
        ]

        appariees_global_apres = {
            t
            for apps in appariements_par_jour.values()
            for app in apps
            for t in app.transactions
        }
        restantes_tx_global_apres = [t for t in transactions_valides if t not in appariees_global_apres]
        restantes_tx_om_apres = [
            t
            for t in restantes_tx_global_apres
            if getattr(t, "operateur", "Orange Money") != "MTN Mobile Money"
        ]
        restantes_tx_momo_apres = [
            t
            for t in restantes_tx_global_apres
            if getattr(t, "operateur", "Orange Money") == "MTN Mobile Money"
        ]

        if restantes_j_om_apres and restantes_tx_momo_apres:
            self._appliquer_tolerance(
                match_tolerance(restantes_j_om_apres, restantes_tx_momo_apres, self.config),
                appariements_par_jour,
                lignes_par_jour,
                tx_par_jour,
            )
        if restantes_j_momo_apres and restantes_tx_om_apres:
            self._appliquer_tolerance(
                match_tolerance(restantes_j_momo_apres, restantes_tx_om_apres, self.config),
                appariements_par_jour,
                lignes_par_jour,
                tx_par_jour,
            )

        # 5. Assemblage des résultats journaliers
        for jour in sorted(par_jour):
            lecture = par_jour[jour]
            lignes_initiales = lecture.lignes_orange_money
            tx_initiales = [t for t in all_releve_transactions if t.date_operation == jour]
            tx_valides_jour = [t for t in tx_initiales if t.est_encaissement_client]

            res_jour = ResultatRapprochement(
                periode=lecture.periode,
                appariements=appariements_par_jour[jour],
                arrhes_sans_om=lignes_par_jour[jour],
                recette_du_jour=tx_par_jour[jour],
                doublons_journal=doublons_journal(lignes_initiales),
                doublons_om=doublons_om(tx_valides_jour),
                transactions_invalides=[t for t in tx_initiales if not t.est_reussie],
            )
            resultat.journees.append(res_jour)

        # 6. Journées non couvertes (relevé sans journal)
        appariees_global = {
            t
            for apps in appariements_par_jour.values()
            for app in apps
            for t in app.transactions
        }
        restantes_global = [t for t in transactions_valides if t not in appariees_global]

        for jour in sorted(jours_du_releve - set(par_jour)):
            du_jour = [
                t for t in transactions_valides if t.date_operation == jour and t in restantes_global
            ]
            if du_jour:
                resultat.non_couvertes.append(
                    JourneeNonCouverte(
                        jour=jour,
                        nb_transactions=len(du_jour),
                        total=sum((t.montant for t in du_jour), ZERO),
                    )
                )

        return resultat

    @staticmethod
    def _appliquer_tolerance(
        appariements: Sequence[Appariement],
        appariements_par_jour: dict[date, list[Appariement]],
        lignes_par_jour: dict[date, list[LigneJournal]],
        tx_par_jour: dict[date, list[TransactionOM]],
    ) -> None:
        for app in appariements:
            jour_j = app.lignes[0].jour
            if jour_j in appariements_par_jour:
                appariements_par_jour[jour_j].append(app)
            for ligne in app.lignes:
                if ligne in lignes_par_jour.get(jour_j, []):
                    lignes_par_jour[jour_j].remove(ligne)
            for trans in app.transactions:
                jour_trans = trans.date_operation
                if jour_trans in tx_par_jour and trans in tx_par_jour[jour_trans]:
                    tx_par_jour[jour_trans].remove(trans)

    @staticmethod
    def _indexer(
        lectures: Sequence[LectureEncaissements], resultat: ResultatMensuel
    ) -> dict[date, LectureEncaissements]:
        """Une journée par journal. Un doublon est signalé, jamais écrasé en silence."""
        par_jour: dict[date, LectureEncaissements] = {}
        for lecture in lectures:
            jour = lecture.periode.debut
            if jour in par_jour:
                resultat.doublons_de_journee.setdefault(
                    jour, [par_jour[jour].source]
                ).append(lecture.source)
                continue
            par_jour[jour] = lecture
        return par_jour

    @staticmethod
    def _periode(
        lectures: Sequence[LectureEncaissements],
        releve: LectureOM,
        releve_momo: Optional[LectureOM] = None,
    ) -> Periode:
        """Le relevé annonce le mois ; à défaut, l'étendue des journaux déposés."""
        if releve.periode_declaree:
            return releve.periode_declaree
        if releve_momo and releve_momo.periode_declaree:
            return releve_momo.periode_declaree
        jours_debut = [lecture.periode.debut for lecture in lectures]
        jours_fin = [lecture.periode.fin for lecture in lectures]
        return Periode(min(jours_debut), max(jours_fin))
