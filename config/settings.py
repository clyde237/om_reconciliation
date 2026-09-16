"""Paramètres généraux de l'application."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _chemin(variable: str, defaut: Path) -> Path:
    """Lit un chemin dans l'environnement ; un chemin relatif part de la racine du projet."""
    brut = os.getenv(variable)
    if not brut:
        return defaut
    chemin = Path(brut).expanduser()
    return chemin if chemin.is_absolute() else BASE_DIR / chemin


DATA_DIR = BASE_DIR / "data"
INPUT_DIR = _chemin("DATA_INPUT_DIR", DATA_DIR / "input")
OUTPUT_DIR = _chemin("DATA_OUTPUT_DIR", DATA_DIR / "output")
TEMPLATES_DIR = _chemin("DATA_TEMPLATES_DIR", DATA_DIR / "templates")

JOURNAL_ARRHES_DIR = INPUT_DIR / "journal_arrhes"
RELEVES_OM_DIR = INPUT_DIR / "releves_om"
ASSETS_DIR = BASE_DIR / "assets"

APP_TITLE = "OM Reconciliation"
APP_VERSION = "1.0.0"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
APP_DEBUG = os.getenv("APP_DEBUG", "False").strip().lower() in {"1", "true", "yes", "oui"}


# --- Correspondance des colonnes -----------------------------------------------
#
# Les colonnes sont reconnues par alias, jamais par position : ces fichiers sont des
# exports datés, et leur mise en forme bougera. Les clés de comparaison passent par
# `normalize_key` — sans accents, en majuscules, espaces réduits — ce qui absorbe au
# passage les retours à la ligne des en-têtes (« Montant\nEncaissé »).

JOURNAL_COLUMN_ALIASES: dict[str, frozenset[str]] = {
    "date": frozenset({"DATE", "DATE OPERATION", "DATE D'OPERATION"}),
    "compte": frozenset({"COMPTE / RESERVATION", "COMPTE", "CLIENT", "COMPTE/RESERVATION"}),
    "reintegration": frozenset({"REINTEGRATION"}),
    "mode_paiement": frozenset({"ENCAISSEMENT", "MODE DE PAIEMENT", "MODE", "MODE PAIEMENT"}),
    "montant": frozenset({"MONTANT ENCAISSE", "MONTANT", "MONTANT PERCU"}),
    "montant_reintegre": frozenset({"MONTANT REINTEGRE"}),
    "solde": frozenset({"SOLDE NON REINTEGRE", "SOLDE"}),
    "reservation": frozenset({"RESERVATION"}),
}

#: Les en-têtes du relevé sont dédoublés — « N° de Compte » et « Wallet » désignent
#: tantôt l'agent, tantôt le correspondant. La ligne de groupe située juste au-dessus
#: lève l'ambiguïté ; les alias ci-dessous portent donc le groupe en préfixe.
OM_COLUMN_ALIASES: dict[str, frozenset[str]] = {
    "numero": frozenset({"NO", "N"}),
    "date": frozenset({"DATE"}),
    "heure": frozenset({"HEURE"}),
    "reference": frozenset({"REFERENCE"}),
    "service": frozenset({"SERVICE"}),
    "paiement": frozenset({"PAIEMENT"}),
    "statut": frozenset({"STATUT"}),
    "mode": frozenset({"MODE"}),
    "compte_agent": frozenset({"AGENT NO DE COMPTE"}),
    "wallet_agent": frozenset({"AGENT WALLET"}),
    "pseudo": frozenset({"NO PSEUDO", "AGENT NO PSEUDO"}),
    "correspondant": frozenset({"CORRESPONDANT NO DE COMPTE"}),
    "wallet_correspondant": frozenset({"CORRESPONDANT WALLET"}),
    "debit": frozenset({"MONTANT (XAF) DEBIT", "DEBIT"}),
    "credit": frozenset({"MONTANT (XAF) CREDIT", "CREDIT"}),
    "commission_compte": frozenset({"COMMISSIONS (XAF) COMPTE"}),
    "commission": frozenset({"COMMISSIONS (XAF) SOUS-RESEAU", "SOUS-RESEAU"}),
}
