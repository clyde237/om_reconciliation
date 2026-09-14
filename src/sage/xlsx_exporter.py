"""Exportateur au format Excel formaté pour importation Sage."""

from pathlib import Path
import pandas as pd


class SageXlsxExporter:
    """Exporte les écritures préparées dans un classeur Excel propre."""

    @staticmethod
    def export(df_sage: pd.DataFrame, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_sage.to_excel(output_path, index=False)
        return output_path
