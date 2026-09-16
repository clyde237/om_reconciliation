"""Modèle canonique du domaine.

C'est le contrat entre la lecture des fichiers et le moteur de rapprochement : les
lecteurs produisent ces objets, le moteur ne connaît qu'eux. Une source nouvelle —
MTN Mobile Money, un relevé bancaire — s'ajoutera en écrivant un lecteur de plus,
sans toucher au rapprochement.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Iterator, Optional

from src.normalization.amounts import ZERO
from src.normalization.references import normalize_msisdn, normalize_reference
from src.normalization.text import normalize_key

# --- Vocabulaire des sources ---------------------------------------------------

#: Valeur de la colonne « Encaissement » du journal qui délimite le périmètre.
MODE_ORANGE_MONEY = "Orange Money"

#: Services du relevé Orange Money.
SERVICE_PAIEMENT_MARCHAND = "Merchant Payment"
SERVICE_TRANSFERT_INTERNE = "C2C Transfer"
SERVICE_COMMISSIONS = "Commissions"

#: Statuts du relevé Orange Money.
STATUT_SUCCES = "Succès"
STATUT_ECHEC = "Echec"


@dataclass(frozen=True)
class Periode:
    """Période contrôlée, bornes incluses.

    Le journal des arrhes se tire **par journée** : c'est lui qui porte la période, et
    le relevé mensuel est filtré dessus. La période n'est donc jamais saisie par
    l'utilisateur, elle est lue dans l'en-tête du journal.
    """

    debut: date
    fin: date

    def __post_init__(self) -> None:
        if self.fin < self.debut:
            raise ValueError(f"période inversée : {self.debut} → {self.fin}")

    @classmethod
    def journee(cls, jour: date) -> "Periode":
        return cls(debut=jour, fin=jour)

    @property
    def est_journee(self) -> bool:
        return self.debut == self.fin

    @property
    def libelle(self) -> str:
        if self.est_journee:
            return self.debut.strftime("%d/%m/%Y")
        return f"du {self.debut:%d/%m/%Y} au {self.fin:%d/%m/%Y}"

    def contient(self, valeur: date | datetime | None) -> bool:
        """Vrai si la date tombe dans la période. Une date absente n'y tombe jamais."""
        if valeur is None:
            return False
        jour = valeur.date() if isinstance(valeur, datetime) else valeur
        return self.debut <= jour <= self.fin

    def __iter__(self) -> Iterator[date]:
        from datetime import timedelta

        jour = self.debut
        while jour <= self.fin:
            yield jour
            jour += timedelta(days=1)


@dataclass(frozen=True)
class LigneJournal:
    """Une ligne d'encaissement du journal des arrhes."""

    ligne_source: int
    date_operation: datetime
    client: str
    mode_paiement: str
    montant: Decimal
    reference_interne: str = ""
    libelle: str = ""
    montant_reintegre: Decimal = ZERO

    @property
    def jour(self) -> date:
        return self.date_operation.date()

    @property
    def est_orange_money(self) -> bool:
        return normalize_key(self.mode_paiement) == normalize_key(MODE_ORANGE_MONEY)

    @property
    def cle_client(self) -> str:
        return normalize_key(self.client)


@dataclass(frozen=True)
class TransactionOM:
    """Une transaction du relevé Orange Money."""

    numero: int
    date_operation: date
    reference: str
    service: str
    statut: str
    compte_agent: str
    heure: Optional[time] = None
    correspondant: str = ""
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    commission: Decimal = ZERO
    libelle_compte: str = ""

    @property
    def montant(self) -> Decimal:
        """Montant de l'encaissement. Le crédit est l'entrée d'argent."""
        return self.credit

    @property
    def est_reussie(self) -> bool:
        return normalize_key(self.statut) == normalize_key(STATUT_SUCCES)

    @property
    def est_paiement_marchand(self) -> bool:
        return normalize_key(self.service) == normalize_key(SERVICE_PAIEMENT_MARCHAND)

    @property
    def est_transfert_interne(self) -> bool:
        """Virement entre comptes du groupe : hors périmètre du rapprochement."""
        return normalize_key(self.service) == normalize_key(SERVICE_TRANSFERT_INTERNE)

    @property
    def est_commission(self) -> bool:
        return normalize_key(SERVICE_COMMISSIONS) in normalize_key(self.service)

    @property
    def est_encaissement_client(self) -> bool:
        """Seules ces transactions entrent dans le rapprochement."""
        return self.est_paiement_marchand and self.est_reussie and self.credit > ZERO

    @property
    def cle_reference(self) -> str:
        return normalize_reference(self.reference)

    @property
    def cle_correspondant(self) -> str:
        return normalize_msisdn(self.correspondant)


@dataclass
class LotImport:
    """Résultat de la lecture d'un fichier : ce qui est retenu, et ce qui est écarté.

    Les rejets sont conservés avec leur motif : le rapport d'import doit pouvoir
    justifier chaque ligne absente, sous peine de faire passer une perte de données
    pour un rapprochement propre.
    """

    retenues: list = field(default_factory=list)
    rejets: list[tuple[int, str]] = field(default_factory=list)

    def rejeter(self, ligne_source: int, motif: str) -> None:
        self.rejets.append((ligne_source, motif))

    @property
    def nb_lues(self) -> int:
        return len(self.retenues) + len(self.rejets)

    def resume(self) -> str:
        return f"{len(self.retenues)} ligne(s) retenue(s), {len(self.rejets)} écartée(s)"
