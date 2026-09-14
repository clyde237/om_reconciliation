"""Lecteur du gabarit d'import Sage."""

from pathlib import Path
from typing import Union
import pandas as pd


class SageTemplateReader:
    """Charge le gabarit de modèle d'importation Sage."""

    def __init__(self, template_path: Union[str, Path]):
        self.template_path = Path(template_path)

    def read_template_columns(self) -> list:
        """Retourne la liste des colonnes attendues pour l'import Sage."""
        if not self.template_path.exists():
            return []
        df = pd.read_excel(self.template_path, nrows=1)
        return list(df.columns)
