"""Configuration comptable spécifique à l'environnement Sage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SageConfig:
    journal_code: str = "BQ_OM"
    om_bank_account: str = "512100"       # Compte Banque Orange Money
    arrhes_account: str = "419100"        # Compte Clients - Avances et Acomptes reçus
    commissions_account: str = "627800"   # Compte Frais et Commissions OM
    currency: str = "XAF"
    date_format_sage: str = "%d%m%y"      # Format classique Sage JJMMAA
    piece_ref_prefix: str = "OM-"


DEFAULT_SAGE_CONFIG = SageConfig()
