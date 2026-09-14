# OM Reconciliation (Rapprochement Orange Money & Journal des Arrhes)

Plateforme automatisée de rapprochement financier entre les relevés **Orange Money (OM)** et le **Journal des Arrhes / Acomptes** avec génération d'écritures d'intégration comptable pour **Sage 100**.

---

## 📌 Fonctionnalités Clés

1. **Ingestion multi-formats :**
   - Importation des relevés Orange Money (Excel / CSV).
   - Importation du Journal des Arrhes comptable (Excel / CSV).
   - Modèle de gabarit Sage personnalisable.

2. **Moteur de normalisation :**
   - Standardisation des dates (formats hétérogènes, dates valeurs vs opérations).
   - Nettoyage des montants (devises, espaces insécables, séparateurs).
   - Extraction et homogénéisation des références de transactions (ID OM, références arrhes).
   - Normalisation textuelle (accents, libellés, noms de clients).

3. **Moteur de réconciliation intelligent (Matching) :**
   - Rapprochement exact (ID transaction + montant exact).
   - Rapprochement flou (libellés similaires, fenêtres de dates glissantes).
   - Détection des transactions orphelines (omissions OM ou journal).
   - Détection avancée des doublons (multiples débits/crédits pour une même référence).

4. **Analyse & Détection d'anomalies :**
   - Écarts de montants sur transactions identifiées.
   - Retards de comptabilisation.
   - Synthèse mensuelle et indicateurs de couverture.

5. **Génération & Export Sage :**
   - Formats exportables : **PNM** (paramétrable Sage), **TXT** structuré, et **Excel**.
   - Affectation automatique des comptes généraux (512xxx Trésorerie, 4191xx Arrhes/Acomptes).

6. **Interface Utilisateur Moderne (Streamlit) :**
   - Tableau de bord synthétique avec KPI financiers.
   - Interface de chargement des fichiers.
   - Grilles de rapprochement interactives avec validation manuelle.
   - Espace dédié à l'audit des anomalies et téléchargement des exports.

---

## 📁 Architecture du Projet

```text
om_reconciliation/
│
├── app.py                      # Point d'entrée principal de l'application
├── requirements.txt            # Dépendances Python
├── README.md                   # Documentation du projet
├── .gitignore                  # Fichiers ignorés par Git
├── .env.example                # Modèle de variables d'environnement
│
├── config/                     # Configurations globales
│   ├── __init__.py
│   ├── settings.py             # Paramètres système et chemins
│   ├── sage_config.py          # Configuration comptable Sage
│   └── matching_config.py      # Seuils et paramètres de réconciliation
│
├── data/                       # Stockage des données
│   ├── input/                  # Fichiers sources à réconcilier
│   │   ├── journal_arrhes/     # Fichiers du journal comptable des arrhes
│   │   └── releves_om/         # Extraits et relevés Orange Money
│   ├── output/                 # Rapports et fichiers exports générés
│   └── templates/              # Gabarits (ex: om_sage_template.xlsx)
│
├── src/                        # Coeur logique métier
│   ├── readers/                # Parseurs de fichiers (Excel, CSV, templates)
│   ├── normalization/          # Nettoyage et standardisation des données
│   ├── matching/               # Algorithmes de matching (exact, flou, doublons)
│   ├── analysis/               # Moteur d'audit, détection d'écarts et synthèses
│   ├── sage/                   # Générateurs d'écritures Sage (TXT, PNM, XLSX)
│   ├── reports/                # Conception des rapports financiers Excel détaillés
│   └── utils/                  # Fonctions transverses (logger, validateurs, helpers)
│
├── ui/                         # Interface graphique (Streamlit)
│   ├── dashboard.py            # Vue KPIs & graphiques
│   ├── upload.py               # Vue de téléversement des fichiers
│   ├── reconciliation_view.py  # Vue détaillée du rapprochement
│   ├── anomalies_view.py       # Vue d'analyse des anomalies & écarts
│   ├── sage_export_view.py     # Vue de génération et export Sage
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
