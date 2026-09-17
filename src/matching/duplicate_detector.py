"""Détection des transactions enregistrées plusieurs fois."""

from collections import defaultdict
from typing import Iterable

from src.models import LigneJournal, TransactionOM


def doublons_journal(lignes: Iterable[LigneJournal]) -> list[LigneJournal]:
    """Même jour, même montant, même client.

    Le client fait partie de la clé, et il le faut : deux arrhes de 90 200 le même
    jour pour deux clients différents sont un cas réel et parfaitement normal.
    """
    groupes: dict[tuple, list[LigneJournal]] = defaultdict(list)
    for ligne in lignes:
        groupes[(ligne.jour, ligne.montant, ligne.cle_client)].append(ligne)
    return [ligne for groupe in groupes.values() if len(groupe) > 1 for ligne in groupe]


def doublons_om(transactions: Iterable[TransactionOM]) -> list[TransactionOM]:
    """Même référence Orange Money.

    La référence est unique par transaction : deux lignes qui la partagent sont le
    même encaissement compté deux fois, pas deux encaissements identiques.
    """
    groupes: dict[str, list[TransactionOM]] = defaultdict(list)
    for transaction in transactions:
        cle = transaction.cle_reference
        if cle:
            groupes[cle].append(transaction)
    return [t for groupe in groupes.values() if len(groupe) > 1 for t in groupe]
