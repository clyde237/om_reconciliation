"""Exportateur au format texte structuré Sage."""

from pathlib import Path
import pandas as pd


class SageTxtExporter:
    """Exporte les écritures au format texte délimité selon les spécifications Sage."""

    @staticmethod
    def export(df_sage: pd.DataFrame, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_sage.to_csv(output_path, sep=";", index=False, encoding="latin-1")
        return output_path
