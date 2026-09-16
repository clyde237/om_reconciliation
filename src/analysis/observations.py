"""Observations automatiques attachées à chaque opération (cahier des charges §7).

Les phrases sont produites ici et nulle part ailleurs. Dispersées dans le code, elles
divergeraient au premier ajout de statut, et le rapport d'audit deviendrait incohérent
d'une feuille à l'autre.
"""

from decimal import Decimal

from config.matching_config import MatchLevel, MatchStatus
from src.matching.appariement import Appariement
from src.models import LigneJournal, TransactionOM
from src.normalization.amounts import format_amount

DEVISE = "FCFA"


def _jours(mot: int) -> str:
    return "d'un jour" if mot == 1 else f"de {mot} jours"


def observer_appariement(appariement: Appariement) -> str:
    """Décrit une correspondance : ce qui la justifie, et ce qui cloche s'il y a lieu."""
    ecart = appariement.ecart
    if ecart:
        sens = "supérieur" if ecart > 0 else "inférieur"
        return (
            f"Écart de montant constaté : {format_amount(abs(ecart))} {DEVISE}. "
            f"Le journal est {sens} au relevé."
        )

    if appariement.est_groupe:
        return (
            f"{len(appariement.lignes)} ligne(s) du journal regroupée(s) sur "
            f"{len(appariement.transactions)} encaissement(s) de même montant total."
        )

    decalage = _decalage_en_jours(appariement)
    if decalage:
        return f"Montant identique, date différente {_jours(decalage)}."

    if appariement.niveau is MatchLevel.REFERENCE_MONTANT:
        return "Correspondance exacte trouvée : référence et montant identiques."
    if appariement.niveau is MatchLevel.DATE_MONTANT:
        return "Correspondance exacte trouvée : même date, même montant."
    if appariement.niveau is MatchLevel.DATE_MONTANT_CLIENT:
        return (
            f"Correspondance probable sur le nom du client "
            f"(similarité {appariement.score:.0f} %) : à valider."
        )
    return f"Correspondance probable (score {appariement.score:.0f}) : à valider."


def _decalage_en_jours(appariement: Appariement) -> int:
    jours_journal = {ligne.jour for ligne in appariement.lignes}
    jours_om = {t.date_operation for t in appariement.transactions}
    if not jours_journal or not jours_om:
        return 0
    return max(
        abs((j - o).days) for j in jours_journal for o in jours_om if j and o
    )


def observer_arrhe_sans_om(ligne: LigneJournal) -> str:
    return (
        "Transaction présente dans le journal mais introuvable dans le relevé OM "
        f"({format_amount(ligne.montant)} {DEVISE})."
    )


def observer_recette(transaction: TransactionOM) -> str:
    """Le résidu n'est pas un manquant : c'est la recette ordinaire du jour."""
    return (
        "Encaissement Orange Money sans arrhe correspondante : recette du jour, "
        "à comptabiliser dans l'écriture agrégée."
    )


def observer_transaction_sans_journal(transaction: TransactionOM) -> str:
    return "Transaction OM présente mais aucune ligne correspondante dans le journal."


def observer_doublon(occurrences: int = 2) -> str:
    return f"Doublon potentiel détecté : {occurrences} enregistrements identiques."


def observer_invalide(transaction: TransactionOM) -> str:
    return (
        f"Transaction non exploitable : statut « {transaction.statut or 'inconnu'} » "
        f"pour le service « {transaction.service or 'inconnu'} »."
    )


def observer_statut(statut: MatchStatus) -> str:
    """Repli générique, pour un statut posé à la main par le contrôleur."""
    return {
        MatchStatus.CONFORME: "Correspondance confirmée.",
        MatchStatus.ECART_MONTANT: "Correspondance établie mais montant différent.",
        MatchStatus.MANQUANT_OM: "Absent du relevé Orange Money.",
        MatchStatus.MANQUANT_JOURNAL: "Absent du journal des arrhes.",
        MatchStatus.DOUBLON: "Doublon potentiel détecté.",
        MatchStatus.CORRESPONDANCE_PROBABLE: "Correspondance plausible à valider.",
        MatchStatus.CORRESPONDANCE_GROUPEE: "Opération regroupée sur plusieurs lignes.",
        MatchStatus.STATUT_OM_INVALIDE: "Transaction non exploitable.",
        MatchStatus.A_CONTROLER: "Cas non résolu automatiquement.",
        MatchStatus.RECETTE_JOUR: "Recette ordinaire de la journée.",
    }.get(statut, "")
