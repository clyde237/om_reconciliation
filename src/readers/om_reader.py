"""Lecteur des relevés Orange Money.

Le fichier n'est pas une table : il concatène un sous-relevé par compte, chacun
répétant tout son préambule puis alternant des blocs « transactions échouées » et
« transactions réussies » encadrés de lignes de solde. Les cellules fusionnées
rendent la plupart des lignes d'en-tête illisibles — une seule est exploitable, et
c'est d'elle que la correspondance des colonnes est tirée.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from openpyxl import load_workbook

from config.settings import (
    OM_COLONNES_ESSENTIELLES,
    OM_COLUMN_ALIASES,
    OM_COLUMN_DEFAULTS,
)
from src.models import STATUT_ECHEC, STATUT_SUCCES, LotImport, Periode, TransactionOM
from src.normalization.amounts import normalize_amount
from src.normalization.dates import DateParseError, normalize_date, parse_date
from src.normalization.text import clean_text, normalize_key

#: Un numéro de compte Orange Money camerounais : neuf chiffres.
_COMPTE = re.compile(r"^\d{9}$")

#: « USSD - 656009773 RELEVE AVRIL 2026 RECEPTION » → le libellé du point de vente.
_LIBELLE_POINT_DE_VENTE = re.compile(r"^USSD\s*-\s*\d{9}\s*(.*)$", re.IGNORECASE)

@dataclass(frozen=True)
class CompteOM:
    """Un des sous-relevés : le compte, son intitulé, le libellé de son export."""

    numero: str
    intitule: str = ""
    libelle: str = ""

    @property
    def point_de_vente(self) -> str:
        trouve = _LIBELLE_POINT_DE_VENTE.match(self.libelle)
        return clean_text(trouve.group(1)) if trouve else self.libelle


@dataclass
class LectureOM:
    """Résultat de la lecture : les comptes, les transactions et les commissions."""

    lot: LotImport = field(default_factory=LotImport)
    comptes: list[CompteOM] = field(default_factory=list)
    commissions: list[TransactionOM] = field(default_factory=list)
    periode_declaree: Optional[Periode] = None
    #: Colonnes que la ligne d'en-tête n'a pas permis d'identifier, déduites de la
    #: disposition positionnelle. Non vide = en-tête brouillé par les fusions.
    colonnes_deduites: list[str] = field(default_factory=list)

    @property
    def transactions(self) -> list[TransactionOM]:
        return self.lot.retenues

    def encaissements(self, periode: Optional[Periode] = None) -> list[TransactionOM]:
        """Les encaissements clients, restreints à la période contrôlée.

        C'est ici que s'applique la règle de périmètre : le journal porte la période,
        le relevé mensuel est filtré dessus. Sans filtre, tout le mois remonterait.
        """
        retenues = [t for t in self.transactions if t.est_encaissement_client]
        if periode is None:
            return retenues
        return [t for t in retenues if periode.contient(t.date_operation)]

    def comptes_par_numero(self) -> dict[str, CompteOM]:
        return {compte.numero: compte for compte in self.comptes}


def fusionner_lectures(lectures: list[LectureOM]) -> LectureOM:
    """Fusionne plusieurs fichiers de relevé d'un même opérateur."""
    if not lectures:
        raise ValueError("Aucun relevé à fusionner.")

    comptes: dict[str, CompteOM] = {}
    transactions = []
    commissions = []
    rejets = []
    periodes = []
    for lecture in lectures:
        comptes.update({compte.numero: compte for compte in lecture.comptes})
        transactions.extend(lecture.transactions)
        commissions.extend(lecture.commissions)
        rejets.extend(lecture.lot.rejets)
        if lecture.periode_declaree is not None:
            periodes.append(lecture.periode_declaree)

    lot = LotImport(retenues=transactions, rejets=rejets)
    periode = None
    if periodes:
        periode = Periode(
            min(periode.debut for periode in periodes),
            max(periode.fin for periode in periodes),
        )
    return LectureOM(
        lot=lot,
        comptes=list(comptes.values()),
        commissions=commissions,
        periode_declaree=periode,
    )


class OMReader:
    """Charge un relevé Orange Money et en extrait les transactions par compte."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)

    def read(self) -> LectureOM:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable : {self.filepath}")

        classeur = load_workbook(self.filepath, read_only=True, data_only=True)
        try:
            feuille = classeur[classeur.sheetnames[0]]
            lignes = [tuple(ligne) for ligne in feuille.iter_rows(values_only=True)]
        finally:
            classeur.close()

        colonnes, deduites = self._mapper_colonnes(lignes)
        lecture = LectureOM(colonnes_deduites=deduites)
        compte_courant = ""

        for numero, ligne in enumerate(lignes, start=1):
            if not any(cellule not in (None, "") for cellule in ligne):
                continue

            nouveau = self._debut_de_sous_releve(numero, lignes)
            if nouveau is not None:
                lecture.comptes.append(nouveau)
                compte_courant = nouveau.numero
                continue

            self._traiter(numero, ligne, colonnes, compte_courant, lecture)

        lecture.periode_declaree = self._periode_declaree(lignes)
        return lecture

    # --- correspondance des colonnes -------------------------------------------

    def _mapper_colonnes(self, lignes: list[tuple]) -> tuple[dict[str, int], list[str]]:
        """Associe chaque champ à sa colonne, par les en-têtes puis par la position.

        Les en-têtes de ce relevé sont brouillés par les cellules fusionnées : selon
        l'export, on y trouve « Généré le : » ou « Réseau : » en guise de nom de
        colonne. Aucun export journalier observé n'en présente un seul exploitable.

        La lecture procède donc en trois temps. Elle retient d'abord la meilleure
        correspondance par alias parmi toutes les lignes candidates. Elle complète
        ensuite les champs restants par la disposition positionnelle, constante sur
        tous les exports observés. Elle vérifie enfin la colonne du statut sur les
        données elles-mêmes — c'est la seule dont une erreur est silencieuse : un
        statut vide écarte toute la journée du rapprochement sans rien signaler.
        """
        meilleure: dict[str, int] = {}
        for rang, ligne in enumerate(lignes):
            cles = [normalize_key(c) for c in ligne]
            if len(cles) < 2 or cles[0] not in {"NO", "N"} or cles[1] != "DATE":
                continue
            colonnes = self._par_alias(cles, self._groupes(lignes[rang - 1]) if rang else {})
            if len(colonnes) > len(meilleure):
                meilleure = colonnes

        if "date" not in meilleure:
            raise ValueError(
                f"Aucune ligne d'en-tête exploitable dans {self.filepath.name} : "
                "les colonnes du relevé n'ont pas pu être identifiées."
            )

        deduites = self._completer_par_position(meilleure, lignes)
        self._verifier_statut(meilleure, lignes, deduites)

        manquantes = [c for c in OM_COLONNES_ESSENTIELLES if c not in meilleure]
        if manquantes:
            raise ValueError(
                f"Colonnes essentielles introuvables dans {self.filepath.name} : "
                f"{', '.join(manquantes)}."
            )
        return meilleure, deduites

    @staticmethod
    def _par_alias(cles: list[str], groupes: dict[int, str]) -> dict[str, int]:
        """La ligne de groupe lève l'ambiguïté des noms dédoublés (« N° de Compte »)."""
        colonnes: dict[str, int] = {}
        for index, cle in enumerate(cles):
            if not cle:
                continue
            groupe = groupes.get(index, "")
            for champ, alias in OM_COLUMN_ALIASES.items():
                if champ in colonnes:
                    continue
                if f"{groupe} {cle}".strip() in alias or cle in alias:
                    colonnes[champ] = index
                    break
        return colonnes

    @staticmethod
    def _completer_par_position(colonnes: dict[str, int], lignes: list[tuple]) -> list[str]:
        """Comble les champs non identifiés par la disposition positionnelle."""
        largeur = max((len(ligne) for ligne in lignes), default=0)
        deduites = []
        occupees = set(colonnes.values())
        for champ, index in OM_COLUMN_DEFAULTS.items():
            if champ in colonnes or index >= largeur or index in occupees:
                continue
            colonnes[champ] = index
            occupees.add(index)
            deduites.append(champ)
        return deduites

    def _verifier_statut(
        self, colonnes: dict[str, int], lignes: list[tuple], deduites: list[str]
    ) -> None:
        """Confirme la colonne du statut sur les données, ou la relocalise.

        Une colonne de statut fausse ne produit aucune erreur : elle vide simplement
        le statut, et toutes les transactions du fichier cessent d'être réussies.
        """
        attendus = {normalize_key(STATUT_SUCCES), normalize_key(STATUT_ECHEC)}
        candidates = self._colonnes_de_statut(lignes, attendus)
        if not candidates:
            return  # relevé sans aucune ligne de transaction : rien à confirmer

        actuelle = colonnes.get("statut")
        if actuelle in candidates:
            return
        colonnes["statut"] = candidates[0]
        if "statut" not in deduites:
            deduites.append("statut")

    @staticmethod
    def _colonnes_de_statut(lignes: list[tuple], attendus: set[str]) -> list[int]:
        """Colonnes dont les valeurs ressemblent à des statuts, les plus sûres d'abord."""
        scores: dict[int, int] = {}
        for ligne in lignes:
            if not ligne or not isinstance(ligne[0], int):
                continue
            for index, cellule in enumerate(ligne):
                if normalize_key(cellule) in attendus:
                    scores[index] = scores.get(index, 0) + 1
        return sorted(scores, key=lambda index: (-scores[index], index))

    @staticmethod
    def _groupes(ligne: tuple) -> dict[int, str]:
        """Propage le libellé de groupe vers la droite jusqu'au groupe suivant."""
        groupes: dict[int, str] = {}
        courant = ""
        for index, cellule in enumerate(ligne):
            cle = normalize_key(cellule)
            if cle:
                courant = cle
            groupes[index] = courant
        return groupes

    # --- sous-relevés ----------------------------------------------------------

    def _debut_de_sous_releve(self, numero: int, lignes: list[tuple]) -> Optional[CompteOM]:
        """Un sous-relevé commence là où une ligne d'étiquette expose un n° de compte."""
        ligne = lignes[numero - 1]
        etiquette = clean_text(ligne[0] if ligne else "")
        valeur = clean_text(self._colonne_valeur(ligne))
        if not etiquette or etiquette.isdigit() or not _COMPTE.match(valeur):
            return None  # une étiquette numérique est un n° de transaction, pas un libellé
        suivantes = [clean_text(self._colonne_valeur(l)) for l in lignes[numero:numero + 2]]
        return CompteOM(
            numero=valeur,
            intitule=suivantes[0] if suivantes else "",
            libelle=suivantes[1] if len(suivantes) > 1 else "",
        )

    @staticmethod
    def _colonne_valeur(ligne: tuple) -> Any:
        """Le préambule met sa valeur dans la première cellule non vide après la première."""
        for cellule in ligne[1:]:
            if cellule not in (None, ""):
                return cellule
        return ""

    # --- transactions ----------------------------------------------------------

    def _traiter(
        self,
        numero: int,
        ligne: tuple,
        colonnes: dict[str, int],
        compte_courant: str,
        lecture: LectureOM,
    ) -> None:
        brut_numero = self._cellule(ligne, colonnes, "numero")
        if not self._est_numero(brut_numero):
            return  # préambule, en-tête, ligne de solde ou de total : silencieux

        service = clean_text(self._cellule(ligne, colonnes, "service"))
        transaction = TransactionOM(
            numero=int(str(brut_numero).strip()),
            date_operation=normalize_date(self._cellule(ligne, colonnes, "date")),
            heure=self._heure(self._cellule(ligne, colonnes, "heure")),
            reference=clean_text(self._cellule(ligne, colonnes, "reference")),
            service=service,
            statut=clean_text(self._cellule(ligne, colonnes, "statut")),
            compte_agent=clean_text(self._cellule(ligne, colonnes, "compte_agent")) or compte_courant,
            correspondant=clean_text(self._cellule(ligne, colonnes, "correspondant")),
            debit=normalize_amount(self._cellule(ligne, colonnes, "debit")),
            credit=normalize_amount(self._cellule(ligne, colonnes, "credit")),
            commission=normalize_amount(self._cellule(ligne, colonnes, "commission")),
            libelle_compte=compte_courant,
        )

        if transaction.est_commission:
            lecture.commissions.append(transaction)
            return
        if transaction.date_operation is None:
            lecture.lot.rejeter(numero, f"transaction sans date ({service or 'service inconnu'})")
            return
        lecture.lot.retenues.append(transaction)

    @staticmethod
    def _est_numero(valeur: Any) -> bool:
        if isinstance(valeur, bool) or valeur in (None, ""):
            return False
        if isinstance(valeur, int):
            return True
        return str(valeur).strip().isdigit()

    @staticmethod
    def _cellule(ligne: tuple, colonnes: dict[str, int], champ: str) -> Any:
        index = colonnes.get(champ)
        if index is None or index >= len(ligne):
            return None
        return ligne[index]

    @staticmethod
    def _heure(valeur: Any):
        from datetime import datetime, time

        if isinstance(valeur, time):
            return valeur
        if isinstance(valeur, datetime):
            return valeur.time()
        texte = clean_text(valeur)
        for modele in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(texte, modele).time()
            except ValueError:
                continue
        return None

    # --- période déclarée ------------------------------------------------------

    def _periode_declaree(self, lignes: list[tuple]) -> Optional[Periode]:
        """Le préambule annonce la période couverte ; elle sert de contrôle, pas de filtre.

        C'est le journal qui porte la période de contrôle. Celle-ci ne sert qu'à
        vérifier que le relevé déposé couvre bien la journée demandée.
        """
        bornes: dict[str, Any] = {}
        for ligne in lignes:
            etiquette = normalize_key(ligne[0] if ligne else "")
            if etiquette not in {"DEBUT DE PERIODE :", "FIN DE PERIODE :"}:
                continue
            try:
                jour = parse_date(self._colonne_valeur(ligne))
            except DateParseError:
                continue  # réutilisée comme étiquette dans les sous-relevés suivants
            bornes.setdefault("debut" if "DEBUT" in etiquette else "fin", jour)
        if "debut" in bornes and "fin" in bornes:
            return Periode(bornes["debut"], bornes["fin"])
        return None
