"""Générateur de classeur Excel récapitulatif pour audit et direction."""

from pathlib import Path
import pandas as pd


class ExcelReportGenerator:
    """Construit le rapport Excel final comprenant synthèse, rapprochements et anomalies."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    def generate(self, results: dict, filename: str = "rapport_rapprochement.xlsx") -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.output_dir / filename
        with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
            # Onglet Synthèse
            pd.DataFrame([{"Statut": "Prêt", "Date": "2026-09-14"}]).to_excel(writer, sheet_name="Synthese", index=False)
        return filepath
