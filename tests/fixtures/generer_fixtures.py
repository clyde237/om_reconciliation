"""Génère les classeurs d'exemple utilisés par les tests de lecture.

Les fichiers réels contiennent des noms de clients et des numéros de téléphone : ils
restent dans `data/input/`, exclu du dépôt. Ces exemples en reproduisent **la
structure et les pièges** — bloc d'en-tête, table décalée, sous-totaux, récapitulatif,
sous-relevés concaténés, en-têtes brouillés par les cellules fusionnées — avec des
données entièrement fabriquées.

Régénération :

    .venv/bin/python tests/fixtures/generer_fixtures.py
"""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

ICI = Path(__file__).resolve().parent


def journal_des_arrhes() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "A"

    # Bloc d'en-tête : tout tient dans une seule cellule, période comprise.
    ws["C1"] = (
        "Journal des arrhes\n\nHOTEL EXEMPLE SA \nBP000 VILLE  \n"
        "Tél: +237200000000\n12/05/2026 09:00 POSTE-TEST Agent TEST (00-00-0) \n\n\n"
        "Période du 12/05/2026 au 12/05/2026  (Type d'arrhes : Toutes)  \n"
    )

    # Ligne 2 : les en-têtes, avec les retours à la ligne de l'export réel.
    ws.append([])  # ligne 1 déjà remplie par affectation directe
    for colonne, valeur in enumerate(
        ["Date", "Compte / Réservation", "Réintégration", "Encaissement",
         "Montant\nEncaissé", "Montant\nRéintégré", "Solde non\nréintégré", "Réservation"],
        start=1,
    ):
        ws.cell(row=2, column=colonne, value=valeur)

    lignes = [
        (datetime(2026, 5, 12, 9, 30), "ENTREPRISE EXEMPLE", None, "Espèces", 500000, None, 500000),
        (datetime(2026, 5, 12, 11, 15),
         "Monsieur ALPHA Jean\nRéservation N°9001 13/05/26  ALPHA",
         "Facture N°TS-0001  75 000 FCFA 14/05/2026", "Orange Money", 75000, 75000, 0),
        (datetime(2026, 5, 12, 14, 5),
         "Madame BETA Claire\nRéservation N°9002 13/05/26  BETA",
         "Facture N°TS-0002  120 500 FCFA 14/05/2026", "Orange Money", 120500, 120500, 0),
        (datetime(2026, 5, 12, 17, 40),
         "Monsieur GAMMA Paul\nRéservation N°9003 14/05/26  GAMMA",
         "Facture N°TS-0003  75 000 FCFA 15/05/2026", "Orange Money", 75000, 75000, 0),
        (datetime(2026, 5, 12, 18, 20),
         "Madame DELTA Sophie\nRéservation N°9004 14/05/26  DELTA",
         "Facture N°TS-0004  40 000 FCFA 15/05/2026", "Virement Bancaire", 40000, 40000, 0),
    ]
    for ligne in lignes:
        ws.append(list(ligne))

    # Pied de table : sous-totaux, note, pagination.
    ws.append(["Sous-total des arrhes antérieures à la période éditée", None, None, None, 0, 0, 0])
    ws.append(["Sous-total des arrhes de la période éditée", None, None, None, 810500, 310500, 500000])
    ws.append(["Total (avec solde antérieur à la période)", None, None, None, 810500, 310500, 500000])
    ws.append(["* Les lignes de détail en italiques sont des arrhes antérieures."])
    ws.append([None, None, None, None, None, None, "1 / 1"])

    # Bloc « Récapitulatif » : des libellés en colonne date, aucun n'est une date.
    ws.append(["Récapitulatif", "Arrhes\nPerçues", "Arrhes réintégrées", None, "Arrhes période"])
    ws.append([None, None, "Réintégrées", "Solde âgé", "Réintégrées", "Solde"])
    ws.append(["Solde au 11/05/26", None, None, 0, None, 0])
    ws.append(["Espèces", 500000, 0, 500000, 0, 500000])
    ws.append(["Virement Bancaire", 40000, 40000, 0, 40000, 0])
    ws.append(["Orange Money", 270500, 270500, 0, 270500, 0])
    ws.append(["Total encaissements période", 810500, 310500, 500000, 310500, 500000])
    ws.append(["Totaux", None, None, 500000, None, 500000])
    return wb


def _entetes_releve(ws, brouilles: bool) -> None:
    """Ajoute la paire ligne de groupe / ligne d'en-tête.

    Dans le fichier réel, seule la première paire est exploitable : les cellules
    fusionnées décalent les suivantes au point d'y écrire « Généré le : » en guise de
    nom de colonne. Le lecteur doit donc s'en tenir à la première.
    """
    if brouilles:
        ws.append([None, None, None, None, "Type de rapport :", None, None, None,
                   "Coordonnées entrepris", None, None, "Date", None, "Montant (XAF)",
                   None, "Commissions (XAF)"])
        ws.append(["Agent", "Opération", "Paiement", "N° de Compte", "Statut", "Réseau :",
                   "Compte Orange Money :", "Contact chez le client :", "Généré le :",
                   "Heure", "Mode", "Généré le :", "Heure", "N°", "Référence",
                   "Compte: 600000001", "Sous-réseau"])
        return
    ws.append([None, None, None, None, "Opération", None, None, None, "Agent", None, None,
               "Correspondant", None, "Montant (XAF)", None, "Commissions (XAF)"])
    ws.append(["N°", "Date", "Heure", "Référence", "Service", "Paiement", "Statut", "Mode",
               "N° de Compte", "Wallet", "N° Pseudo", "N° de Compte", "Wallet",
               "Débit", "Crédit", "Compte: 600000001", "Sous-réseau"])


def _transaction(numero, date, heure, reference, service, statut, agent, correspondant,
                 debit=None, credit=None, commission=None):
    return [numero, date, heure, reference, service, "Transaction", statut, "USSD",
            agent, "Normal", None, correspondant, "Normal", debit, credit, 0, commission]


def releve_orange_money() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Channel User Transaction Report"

    ws.append(["."])
    ws.append(["RELEVE DES OPERATIONS OM DU MOIS DE MAI 2026"])
    ws.append(["Application :", None, None, "Orange Money"])
    ws.append(["Réseau :", None, None, "Cameroon"])
    ws.append(["Début de Période :", None, None, "01/05/2026"])
    ws.append(["Fin de Période :", None, None, "31/05/2026"])
    ws.append(["Type de rapport :", None, None, "Rapport mensuel"])
    ws.append(["."])

    # --- premier sous-relevé : le préambule utilise ses propres étiquettes
    ws.append(["Compte Orange Money :", None, None, "600000001"])
    ws.append(["Coordonnées entrepris", None, None, "POINT DE VENTE UN - Cameroun, 000000, Ville"])
    ws.append(["Contact chez le client :", None, None, "USSD - 600000001 RELEVE MAI 2026 ACCUEIL"])
    ws.append(["."])
    _entetes_releve(ws, brouilles=False)
    ws.append([None, None, None, "Transactions échouées", "Wallet Normal", None, None, None,
               "600000001", "Normal", None, None, None, None, 0])
    ws.append(_transaction(1, "03/05/2026", "10:00:00", "MP260503.1000.A00001",
                           "Merchant Payment", "Echec", "600000001", "690000011", credit=50000))
    ws.append(["Total", None, None, "Transactions échouées", "Wallet Normal", None, None, None,
               "600000001", "Normal", None, "Total échecs", None, None, 50000])
    ws.append([None, None, None, "Transactions réussies", "Wallet Normal", None, None, None,
               "600000001", "Normal", None, "Solde initial", None, None, 100000])
    ws.append(_transaction(2, "12/05/2026", "11:10:44", "MP260512.1110.B00002",
                           "Merchant Payment", "Succès", "600000001", "690000012",
                           credit=75000, commission=-750))
    ws.append(_transaction(3, "12/05/2026", "14:02:19", "MP260512.1402.C00003",
                           "Merchant Payment", "Succès", "600000001", "690000013",
                           credit=120500, commission=-1205))
    ws.append(_transaction(4, "12/05/2026", "17:35:08", "MP260512.1735.D00004",
                           "Merchant Payment", "Succès", "600000001", "690000014",
                           credit=75000, commission=-750))
    ws.append(_transaction(5, "12/05/2026", "20:11:02", "MP260512.2011.E00005",
                           "Merchant Payment", "Succès", "600000001", "690000015",
                           credit=3500, commission=-35))
    ws.append(_transaction(6, "18/05/2026", "08:45:00", "MP260518.0845.F00006",
                           "Merchant Payment", "Succès", "600000001", "690000016",
                           credit=9000, commission=-90))
    ws.append(["Relevé de vos opérations", None, None, "Transactions réussies", "Wallet Normal",
               None, None, None, "600000001", "Normal", None, "Total activités", None, None, 283000])
    ws.append(["."])

    # --- second sous-relevé : préambule ré-étiqueté, en-têtes brouillés
    ws.append(["Application :", None, None, "600000002"])
    ws.append(["Fin de Période :", None, None, "POINT DE VENTE DEUX - Cameroun, 000000, Ville"])
    ws.append(["Orange Money", None, None, "USSD - 600000002 RELEVE MAI 2026 RESTAURANT"])
    ws.append(["."])
    _entetes_releve(ws, brouilles=True)
    ws.append(_transaction(7, "12/05/2026", "19:20:30", "MP260512.1920.G00007",
                           "Merchant Payment", "Succès", "600000002", "690000017",
                           credit=12000, commission=-120))
    ws.append(_transaction(8, "12/05/2026", "21:05:57", "PP260512.2105.H00008",
                           "C2C Transfer", "Succès", "600000002", "600000001",
                           credit=200000))
    # Ligne de commission : un numéro, aucune date.
    ws.append([9, None, None, None, "  Commissions", None, None, None, "600000002", "Normal",
               None, "600000002", None, 4500])
    ws.append(["Relevé de vos opérations", None, None, "Transactions réussies", "Wallet Normal",
               None, None, None, "600000002", "Normal", None, "Solde final", None, None, 95000])
    return wb


if __name__ == "__main__":
    journal_des_arrhes().save(ICI / "journal_arrhes_exemple.xlsx")
    releve_orange_money().save(ICI / "releve_om_exemple.xlsx")
    print("fixtures générées dans", ICI)
