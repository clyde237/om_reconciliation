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
from src.normalization.text import normalize_key

DEVISE = "FCFA"


def _jours(mot: int) -> str:
    return "d'un jour" if mot == 1 else f"de {mot} jours"


def _nom_court_op(op: str) -> str:
    cle = normalize_key(op)
    if "MTN" in cle or "MOMO" in cle:
        return "MoMo"
    return "OM"


def observer_appariement(appariement: Appariement) -> str:
    """Décrit une correspondance : ce qui la justifie, et ce qui cloche s'il y a lieu."""
    ecart = appariement.ecart
    if ecart:
        sens = "supérieur" if ecart > 0 else "inférieur"
        return (
            f"Écart de montant constaté : {format_amount(abs(ecart))} {DEVISE}. "
            f"Le journal est {sens} au relevé."
        )

    mode_j = appariement.lignes[0].mode_paiement if appariement.lignes else ""
    mode_t = (
        getattr(appariement.transactions[0], "operateur", "Orange Money")
        if appariement.transactions
        else ""
    )
    croisement = bool(mode_j and mode_t and normalize_key(mode_j) != normalize_key(mode_t))

    decalage = _decalage_en_jours(appariement)
    if croisement:
        if decalage:
            jour_j = appariement.lignes[0].jour.strftime("%d/%m/%Y") if appariement.lignes else ""
            jour_t = (
                appariement.transactions[0].date_operation.strftime("%d/%m/%Y")
                if appariement.transactions and appariement.transactions[0].date_operation
                else ""
            )
            return (
                f"Croisement d'opérateur : saisi en {mode_j} au journal mais encaissé sur {mode_t} "
                f"(décalage {_jours(decalage)}, journal : {jour_j}, relevé : {jour_t}) : à valider."
            )
        ref = appariement.references_om or "N/A"
        return (
            f"Croisement d'opérateur : saisi en {mode_j} au journal mais encaissé sur {mode_t} "
            f"(Réf: {ref}) : à valider."
        )

    if appariement.est_groupe:
        return (
            f"{len(appariement.lignes)} ligne(s) du journal regroupée(s) sur "
            f"{len(appariement.transactions)} encaissement(s) de même montant total."
        )

    if decalage:
        jour_j = appariement.lignes[0].jour.strftime("%d/%m/%Y") if appariement.lignes else ""
        nom_op = _nom_court_op(mode_t)
        jour_om = (
            appariement.transactions[0].date_operation.strftime("%d/%m/%Y")
            if appariement.transactions and appariement.transactions[0].date_operation
            else ""
        )
        montant = format_amount(appariement.montant_journal)
        return (
            f"Montant identique ({montant} {DEVISE}), décalage {_jours(decalage)} "
            f"(journal : {jour_j}, {nom_op} : {jour_om}) : à valider."
        )

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
    nom_op = _nom_court_op(ligne.mode_paiement) if ligne.mode_paiement else "OM"
    return (
        f"Transaction présente dans le journal mais introuvable dans le relevé {nom_op} "
        f"({format_amount(ligne.montant)} {DEVISE})."
    )


def observer_recette(transaction: TransactionOM) -> str:
    """Le résidu n'est pas un manquant : paiement présent sur le relevé mais absent du journal."""
    op = getattr(transaction, "operateur", "Orange Money")
    return f"Paiement {op} reçu sur le relevé mais absent du journal des encaissements."


def observer_transaction_sans_journal(transaction: TransactionOM) -> str:
    op = getattr(transaction, "operateur", "Orange Money")
    return f"Transaction {op} présente mais aucune ligne correspondante dans le journal."


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
