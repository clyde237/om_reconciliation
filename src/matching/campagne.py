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
    """Rapproche une série de journaux d'encaissements avec un relevé mensuel."""

    def __init__(self, config: MatchingConfig = DEFAULT_MATCHING_CONFIG):
        self.config = config
        self.moteur = ReconciliationMatcher(config)

    def run(
        self, lectures: Sequence[LectureEncaissements], releve: LectureOM
    ) -> ResultatMensuel:
        if not lectures:
            raise ValueError("Aucun journal des encaissements déposé.")

        encaissements = releve.encaissements()
        jours_du_releve = {t.date_operation for t in encaissements if t.date_operation}
        periode = self._periode(lectures, releve)
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

        # 2. Préparation des flux OM et des lignes de journal
        transactions_om_valides = [t for t in releve.transactions if t.est_encaissement_client]

        lignes_par_jour: dict[date, list[LigneJournal]] = {
            jour: list(par_jour[jour].lignes_orange_money) for jour in par_jour
        }
        om_par_jour: dict[date, list[TransactionOM]] = {
            jour: [t for t in transactions_om_valides if t.date_operation == jour]
            for jour in par_jour
        }
        appariements_par_jour: dict[date, list[Appariement]] = {jour: [] for jour in par_jour}

        # 3. PASSE 1 : Rapprochement intra-journalier (même date)
        for jour in sorted(par_jour):
            restantes_j = lignes_par_jour[jour]
            restantes_om = om_par_jour[jour]

            # Niveau 1 : Référence + montant
            appariements_par_jour[jour].extend(
                match_reference(restantes_j, restantes_om, self.config)
            )
            # Niveau 2 : Date + montant identiques
            appariements_par_jour[jour].extend(
                match_date_montant(restantes_j, restantes_om, self.config)
            )
            # Niveau 3 : Date + montant + similarité client
            appariements_par_jour[jour].extend(
                match_client(restantes_j, restantes_om, self.config)
            )
            # Niveau 5 : Regroupement N-1 ou 1-N sur la même journée
            appariements_par_jour[jour].extend(
                match_groupe(restantes_j, restantes_om, self.config)
            )

        # 4. PASSE 2 : Détection des décalages de dates (tolérance inter-journalière)
        restantes_j_global: list[LigneJournal] = [
            l for jour in sorted(par_jour) for l in lignes_par_jour[jour]
        ]
        appariees_om = {
            t
            for apps in appariements_par_jour.values()
            for app in apps
            for t in app.transactions
        }
        restantes_om_global: list[TransactionOM] = [
            t for t in transactions_om_valides if t not in appariees_om
        ]

        # Niveau 4 : Montant avec tolérance de date (± tolerance_days)
        appariements_tolerance = match_tolerance(
            restantes_j_global, restantes_om_global, self.config
        )

        for app in appariements_tolerance:
            jour_j = app.lignes[0].jour
            if jour_j in appariements_par_jour:
                appariements_par_jour[jour_j].append(app)
            for ligne in app.lignes:
                if ligne in lignes_par_jour.get(jour_j, []):
                    lignes_par_jour[jour_j].remove(ligne)
            for trans in app.transactions:
                jour_trans = trans.date_operation
                if trans in om_par_jour.get(jour_trans, []):
                    om_par_jour[jour_trans].remove(trans)

        # 5. Assemblage des résultats journaliers
        for jour in sorted(par_jour):
            lecture = par_jour[jour]
            lignes_initiales = lecture.lignes_orange_money
            om_initiales = [t for t in releve.transactions if t.date_operation == jour]
            om_valides_jour = [t for t in om_initiales if t.est_encaissement_client]

            res_jour = ResultatRapprochement(
                periode=lecture.periode,
                appariements=appariements_par_jour[jour],
                arrhes_sans_om=lignes_par_jour[jour],
                recette_du_jour=om_par_jour[jour],
                doublons_journal=doublons_journal(lignes_initiales),
                doublons_om=doublons_om(om_valides_jour),
                transactions_invalides=[t for t in om_initiales if not t.est_reussie],
            )
            resultat.journees.append(res_jour)

        # 6. Journées non couvertes (relevé sans journal)
        for jour in sorted(jours_du_releve - set(par_jour)):
            du_jour = [
                t for t in encaissements if t.date_operation == jour and t in restantes_om_global
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
    def _periode(lectures: Sequence[LectureEncaissements], releve: LectureOM) -> Periode:
        """Le relevé annonce le mois ; à défaut, l'étendue des journaux déposés."""
        if releve.periode_declaree:
            return releve.periode_declaree
        jours_debut = [lecture.periode.debut for lecture in lectures]
        jours_fin = [lecture.periode.fin for lecture in lectures]
        return Periode(min(jours_debut), max(jours_fin))
