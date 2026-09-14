"""Paramètres généraux de l'application."""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
TEMPLATES_DIR = DATA_DIR / "templates"

JOURNAL_ARRHES_DIR = INPUT_DIR / "journal_arrhes"
RELEVES_OM_DIR = INPUT_DIR / "releves_om"
ASSETS_DIR = BASE_DIR / "assets"

APP_TITLE = "OM Reconciliation"
APP_VERSION = "1.0.0"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
