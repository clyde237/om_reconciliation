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

from config.settings import OM_COLUMN_ALIASES
from src.models import LotImport, Periode, TransactionOM
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

        colonnes = self._mapper_colonnes(lignes)
        lecture = LectureOM()
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

    def _mapper_colonnes(self, lignes: list[tuple]) -> dict[str, int]:
        """Cherche la seule ligne d'en-tête exploitable et en tire la correspondance.

        Les autres en-têtes du fichier sont brouillés par les cellules fusionnées :
        on y trouve « Généré le : » en guise de nom de colonne. Celui qui commence par
        « N° » puis « Date » est le bon ; la ligne juste au-dessus porte les groupes
        (« Agent », « Correspondant »), qui lèvent l'ambiguïté des noms dédoublés.
        """
        for rang, ligne in enumerate(lignes):
            cles = [normalize_key(c) for c in ligne]
            if len(cles) < 2 or cles[0] not in {"NO", "N"} or cles[1] != "DATE":
                continue
            groupes = self._groupes(lignes[rang - 1]) if rang else {}
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
            if "date" in colonnes and "credit" in colonnes:
                return colonnes

        raise ValueError(
            f"Aucune ligne d'en-tête exploitable dans {self.filepath.name} : "
            "les colonnes du relevé n'ont pas pu être identifiées."
        )

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
