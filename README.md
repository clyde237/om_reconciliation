# OM Reconciliation (Rapprochement Orange Money & Journal des Encaissements)

Plateforme automatisée de rapprochement financier entre les relevés **Orange Money (OM)** mensuels et les **Journaux des Encaissements** quotidiens (arrhes de réservation et factures directes des points de vente), avec génération d'audit Excel 7 feuilles et écritures d'intégration comptable pour **Sage 100**.

---

## 📌 Fonctionnalités Clés

1. **Ingestion multi-sources & multi-journaux :**
   - Importation du relevé mensuel Orange Money multi-comptes (Kotibé, Baleng, Réception, Agrégateur).
   - Téléversement d'un ou plusieurs Journaux des Encaissements quotidiens avec ventilation par mode de paiement.
   - Contrôle automatique d'intégrité de lecture par rapport aux totaux déclarés dans le bloc « RECAPITULATIF » du journal.

2. **Moteur de normalisation :**
   - Standardisation des dates (formats hétérogènes, dates valeurs vs opérations).
   - Nettoyage des montants (`Decimal` strict, devises, espaces insécables, séparateurs).
   - Extraction et homogénéisation des références (réservations, factures Kotibé/Baleng, IDs de transaction OM).
   - Détection de la nature comptable (`est_arrhe` : arrhes vs factures directes).

3. **Moteur de réconciliation intelligent (Matching en cascade) :**
   - Rapprochement exact (ID transaction / montant exact).
   - Rapprochement sur date et montant.
   - Combinaison de lignes (ex. règlement OM unique pour plusieurs factures directes).
   - Rapprochement flou multi-critères.
   - Détection de doublons (journal et relevé).
   - Qualification des flux orphelins (recette du jour non inscrite aux encaissements).

4. **Contrôle mensuel de campagne :**
   - Détection des journées du relevé non couvertes (absence de journal déposé).
   - Détection des journées déposées en doublon.
   - Taux de couverture du relevé et taux de rapprochement consolidé.

5. **Livrables d'audit & Validation :**
   - Rapport Excel d'audit complet à 7 feuilles conforme au cahier des charges §9.
   - Support du rapport mensuel consolidé et du rapport journalier.
   - Workflow de validation humaine motivée pour levée du verrou comptable.

6. **Génération & Export Sage 100 :**
   - Spécification et format d'export **PNM** (validé sur échantillons Sage réels).
   - Ventilation automatique : Arrhes individuelles (41910000), Factures directes (41110000), Recette du jour (70600000), Trésorerie OM (55300000 / MOMO).

---

## 📁 Architecture du Projet

```text
om_reconciliation/
│
├── app.py                      # Point d'entrée Streamlit
├── requirements.txt            # Dépendances Python
├── README.md                   # Documentation du projet
├── ROADMAP.md                  # Suivi des phases et jalons
├── .gitignore                  # Fichiers ignorés par Git
├── .env.example                # Modèle de variables d'environnement
│
├── config/                     # Configurations globales
│   ├── __init__.py
│   ├── settings.py             # Paramètres système, colonnes et chemins
│   ├── sage_config.py          # Configuration comptable Sage (disposition PNM)
│   └── matching_config.py      # Seuils, cascade et statuts de rapprochement
│
├── data/                       # Données
│   ├── input/                  # Fichiers sources à réconcilier
│   │   ├── journal_encaissements/ # Journaux quotidiens des encaissements
│   │   └── releves_om/         # Relevés Orange Money mensuels
│   ├── output/                 # Rapports et fichiers exports générés
│   └── templates/              # Gabarits et échantillons PNM
│
├── src/                        # Coeur logique métier
│   ├── readers/                # Parseurs (EncaissementsReader, OMReader)
│   ├── normalization/          # Nettoyage et standardisation (dates, montants, texte)
│   ├── matching/               # Cascade de matching et campagne mensuelle
│   ├── analysis/               # Synthèse mensuelle, anomalies, doublons, validation
│   ├── sage/                   # Exportateurs Sage (PNM, TXT, XLSX)
│   ├── reports/                # Générateur Excel d'audit 7 feuilles (OpenPyXL)
│   └── utils/                  # Fonctions transverses (logger, helpers)
│
├── ui/                         # Interface graphique (Streamlit)
│   ├── dashboard.py            # Vue KPIs, bandeau mensuel & téléchargement Excel
│   ├── upload.py               # Vue de téléversement multi-journaux
│   ├── reconciliation_view.py  # Vue détaillée du rapprochement avec filtres
│   ├── anomalies_view.py       # Vue d'audit, décisions et verrou d'export
│   ├── sage_export_view.py     # Vue d'export comptable Sage
│   ├── session.py              # Gestion d'état de session Streamlit
│   └── components.py           # Composants graphiques réutilisables
│
├── tests/                      # Suite de tests unitaires (pytest)
└── assets/                     # Ressources graphiques et styles CSS
```

---

## 🚀 Installation & Démarrage

### 1. Cloner ou naviguer dans le dossier
```bash
cd om_reconciliation
```

### 2. Créer un environnement virtuel
```bash
python3 -m venv .venv
source .venv/bin/activate  # Sous Linux/macOS
# ou .venv\Scripts\activate sous Windows
```

### 3. Installer les dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
```bash
cp .env.example .env
```

### 5. Lancer l'application
```bash
streamlit run app.py
```

---

## 🧪 Exécution des Tests

Pour exécuter tous les tests unitaires :
```bash
pytest tests/ -v
```
