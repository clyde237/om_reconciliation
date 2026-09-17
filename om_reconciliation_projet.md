# OM Reconciliation — Cahier des charges technique

## 1. Objectif

**Nom technique provisoire :** `om_reconciliation`  
**Technologie :** Python + Streamlit

L'application automatise le contrôle de conformité des encaissements Orange Money en comparant le **Journal des arrhes** avec le **Relevé mensuel Orange Money**.

Le résultat est un **nouveau fichier Excel d'audit** contenant les correspondances, écarts, transactions manquantes, doublons et observations automatiques.

Après validation du contrôle, l'application génère les écritures comptables destinées à **Sage 100 Comptabilité**.

> **OM SAGE.xlsx est uniquement un modèle d'écriture comptable finale. Il ne sert pas de source pour le rapprochement.**

## 2. Flux métier

```text
Journal des arrhes
        +
Relevé Orange Money
        ↓
Normalisation
        ↓
Rapprochement automatique
        ↓
Analyse des anomalies
        ↓
Rapport Excel d'audit
        ↓
Validation humaine
        ↓
Mapping selon OM SAGE.xlsx
        ↓
Export Sage : XLSX / TXT / PNM
```

## 3. Sources

### Journal des arrhes

Informations exploitées selon les colonnes disponibles :
- date ;
- référence ;
- client/compte ;
- mode de paiement ;
- montant ;
- libellé ;
- autres champs utiles.

### Relevé Orange Money

Le relevé mensuel est la source de référence des transactions OM :
- numéro/référence ;
- date ;
- heure ;
- service ;
- paiement ;
- statut ;
- agent ;
- correspondant ;
- débit ;
- crédit ;
- montant ;
- autres champs disponibles.

### OM SAGE.xlsx

Ce fichier définit uniquement la structure de l'écriture comptable finale :
- journal ;
- comptes ;
- date ;
- pièce ;
- libellé ;
- débit/crédit ;
- ordre et format des colonnes.

## 4. Règles de rapprochement

Le moteur travaille par niveaux :

1. **Référence exacte + montant**
2. **Date + montant**
3. **Date + montant + client/correspondant**
4. **Montant + date avec tolérance configurable**
5. **Recherche de combinaison de plusieurs lignes** lorsque des encaissements peuvent être regroupés.

Les correspondances faibles sont marquées comme probables et soumises à validation.

## 5. Normalisation

### Montants

Les formats `90 200`, `90.200`, `90200`, `90 200,00` ou `90 200 FCFA` doivent être normalisés vers une valeur monétaire unique.

Les calculs utilisent `Decimal`, pas `float`.

### Dates

Les formats `16/04/2026`, `16-04-2026`, `16/04/26` et `2026-04-16` sont convertis vers un format interne commun.

### Références et textes

Nettoyage des espaces, casse, caractères parasites et formats équivalents.

## 6. Statuts

| Statut | Signification |
|---|---|
| `CONFORME` | Correspondance confirmée |
| `ECART_MONTANT` | Correspondance mais montant différent |
| `MANQUANT_OM` | Présent dans le journal, absent du relevé OM |
| `MANQUANT_JOURNAL` | Présent dans OM, absent du journal |
| `DOUBLON` | Transaction potentiellement enregistrée plusieurs fois |
| `CORRESPONDANCE_PROBABLE` | Correspondance plausible à valider |
| `CORRESPONDANCE_GROUPEE` | Plusieurs lignes correspondent à une opération regroupée |
| `STATUT_OM_INVALIDE` | Transaction non exploitable |
| `A_CONTROLER` | Cas non résolu automatiquement |

## 7. Observations automatiques

Exemples :
- `Correspondance exacte trouvée.`
- `Montant identique, date différente d'un jour.`
- `Transaction présente dans le journal mais introuvable dans le relevé OM.`
- `Transaction OM présente mais aucune ligne correspondante dans le journal.`
- `Écart de montant constaté : 25 000 FCFA.`
- `Doublon potentiel détecté.`

## 8. Contrôles globaux

L'application calcule :
- nombre de lignes du journal ;
- nombre de transactions OM ;
- total journal ;
- total OM ;
- total rapproché ;
- total non rapproché ;
- montant des écarts ;
- conformités ;
- manquants ;
- doublons ;
- anomalies.

## 9. Rapport Excel final

Nom exemple :

`Rapprochement_OM_Avril_2026.xlsx`

Feuilles :

### `Synthèse`
Période, totaux, écarts, nombre de transactions et statut global.

### `Rapprochement`
Une ligne par opération :

| Date | Référence | Client | Montant Journal | Montant OM | Écart | Statut | Observation |
|---|---|---|---:|---:|---:|---|---|

### `Anomalies`
Toutes les opérations nécessitant une intervention.

### `Manquants_Journal`
Transactions OM absentes du journal.

### `Manquants_OM`
Transactions du journal absentes du relevé OM.

### `Doublons`
Transactions potentiellement enregistrées plusieurs fois.

### `Contrôle_Mensuel`
Totaux et résultats par mois.

## 10. Validation

L'export Sage est séparé du rapport d'audit.

```text
IMPORT → RAPPROCHEMENT → ANALYSE → RAPPORT → VALIDATION → EXPORT SAGE
```

Si des anomalies bloquantes restent non validées :

```text
EXPORT SAGE = BLOQUÉ
```

L'utilisateur peut examiner et valider manuellement les cas nécessaires.

## 11. Génération Sage 100

Après validation :

```text
Transactions validées
        ↓
Mapping selon OM SAGE.xlsx
        ↓
Génération écriture comptable
```

Le système doit reproduire fidèlement la structure du modèle Sage : colonnes, dates, journal, comptes, libellés, références et débit/crédit.

### XLSX

Le classeur suit exactement la structure définie pour le processus d'import Sage.

### TXT

Le format est configurable :
- séparateur ;
- encodage ;
- ordre des champs ;
- dates ;
- nombres ;
- en-tête.

### PNM

Le format `.pnm` ne doit pas être inventé. Il doit être implémenté à partir d'un fichier PNM réel produit par Sage ou d'une spécification fiable du format attendu par l'installation Sage 100.

## 12. Architecture

```text
om_reconciliation/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── sage_config.py
│   └── matching_config.py
│
├── data/
│   ├── input/
│   │   ├── .gitkeep
│   │   ├── journal_arrhes/
│   │   └── releves_om/
│   ├── output/
│   │   └── .gitkeep
│   └── templates/
│       └── om_sage_template.xlsx
│
├── src/
│   ├── __init__.py
│   ├── readers/
│   │   ├── __init__.py
│   │   ├── journal_reader.py
│   │   ├── om_reader.py
│   │   └── sage_template_reader.py
│   ├── normalization/
│   │   ├── __init__.py
│   │   ├── dates.py
│   │   ├── amounts.py
│   │   ├── references.py
│   │   └── text.py
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── matcher.py
│   │   ├── exact_match.py
│   │   ├── fuzzy_match.py
│   │   ├── amount_match.py
│   │   ├── date_match.py
│   │   └── duplicate_detector.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── reconciliation.py
│   │   ├── anomalies.py
│   │   ├── missing.py
│   │   ├── duplicates.py
│   │   └── monthly_summary.py
│   ├── sage/
│   │   ├── __init__.py
│   │   ├── mapper.py
│   │   ├── journal_generator.py
│   │   ├── txt_exporter.py
│   │   ├── pnm_exporter.py
│   │   └── xlsx_exporter.py
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── excel_report.py
│   │   ├── formatting.py
│   │   └── summary.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── validators.py
│       └── helpers.py
│
├── ui/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── upload.py
│   ├── reconciliation_view.py
│   ├── anomalies_view.py
│   ├── sage_export_view.py
│   └── components.py
│
├── tests/
│   ├── __init__.py
│   ├── test_amounts.py
│   ├── test_dates.py
│   ├── test_matching.py
│   ├── test_reconciliation.py
│   ├── test_anomalies.py
│   └── test_sage_export.py
│
└── assets/
    ├── logo.png
    └── styles.css
```

## 13. Rôle des modules

- `app.py` : point d'entrée Streamlit.
- `readers/` : lecture des fichiers Excel.
- `normalization/` : normalisation dates, montants, références et textes.
- `matching/` : moteur de rapprochement.
- `analysis/` : classement et analyse des anomalies.
- `reports/` : génération du rapport Excel.
- `sage/` : génération des écritures comptables.
- `ui/` : interface Streamlit.
- `tests/` : tests automatiques.
- `config/` : paramètres métier et configuration Sage.
- `data/templates/` : modèle d'écriture Sage.

## 14. Interface Streamlit

### Étape 1 — Import

```text
JOURNAL DES ARRHES
[ Sélectionner le fichier ]

RELEVÉ ORANGE MONEY
[ Sélectionner le fichier ]

MODÈLE SAGE
[ Sélectionner le modèle ]

Période
[ Avril 2026 ]

[ LANCER LE CONTRÔLE ]
```

### Étape 2 — Résultats

Afficher notamment :

```text
Transactions journal      250
Transactions OM           252
Conformes                 238
Écarts                      3
Manquants OM                7
Manquants journal            4
Doublons                     0
```

### Étape 3 — Anomalies

Table filtrable par statut.

### Étape 4 — Validation

```text
[ Valider les anomalies sélectionnées ]
[ Valider toute la période ]
```

### Étape 5 — Export

```text
[ Télécharger rapport Excel ]

Format Sage :
( ) XLSX
( ) TXT
( ) PNM

[ Générer l'écriture ]
```

## 15. Technologies

- Python 3.11+
- Streamlit
- Pandas
- OpenPyXL
- Python-dateutil
- Decimal
- RapidFuzz (optionnel pour les rapprochements textuels)

## 16. Sécurité

Les fichiers comptables doivent être traités localement lorsque possible.

L'application doit :
- éviter l'envoi des données vers des services externes ;
- supprimer les fichiers temporaires après traitement ;
- limiter la conservation des données ;
- ne pas exposer les données sensibles dans les logs.

## 17. Tests

Prévoir des tests pour :
- montants ;
- dates ;
- références ;
- correspondances exactes ;
- correspondances avec tolérance ;
- manquants ;
- doublons ;
- écarts ;
- totaux ;
- rapport Excel ;
- export XLSX ;
- export TXT ;
- export PNM lorsque son format est spécifié.

## 18. Évolutions possibles

L'architecture doit pouvoir accueillir plus tard :
- MTN Mobile Money ;
- rapprochement bancaire ;
- contrôle caisse ;
- plusieurs sociétés ;
- plusieurs comptes OM ;
- historique des contrôles ;
- archivage ;
- gestion des utilisateurs ;
- validation multi-niveaux ;
- journal des modifications ;
- génération automatisée des écritures comptables.

## 19. Règle métier fondamentale

Le système doit toujours séparer :

**CONTRÔLE**

et

**COMPTABILISATION**.

Une opération du Journal des arrhes ne doit pas devenir automatiquement une écriture comptable simplement parce qu'elle existe dans le journal.

Elle doit être :

```text
identifiée
+
rapprochée avec le relevé OM
+
contrôlée
+
validée
```

avant de pouvoir alimenter l'export Sage.

Ainsi, l'automatisation accélère le travail du contrôleur tout en évitant de transformer automatiquement une anomalie en écriture comptable.
