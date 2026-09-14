"""Lecteur du journal des arrhes comptable."""

from pathlib import Path
from typing import Union
import pandas as pd


class JournalReader:
    """Charge et valide les fichiers du journal des arrhes (Excel / CSV)."""

    REQUIRED_COLUMNS = ["Date", "Montant", "Reference", "Libelle"]

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)

    def read(self) -> pd.DataFrame:
        """Lit le fichier source et retourne un DataFrame nettoyé préliminairement."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable: {self.filepath}")

        if self.filepath.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(self.filepath)
        elif self.filepath.suffix.lower() == ".csv":
            df = pd.read_csv(self.filepath)
        else:
            raise ValueError(f"Format de fichier non supporté: {self.filepath.suffix}")

        return df
