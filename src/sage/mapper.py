"""Mappeur de données transactionnelles vers le schéma comptable Sage."""

from config.sage_config import SageConfig, DEFAULT_SAGE_CONFIG
import pandas as pd


class SageMapper:
    """Mappe les transactions validées en colonnes compatibles Sage 100."""

    def __init__(self, config: SageConfig = DEFAULT_SAGE_CONFIG):
        self.config = config

    def map_to_sage_schema(self, reconciled_df: pd.DataFrame) -> pd.DataFrame:
        """Transforme les flux réconciliés en lignes de débits/crédits pour Sage."""
        return pd.DataFrame(columns=[
            "Code_Journal", "Date", "N_Piece", "N_Compte", "Compte_Tiers", "Libelle", "Debit", "Credit", "Reference"
        ])
