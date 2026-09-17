"""Les cinq niveaux de la cascade de rapprochement (cahier des charges §4).

Chaque niveau reçoit le **reliquat** du précédent et renvoie les appariements qu'il
sait justifier. Une ligne appariée est aussitôt consommée : c'est ce qui garantit un
appariement un pour un lorsque plusieurs opérations du même jour portent le même
montant — situation observée dès la première journée réelle contrôlée.

Sur les sources actuelles, les niveaux 1 et 3 ne trouvent rien : le journal des arrhes
ne porte aucune référence Orange Money, et le relevé identifie le client par son
numéro de téléphone quand le journal le nomme. Ils restent implémentés pour les
sources à venir — MTN Mobile Money, relevé bancaire — qui, elles, les exploiteront.
"""

from decimal import Decimal
from itertools import combinations
from typing import Callable, Iterable, Optional

from rapidfuzz import fuzz

from config.matching_config import MatchingConfig, MatchLevel
from src.matching.appariement import Appariement
from src.models import LigneJournal, TransactionOM
from src.normalization.amounts import ZERO
from src.normalization.references import normalize_reference
from src.normalization.text import normalize_key

#: Score attribué aux niveaux dont la correspondance est certaine.
SCORE_CERTAIN = 100.0


def _ecart_jours(ligne: LigneJournal, transaction: TransactionOM) -> int:
    return abs((ligne.jour - transaction.date_operation).days)


def _apparier(
    lignes: list[LigneJournal],
    transactions: list[TransactionOM],
    niveau: MatchLevel,
    candidat: Callable[[LigneJournal, TransactionOM], Optional[float]],
) -> list[Appariement]:
    """Apparie un pour un, en consommant les deux côtés.

    `candidat` renvoie un score si la paire convient, `None` sinon. À score égal, la
    première transaction restante l'emporte : l'ordre du relevé fait arbitre, ce qui
    rend le résultat reproductible.
    """
    appariements: list[Appariement] = []
    disponibles = list(transactions)

    for ligne in list(lignes):
        meilleure: Optional[TransactionOM] = None
        meilleur_score = -1.0
        for transaction in disponibles:
            score = candidat(ligne, transaction)
            if score is not None and score > meilleur_score:
                meilleure, meilleur_score = transaction, score
        if meilleure is None:
            continue
        disponibles.remove(meilleure)
        lignes.remove(ligne)
        appariements.append(
            Appariement(
                lignes=(ligne,),
                transactions=(meilleure,),
                niveau=niveau,
                score=meilleur_score,
            )
        )

    transactions[:] = disponibles
    return appariements


# --- Niveau 1 : référence exacte + montant -------------------------------------


def match_reference(
    lignes: list[LigneJournal], transactions: list[TransactionOM], config: MatchingConfig
) -> list[Appariement]:
    """La correspondance la plus sûre : même référence, même montant."""

    def candidat(ligne: LigneJournal, transaction: TransactionOM) -> Optional[float]:
        reference = normalize_reference(ligne.reference_interne)
        if not reference or reference != transaction.cle_reference:
            return None
        return SCORE_CERTAIN if ligne.montant == transaction.montant else None

    return _apparier(lignes, transactions, MatchLevel.REFERENCE_MONTANT, candidat)


# --- Niveau 2 : date + montant --------------------------------------------------


def match_date_montant(
    lignes: list[LigneJournal], transactions: list[TransactionOM], config: MatchingConfig
) -> list[Appariement]:
    """Le niveau qui fait le travail sur les sources actuelles.

    L'heure n'entre pas en compte : le journal horodate la saisie de l'arrhe, pas
    l'encaissement, avec des écarts allant jusqu'à plus d'une heure.
    """

    def candidat(ligne: LigneJournal, transaction: TransactionOM) -> Optional[float]:
        if ligne.jour != transaction.date_operation or ligne.montant != transaction.montant:
            return None
        return SCORE_CERTAIN

    return _apparier(lignes, transactions, MatchLevel.DATE_MONTANT, candidat)


# --- Niveau 3 : date + montant + client -----------------------------------------


def match_client(
    lignes: list[LigneJournal], transactions: list[TransactionOM], config: MatchingConfig
) -> list[Appariement]:
    """Départage par le nom du client, quand les deux sources en portent un.

    Sans champ commun — et le relevé Orange Money n'en a pas — ce niveau ne peut
    rien produire : il s'abstient plutôt que d'inventer une ressemblance.
    """

    def candidat(ligne: LigneJournal, transaction: TransactionOM) -> Optional[float]:
        if ligne.jour != transaction.date_operation or ligne.montant != transaction.montant:
            return None
        cote_journal = ligne.cle_client
        cote_om = normalize_key(transaction.libelle_compte or transaction.correspondant)
        if not cote_journal or not cote_om or cote_om.isdigit():
            return None  # rien de textuel à comparer
        score = fuzz.token_set_ratio(cote_journal, cote_om)
        return float(score) if score >= config.fuzzy_similarity_threshold else None

    return _apparier(lignes, transactions, MatchLevel.DATE_MONTANT_CLIENT, candidat)


# --- Niveau 4 : montant + date avec tolérance -----------------------------------


def match_tolerance(
    lignes: list[LigneJournal], transactions: list[TransactionOM], config: MatchingConfig
) -> list[Appariement]:
    """Dernier recours un pour un : on desserre la date, puis le montant.

    Le score décroît avec l'écart, de sorte que la paire la plus proche l'emporte.
    La tolérance de dates doit rester étroite : un même montant réapparaît à
    plusieurs dates du mois, et l'élargir produirait des appariements croisés.
    """
    tolerance_montant = Decimal(str(config.amount_tolerance))

    def candidat(ligne: LigneJournal, transaction: TransactionOM) -> Optional[float]:
        jours = _ecart_jours(ligne, transaction)
        if jours > config.tolerance_days:
            return None
        ecart = abs(ligne.montant - transaction.montant)
        if ecart > tolerance_montant:
            return None
        penalite_date = 10.0 * jours
        penalite_montant = 10.0 * float(ecart) / float(tolerance_montant or 1)
        return max(0.0, 90.0 - penalite_date - penalite_montant)

    return _apparier(lignes, transactions, MatchLevel.MONTANT_DATE_TOLERANCE, candidat)


# --- Niveau 5 : combinaison de plusieurs lignes ---------------------------------

SCORE_GROUPE = 80.0


def match_groupe(
    lignes: list[LigneJournal], transactions: list[TransactionOM], config: MatchingConfig
) -> list[Appariement]:
    """Regroupe plusieurs lignes d'un côté face à une seule de l'autre.

    Seule étape combinatoire de la cascade, donc la seule à borner : la taille des
    groupes est plafonnée par `max_group_size`, et les candidats sont restreints à la
    même journée. Sans ces deux bornes, le coût explose avec le volume du relevé.
    """
    appariements: list[Appariement] = []
    appariements += _grouper(
        lignes, transactions, config,
        cle_source=lambda l: l.jour, cle_cible=lambda t: t.date_operation,
        montant_source=lambda l: l.montant, montant_cible=lambda t: t.montant,
        sens_journal=True,
    )
    appariements += _grouper(
        transactions, lignes, config,
        cle_source=lambda t: t.date_operation, cle_cible=lambda l: l.jour,
        montant_source=lambda t: t.montant, montant_cible=lambda l: l.montant,
        sens_journal=False,
    )
    return appariements


def _grouper(
    sources: list,
    cibles: list,
    config: MatchingConfig,
    cle_source,
    cle_cible,
    montant_source,
    montant_cible,
    sens_journal: bool,
) -> list[Appariement]:
    """Cherche un groupe de `sources` dont la somme égale une `cible` du même jour."""
    appariements: list[Appariement] = []

    for cible in list(cibles):
        jour = cle_cible(cible)
        candidats = [s for s in sources if cle_source(s) == jour]
        if len(candidats) < 2:
            continue
        trouve = None
        for taille in range(2, min(config.max_group_size, len(candidats)) + 1):
            for groupe in combinations(candidats, taille):
                if sum((montant_source(s) for s in groupe), ZERO) == montant_cible(cible):
                    trouve = groupe
                    break
            if trouve:
                break
        if not trouve:
            continue
        for element in trouve:
            sources.remove(element)
        cibles.remove(cible)
        appariements.append(
            Appariement(
                lignes=trouve if sens_journal else (cible,),
                transactions=(cible,) if sens_journal else trouve,
                niveau=MatchLevel.COMBINAISON_LIGNES,
                score=SCORE_GROUPE,
            )
        )
    return appariements


#: La cascade, dans l'ordre du §4. Chaque niveau reçoit le reliquat du précédent.
CASCADE: tuple[Callable[..., list[Appariement]], ...] = (
    match_reference,
    match_date_montant,
    match_client,
    match_tolerance,
    match_groupe,
)
