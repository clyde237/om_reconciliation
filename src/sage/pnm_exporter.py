"""Exportateur au format PNM propriétaire Sage."""

from pathlib import Path
import pandas as pd


class SagePnmExporter:
    """Exporte les écritures au format PNM (Paramétrable Sage)."""

    @staticmethod
    def export(df_sage: pd.DataFrame, output_path: Path) -> Path:
        """Génère le fichier .pnm d'intégration Sage."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="latin-1") as f:
            f.write("# SAGE 100 IMPORT PNM FORMAT\n")
        return output_path
