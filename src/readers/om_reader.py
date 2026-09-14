"""Lecteur des relevés et extraits Orange Money."""

from pathlib import Path
from typing import Union
import pandas as pd


class OMReader:
    """Charge et parse les relevés de transactions Orange Money."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)

    def read(self) -> pd.DataFrame:
        """Lit le relevé Orange Money (Excel ou CSV)."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable: {self.filepath}")

        if self.filepath.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(self.filepath)
        elif self.filepath.suffix.lower() == ".csv":
            df = pd.read_csv(self.filepath)
        else:
            raise ValueError(f"Format non supporté: {self.filepath.suffix}")

        return df
