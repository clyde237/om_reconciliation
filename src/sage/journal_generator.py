"""Générateur de lignes de journal comptable équilibrées."""

import pandas as pd
from config.sage_config import SageConfig, DEFAULT_SAGE_CONFIG


class SageJournalGenerator:
    """Crée les écritures comptables d'OD ou de Trésorerie pour Sage."""

    def __init__(self, config: SageConfig = DEFAULT_SAGE_CONFIG):
        self.config = config

    def generate(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """Génère les paires débit (banque OM 512) et crédit (arrhes 4191) équilibrées."""
        return pd.DataFrame()
