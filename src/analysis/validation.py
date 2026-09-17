"""Validation humaine et gestion du verrou d'export comptable (§10, §14 et §19).

Règle fondamentale (§19) :
Une opération du journal des arrhes ne devient pas une écriture comptable du seul fait
qu'elle existe dans le journal. Elle doit être identifiée, rapprochée, contrôlée et validée.
Si des anomalies bloquantes subsistent sans validation, l'export comptable est strictement verrouillé.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence, Union

from config.matching_config import BLOCKING_STATUSES, MatchStatus
from src.analysis.reconciliation import LigneRapprochement, construire_table
from src.matching.appariement import ResultatRapprochement
from src.models import LigneJournal, TransactionOM


class DecisionType(str, Enum):
    """État d'instruction d'une opération ou d'une anomalie."""

    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    REJETE = "REJETE"


@dataclass(frozen=True)
class DecisionValidation:
    """Décision formelle enregistrée par le contrôleur de gestion."""

    identifiant_ligne: str
    statut_initial: MatchStatus
    decision: DecisionType
    auteur: str
    date_decision: datetime
    motif: str

    def to_dict(self) -> dict:
        return {
            "identifiant_ligne": self.identifiant_ligne,
            "statut_initial": self.statut_initial.value,
            "decision": self.decision.value,
            "auteur": self.auteur,
            "date_decision": self.date_decision.isoformat(),
            "motif": self.motif,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionValidation":
        return cls(
            identifiant_ligne=data["identifiant_ligne"],
            statut_initial=MatchStatus(data["statut_initial"]),
            decision=DecisionType(data["decision"]),
            auteur=data["auteur"],
            date_decision=datetime.fromisoformat(data["date_decision"]),
            motif=data.get("motif", ""),
        )


def cle_ligne_rapprochement(ligne: Union[LigneRapprochement, LigneJournal, TransactionOM, str]) -> str:
    """Génère un identifiant déterministe et unique pour une ligne d'audit ou source."""
    if isinstance(ligne, str):
        return ligne
    if isinstance(ligne, LigneJournal):
        date_str = ligne.jour.isoformat() if ligne.jour else "SANS_DATE"
        ref = ligne.reference_interne.strip() or "SANS_REF"
        cli = ligne.client.strip() or "SANS_CLIENT"
        return f"{MatchStatus.MANQUANT_OM.value}::{date_str}::{ref}::{cli}::{ligne.montant}::0"
    if isinstance(ligne, TransactionOM):
        date_str = ligne.date_operation.isoformat() if ligne.date_operation else "SANS_DATE"
        ref = ligne.reference.strip() or "SANS_REF"
        cli = ligne.correspondant.strip() or "SANS_CLIENT"
        return f"{MatchStatus.RECETTE_JOUR.value}::{date_str}::{ref}::{cli}::0::{ligne.montant}"

    date_str = ligne.date_operation.isoformat() if ligne.date_operation else "SANS_DATE"
    ref = ligne.reference.strip() or "SANS_REF"
    cli = ligne.client.strip() or "SANS_CLIENT"
    return f"{ligne.statut.value}::{date_str}::{ref}::{cli}::{ligne.montant_journal}::{ligne.montant_om}"


@dataclass
class JournalDecisions:
    """Journal des décisions de validation persisté pour la traçabilité."""

    decisions: dict[str, DecisionValidation] = field(default_factory=dict)

    def enregistrer(
        self,
        identifiant: str,
        statut_initial: MatchStatus,
        decision: DecisionType,
        auteur: str,
        motif: str = "",
    ) -> DecisionValidation:
        """Enregistre ou met à jour une décision pour une ligne."""
        dec = DecisionValidation(
            identifiant_ligne=identifiant,
            statut_initial=statut_initial,
            decision=decision,
            auteur=auteur.strip() or "Contrôleur",
            date_decision=datetime.now(),
            motif=motif.strip(),
        )
        self.decisions[identifiant] = dec
        return dec

    def valider(
        self,
        ligne: Union[LigneRapprochement, LigneJournal, TransactionOM, str],
        auteur: str,
        motif: str = "",
    ) -> DecisionValidation:
        cle = cle_ligne_rapprochement(ligne)
        statut = getattr(ligne, "statut", MatchStatus.MANQUANT_OM)
        if not isinstance(statut, MatchStatus):
            statut = MatchStatus.MANQUANT_OM
        return self.enregistrer(cle, statut, DecisionType.VALIDE, auteur, motif)

    def rejeter(
        self,
        ligne: Union[LigneRapprochement, LigneJournal, TransactionOM, str],
        auteur: str,
        motif: str = "",
    ) -> DecisionValidation:
        cle = cle_ligne_rapprochement(ligne)
        statut = getattr(ligne, "statut", MatchStatus.MANQUANT_OM)
        if not isinstance(statut, MatchStatus):
            statut = MatchStatus.MANQUANT_OM
        return self.enregistrer(cle, statut, DecisionType.REJETE, auteur, motif)

    def valider_toutes(
        self,
        lignes: Sequence[Union[LigneRapprochement, LigneJournal, TransactionOM]],
        auteur: str,
        motif: str = "Validation groupée de la période",
    ) -> int:
        """Valide en masse l'ensemble des lignes fournies."""
        compteur = 0
        for ligne in lignes:
            self.valider(ligne, auteur, motif)
            compteur += 1
        return compteur

    def reinitialiser(self, ligne: LigneRapprochement) -> None:
        cle = cle_ligne_rapprochement(ligne)
        self.decisions.pop(cle, None)

    def obtenir(self, ligne_ou_cle: Union[LigneRapprochement, str]) -> Optional[DecisionValidation]:
        cle = cle_ligne_rapprochement(ligne_ou_cle) if isinstance(ligne_ou_cle, LigneRapprochement) else ligne_ou_cle
        return self.decisions.get(cle)

    def statut_decision(self, ligne: LigneRapprochement) -> DecisionType:
        dec = self.obtenir(ligne)
        if dec is not None:
            return dec.decision
        return DecisionType.EN_ATTENTE if ligne.est_bloquante else DecisionType.VALIDE

    def to_dict(self) -> dict:
        return {cle: dec.to_dict() for cle, dec in self.decisions.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "JournalDecisions":
        journal = cls()
        for cle, dec_dict in data.items():
            journal.decisions[cle] = DecisionValidation.from_dict(dec_dict)
        return journal


@dataclass(frozen=True)
class EtatVerrou:
    """État actuel du verrou d'export comptable Sage."""

    export_autorise: bool
    nb_anomalies_totales: int
    nb_anomalies_validees: int
    nb_anomalies_rejetees: int
    nb_anomalies_en_attente: int
    anomalies_bloquantes_en_attente: list[LigneRapprochement]
    motif_blocage: str = ""


class GestionnaireVerrou:
    """Contrôle la règle de séparation CONTRÔLE / COMPTABILISATION (§19)."""

    @staticmethod
    def evaluer(
        resultat: ResultatRapprochement,
        journal: Optional[JournalDecisions] = None,
    ) -> EtatVerrou:
        """Évalue si l'export comptable est ouvert ou verrouillé."""
        if journal is None:
            journal = JournalDecisions()

        table = construire_table(resultat)
        bloquantes = [ligne for ligne in table if ligne.est_bloquante]

        validees = 0
        rejetees = 0
        en_attente: list[LigneRapprochement] = []

        for ligne in bloquantes:
            dec = journal.obtenir(ligne)
            if dec is None or dec.decision is DecisionType.EN_ATTENTE:
                en_attente.append(ligne)
            elif dec.decision is DecisionType.VALIDE:
                validees += 1
            elif dec.decision is DecisionType.REJETE:
                rejetees += 1

        export_autorise = len(en_attente) == 0
        motif = ""
        if not export_autorise:
            statuts_diff = {}
            for l in en_attente:
                statuts_diff[l.statut.value] = statuts_diff.get(l.statut.value, 0) + 1
            detail = ", ".join(f"{n} {s}" for s, n in statuts_diff.items())
            motif = f"Export bloqué : {len(en_attente)} anomalie(s) non résolue(s) ({detail})."

        return EtatVerrou(
            export_autorise=export_autorise,
            nb_anomalies_totales=len(bloquantes),
            nb_anomalies_validees=validees,
            nb_anomalies_rejetees=rejetees,
            nb_anomalies_en_attente=len(en_attente),
            anomalies_bloquantes_en_attente=en_attente,
            motif_blocage=motif,
        )

    @staticmethod
    def lignes_eligibles_export(
        resultat: ResultatRapprochement,
        journal: Optional[JournalDecisions] = None,
    ) -> list[LigneRapprochement]:
        """Retourne les seules opérations autorisées à alimenter l'export comptable Sage.

        Règles d'éligibilité :
        - Les lignes conformes ou recettes ordinaires sont éligibles (sauf si explicitement rejetées).
        - Les anomalies bloquantes ne sont éligibles QUE si elles ont été explicitement VALIDÉES.
        - Une ligne REJETÉE n'apparaît JAMAIS dans l'écriture.
        - Si le verrou global est actif (anomalie en attente), une liste vide est renvoyée.
        """
        if journal is None:
            journal = JournalDecisions()

        verrou = GestionnaireVerrou.evaluer(resultat, journal)
        if not verrou.export_autorise:
            return []

        table = construire_table(resultat)
        eligibles: list[LigneRapprochement] = []

        for ligne in table:
            dec = journal.obtenir(ligne)
            if dec is not None and dec.decision is DecisionType.REJETE:
                # Exclue d'office
                continue

            if ligne.est_bloquante:
                if dec is not None and dec.decision is DecisionType.VALIDE:
                    eligibles.append(ligne)
            else:
                # Ligne conforme ou recette ordinaire non rejetée
                eligibles.append(ligne)

        return eligibles
