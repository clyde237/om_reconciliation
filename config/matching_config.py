"""Paramètres et seuils pour les algorithmes de rapprochement."""

from dataclasses import dataclass
from enum import Enum


class MatchStatus(str, Enum):
    """Les neuf statuts métier du rapprochement (cahier des charges §6)."""

    CONFORME = "CONFORME"
    ECART_MONTANT = "ECART_MONTANT"
    MANQUANT_OM = "MANQUANT_OM"
    MANQUANT_JOURNAL = "MANQUANT_JOURNAL"
    DOUBLON = "DOUBLON"
    CORRESPONDANCE_PROBABLE = "CORRESPONDANCE_PROBABLE"
    CORRESPONDANCE_GROUPEE = "CORRESPONDANCE_GROUPEE"
    STATUT_OM_INVALIDE = "STATUT_OM_INVALIDE"
    A_CONTROLER = "A_CONTROLER"
    RECETTE_JOUR = "RECETTE_JOUR"
    PAIEMENT_POSTERIEUR_A_SAISIE = "PAIEMENT_POSTERIEUR_A_SAISIE"


#: Statut ajouté aux neuf du §6, imposé par les sources réelles.
#:
#: Le relevé Orange Money porte tous les encaissements du point de vente, le journal
#: des arrhes seulement les arrhes. Les encaissements de la journée qui ne
#: correspondent à aucune arrhe ne sont donc pas des manquants : ce sont les recettes
#: ordinaires du jour. Le grand livre client le confirme — 88 recettes agrégées
#: « SVT JNAL MOMO DU <date> » pour 9 arrhes individuelles « AVCE <NOM> ».
#:
#: Arbitrage du 16/09/2026 : le résidu devient la recette du jour. Sans cette règle,
#: chaque contrôle déclencherait le verrou d'export sur des opérations normales.
STATUT_RESIDU_OM = MatchStatus.RECETTE_JOUR


#: Statuts qui bloquent l'export Sage tant qu'ils ne sont pas validés manuellement.
#: Arbitrage du 15/09/2026 : écart de montant, manquants (des deux côtés), à contrôler.
#: `RECETTE_JOUR` n'en fait pas partie : c'est une opération normale, pas une anomalie.
BLOCKING_STATUSES: frozenset[MatchStatus] = frozenset({
    MatchStatus.ECART_MONTANT,
    MatchStatus.MANQUANT_OM,
    MatchStatus.MANQUANT_JOURNAL,
    MatchStatus.A_CONTROLER,
    MatchStatus.PAIEMENT_POSTERIEUR_A_SAISIE,
})


class MatchLevel(int, Enum):
    """Niveaux de la cascade de rapprochement (§4), du plus sûr au plus faible."""

    REFERENCE_MONTANT = 1
    DATE_MONTANT = 2
    DATE_MONTANT_CLIENT = 3
    MONTANT_DATE_TOLERANCE = 4
    COMBINAISON_LIGNES = 5


#: Niveaux au-delà desquels une correspondance est soumise à validation humaine.
PROBABLE_FROM_LEVEL = MatchLevel.DATE_MONTANT_CLIENT


#: Invariant de contrôle d'une journée, vérifié par l'analyse (§8) :
#:
#:     total des encaissements OM du jour
#:       = arrhes rapprochées + recette du jour + écarts non résolus
#:
#: Le contrôleur garde donc la main : une ligne classée en recette peut être
#: requalifiée manuellement en `MANQUANT_JOURNAL` si elle aurait dû être une arrhe.


@dataclass(frozen=True)
class MatchingConfig:
    tolerance_days: int = 3
    amount_tolerance: float = 0.0
    fuzzy_similarity_threshold: float = 85.0
    auto_validate_exact: bool = True
    consider_fees: bool = True
    #: Nombre maximal de lignes du journal regroupées sur une seule opération OM (niveau 5).
    max_group_size: int = 3


DEFAULT_MATCHING_CONFIG = MatchingConfig()
