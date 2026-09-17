"""Configuration comptable spécifique à l'environnement Sage 100."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SageConfig:
    """Paramètres de l'écriture comptable générée.

    Valeurs relevées dans le grand livre du client (`OM SAGE.xlsx`, compte 55300000,
    journal MOMO). Les champs marqués « à confirmer » dans docs/sources_reelles.md §4
    restent des hypothèses tant que le comptable ne les a pas arbitrés.
    """

    #: Code journal relevé dans le grand livre client.
    journal_code: str = "MOMO"
    #: Compte de transfert mobile money — libellé Sage : « TRANSFERT VIA MTN MOMO2 ».
    #: À confirmer : un compte distinct existe-t-il pour Orange Money ?
    transfer_account: str = "55300000"
    #: Contrepartie arrhes clients (SYSCOHADA 4191) — à confirmer.
    arrhes_account: str = "41910000"
    #: Commissions Orange Money prélevées à la transaction — à confirmer.
    commissions_account: str = "62780000"
    currency: str = "XAF"
    #: Format de date du format PNM : JJMMAA, confirmé sur les quatre échantillons.
    date_format_sage: str = "%d%m%y"
    #: Gabarit du libellé d'une arrhe individuelle, relevé dans le grand livre.
    label_template_arrhes: str = "AVCE {client} {date}"
    #: Gabarit du libellé de la recette agrégée du jour — le résidu du rapprochement.
    #: Convention la plus récente du grand livre (avril 2026) ; les écritures plus
    #: anciennes écrivent « SVT JRNAL DE CAISSE MOMO <date> ». Saisies à la main, donc
    #: irrégulières : gabarit à confirmer avec le comptable.
    label_template_recette: str = "SVT JNAL MOMO DU {date}"


DEFAULT_SAGE_CONFIG = SageConfig()


#: Longueur du libellé observée dans le grand livre du client. Plusieurs écritures
#: atteignent exactement 35 caractères et aucune ne les dépasse : l'installation Sage
#: du client tient donc un libellé de 35, quand les échantillons PNM n'en montrent
#: que 25. Contradiction ouverte, suivie en B10 (docs/format_pnm.md §4).
LIBELLE_MAX_GRAND_LIVRE = 35


# --- Format PNM ---------------------------------------------------------------
# Relevé par rétro-ingénierie sur quatre fichiers Sage réels.
# Spécification complète et points en suspens : docs/format_pnm.md

PNM_ENCODING = "ascii"
PNM_LINE_ENDING = "\r\n"
PNM_LINE_LENGTH = 199
PNM_HEADER_LENGTH = 30

#: Découpage des 199 caractères : nom -> (position de début, longueur, cadrage).
PNM_LAYOUT: dict[str, tuple[int, int, str]] = {
    "journal":            (0, 3, "left"),
    "date":               (3, 6, "left"),
    "flag_1":             (9, 1, "left"),
    "flag_2":             (10, 1, "left"),
    "compte_general":     (11, 13, "left"),
    "type_ligne":         (24, 1, "left"),
    "code_complementaire": (25, 13, "left"),
    "piece":              (38, 13, "left"),
    "libelle":            (51, 25, "left"),
    "flag_echeance":      (76, 1, "left"),
    "date_echeance":      (77, 6, "left"),
    "sens":               (83, 1, "left"),
    "montant":            (84, 20, "right"),
    "flag_lettrage":      (104, 1, "left"),
    "numero_ecriture":    (109, 3, "left"),
    "devise":             (138, 3, "left"),
    "montant_devise":     (154, 7, "right"),
    "code_devise":        (161, 3, "left"),
    "axe_analytique":     (164, 1, "left"),
}

#: Valeurs constantes sur les quatre échantillons, sémantique inconnue.
PNM_CONSTANTS = {"flag_1": "F", "flag_2": "F", "flag_lettrage": "N"}

#: Préfixes de ligne complémentaire déduits des échantillons.
PNM_TYPE_TIERS = "X"
PNM_TYPE_ECHEANCE = "E"
PNM_TYPE_ANALYTIQUE = "A"
