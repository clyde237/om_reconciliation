# OM Reconciliation — Découpage en phases de développement

> Document de pilotage dérivé de [`om_reconciliation_projet.md`](om_reconciliation_projet.md).
> Mis à jour le 15/09/2026 après analyse des quatre sources réelles.
> Estimations indicatives pour **1 développeur**.

**Documents liés :** [analyse des sources réelles](docs/sources_reelles.md) ·
[format PNM relevé](docs/format_pnm.md)

---

## 1. Lecture rapide

| Phase | Titre | Dépend de | Estim. | Livrable vérifiable |
|---|---|---|---|---|
| **P0** | Socle technique & cadrage | — | 1 j | `pytest` vert, `streamlit run app.py` démarre |
| **P1** | Noyau de normalisation (Decimal, dates, textes) | P0 | 2 j | `normalize_amount("90 200,00 FCFA") -> Decimal("90200.00")` |
| **P2** | Lecture & mapping des colonnes | P1 | 3–4 j | Les 177 transactions OM et les lignes du journal extraites proprement |
| **P3** | Moteur de rapprochement | P2 | 4 j | Le 16/04/2026 rapproché 3/3 sans ambiguïté |
| **P4** | Analyse, statuts & observations | P3 | 3 j | Les 9 statuts + compteurs globaux du §8 |
| **P5** | Rapport Excel d'audit (7 feuilles) | P4 | 2–3 j | `Rapprochement_OM_Avril_2026.xlsx` |
| **P6** | UI Streamlit du contrôle (étapes 1→3) | P5 | 3 j | Parcours import → résultats → anomalies |
| **P7** | Validation humaine & verrou d'export | P6 | 2 j | Export Sage bloqué si anomalie non validée |
| **P8** | Écriture comptable + export PNM / XLSX / TXT | P7 | 4 j | Fichier `.pnm` importé par Sage 100 |
| **P9** | Durcissement : sécurité, perfs, doc | P8 | 2 j | Checklist §16 satisfaite |
| **P10** | Évolutivité (§18) | post-V1 | — | Hors périmètre V1 |

**Jalons :**
- **J1 — Moteur headless** = P0 → P5. Le rapport d'audit est généré par script, sans interface.
- **J2 — V1 Contrôle** = J1 + P6 + P7. Le contrôleur travaille dans l'application, sans export.
- **J3 — V1 Complète** = J2 + P8 + P9.

> **Évolution depuis la première version du plan.** L'export PNM était isolé en phase distincte,
> bloqué faute de spécification. Les quatre échantillons Sage fournis ont levé ce blocage : le
> format est désormais relevé, testé et intégré à P8. Le plan passe de 12 à 11 phases.

---

## 2. Décisions arbitrées le 15/09/2026

| Sujet | Décision |
|---|---|
| **Statuts bloquant l'export** | `ECART_MONTANT`, `MANQUANT_OM`, `MANQUANT_JOURNAL`, `A_CONTROLER` |
| **Version Python** | **3.14** — validée en pratique : Streamlit 1.63, Pandas 3.0.5, OpenPyXL 3.1.5, RapidFuzz 3.14.6, Pydantic 2.13.5, Loguru 0.7.3, Pytest 9.1.1 s'installent et s'importent |
| **Format d'import Sage** | **PNM**, relevé sur quatre fichiers réels et couvert par 15 tests |

Ces choix sont posés dans [`config/matching_config.py`](config/matching_config.py)
(`BLOCKING_STATUSES`) et [`config/sage_config.py`](config/sage_config.py) (`PNM_LAYOUT`).

Deux conséquences de l'arbitrage sur les statuts, à garder en tête :

- **`DOUBLON` ne bloque pas l'export.** Un doublon non détecté comme tel produira deux écritures
  comptables pour un seul encaissement. Le verrou de P7 ne l'en empêchera pas.
- **`CORRESPONDANCE_PROBABLE` ne bloque pas non plus** : une correspondance de niveau 3 ou plus
  partira en comptabilité sans revue. Comme les niveaux 1 et 3 sont inexploitables sur ces
  sources (voir §4), la quasi-totalité des appariements seront de niveau 2 ou 4.

Si ce comportement n'est pas voulu, il suffit d'ajouter les statuts à `BLOCKING_STATUSES` :
le reste du code lit cet ensemble, rien d'autre n'est à changer.

---

## 3. État actuel du dépôt

- L'arborescence du §12 existe intégralement ; les modules sont des **ébauches**.
- Environnement installé et fonctionnel sous **Python 3.14.4**.
- `pytest` : **21 passent, 2 échouent** — `test_amounts.py::test_normalize_amount_formatted`
  et `test_dates.py::test_normalize_dates`. Ces deux échecs sont d'origine : les ébauches de
  normalisation sont fausses. **P1 les remplace**, ce n'est pas une régression.
- Les données client réelles sont dans `data/input/`, **exclu de git** par `.gitignore`.
- Les échantillons PNM (données de démonstration Sage, société fictive « Bijou SA ») sont
  versionnés dans `data/templates/pnm_samples/`.

### Écarts ébauches ↔ cahier des charges

| Fichier | Écart | Statut |
|---|---|---|
| `config/matching_config.py` | 6 statuts anglais | ✅ **corrigé** — 9 statuts métier + `BLOCKING_STATUSES` |
| `config/sage_config.py` | valeurs devinées | ✅ **corrigé** — journal `MOMO`, compte `55300000`, table `PNM_LAYOUT` |
| `src/sage/pnm_exporter.py` | en-tête PNM inventé | ⏳ P8 — à remplacer par la table de positions |
| `src/normalization/amounts.py` | retourne un `float` | ⏳ P1 — `Decimal` exigé au §5 |
| `src/matching/matcher.py` | 2 passes | ⏳ P3 — cascade à 5 niveaux |
| `src/matching/` | pas de regroupement | ⏳ P3 — `group_match.py` à créer |
| `requirements.txt` | `pandas>=2.2.0` installe Pandas **3.0.5** | ⏳ P0 — figer les versions majeures |

---

## 4. Ce que les sources réelles changent au plan

Analyse complète dans [`docs/sources_reelles.md`](docs/sources_reelles.md). Quatre constats
modifient les phases.

### Le relevé OM n'est pas une table — c'est quatre sous-relevés concaténés

Le fichier d'avril contient les comptes `698186110` (agrégateur), `656009773` (Réception),
`691829711` (Kotibé) et `696948928` (Restaurant Baleng), chacun avec son préambule, ses blocs
« échouées » / « réussies » et ses lignes de solde. Les cellules fusionnées rendent les lignes
d'en-tête inexploitables. **P2 doit détecter les lignes de données par leur forme**, pas par le
texte des en-têtes — et passe de 2–3 j à 3–4 j.

De plus, seuls les `Merchant Payment` en `Succès` sont des encaissements clients : les
`C2C Transfer` sont des virements internes au groupe et doivent être écartés du périmètre.

### Les niveaux 1 et 3 du rapprochement sont inexploitables

Le journal des arrhes ne contient **aucune référence Orange Money** — sa colonne de
réintégration porte un numéro de facture, sa colonne compte un numéro de réservation. Et le
relevé identifie le client par son **numéro de téléphone** quand le journal le nomme : aucun
champ commun. Donc :

- niveau 1 (référence + montant) : sans objet sur ces sources ;
- niveau 3 (date + montant + client) : sans objet ;
- niveau 5 (regroupement) : à conserver, mais peu probable sur ces volumes.

**Le travail réel se fait aux niveaux 2 et 4** — `date + montant`, avec tolérance. P3 doit
concentrer son effort là, et les deux niveaux sans objet restent implémentés pour les futures
sources (MTN MoMo, banque) sans être optimisés.

### La consommation des lignes n'est pas une précaution théorique

Le 16/04/2026, le relevé porte **deux encaissements de 90 200** et le journal **deux lignes de
90 200**. Aucune règle ne peut les distinguer : seule la règle « une ligne OM appariée est
consommée » produit un appariement 1-1 correct. Le même montant réapparaît les 11, 12, 14 et
24 avril, ce qui confirme que le montant seul ne discrimine pas.

L'heure, elle, n'est **pas** un critère : le journal horodate la saisie, pas le paiement, avec
des écarts allant jusqu'à 1 h 07 sur les trois cas observés.

### L'export cible est le PNM, pas un classeur

`OM SAGE.xlsx` n'est pas un gabarit d'import : c'est un **grand livre exporté par Sage 100c**
(compte 55300000, journal MOMO). Il reste utile — il donne la forme des écritures visées,
notamment le gabarit `AVCE <NOM CLIENT> <date>` des arrhes — mais le format d'import est le
**PNM**, désormais spécifié et testé.

---

## 5. Points restant à lever

| # | Sujet | Bloque | Ce qu'il faut |
|---|---|---|---|
| B7 | **Compte et journal Orange Money** | P8 | Le grand livre fourni porte le compte `55300000` « TRANSFERT VIA MTN **MOMO2** », journal `MOMO`. Existe-t-il un compte et un journal distincts pour OM, ou les deux opérateurs partagent-ils celui-ci ? |
| B8 | **Contrepartie de l'écriture** | P8 | Le grand livre ne montre qu'un côté. Quelle contrepartie pour une arrhe encaissée par OM ? Et les commissions (~1 % prélevé à la transaction) ? |
| B9 | **Numéro de pièce** | P8 | Les pièces (6417, 6419, 6445…) sont-elles attribuées par Sage à l'import, ou l'export doit-il les fournir ? |
| B10 | **Longueur du libellé** | P8 | Le PNM relevé donne 25 caractères ; les écritures existantes du client vont jusqu'à 35. À vérifier sur l'installation Sage réelle. |
| B11 | **Décimales en XAF** | P8 | Les échantillons sont en EUR à 2 décimales forcées. Sage attend-il `90200.00` ou `90200` en franc CFA ? |
| B12 | **Journal des arrhes sur un mois complet** | P3 | L'export fourni ne couvre **qu'une journée** (16/04/2026) alors que le relevé couvre tout avril. Il faut un export d'avril entier pour valider le moteur à l'échelle réelle. |

B7 à B11 sont regroupés : ils se posent tous au moment d'écrire le mapper, et une seule séance
avec le comptable les tranche. **B12 est le plus urgent** — il conditionne la validation de P3.

---

## Phase 0 — Socle technique & cadrage

**Objectif :** rendre le dépôt exécutable et aligner les ébauches sur le cahier des charges.

- ✅ `venv` Python 3.14.4, dépendances installées et vérifiées.
- ✅ Les 9 statuts métier et `BLOCKING_STATUSES` dans `config/matching_config.py`.
- ✅ Journal, compte et table `PNM_LAYOUT` dans `config/sage_config.py`.
- ⏳ `config/settings.py` : chargement effectif du `.env`.
- ⏳ `src/utils/logger.py` : loguru, **jamais de numéro de téléphone ni de montant client en clair**.
- ⏳ Figer les versions majeures dans `requirements.txt` — Pandas 3.0 change le comportement par défaut.
- ⏳ Jeux de données **anonymisés** dans `tests/fixtures/`, dérivés des fichiers réels.

**Définition de terminé :** `streamlit run app.py` affiche les 5 vues, `pytest` sans échec.

---

## Phase 1 — Noyau de normalisation

**Objectif :** des primitives de domaine fiables, testées, indépendantes de Pandas.

- `amounts.py` → **`Decimal`**. Cas réels à couvrir : `90 200`, `90200`, `90 200,00`,
  `90 200 FCFA`, et l'**espace insécable** que le journal utilise dans
  `Facture N°TH-7206  90 200 FCFA`.
- `dates.py` → gère le **sérial Excel avec heure** du journal (`46128.552777777775` →
  16/04/2026 13:16) et le texte `16/04/2026` du relevé.
- `references.py` → forme canonique des références OM (`MP260416.1311.A17517`).
- `text.py` → accents, ponctuation, et **réduction ASCII** exigée par le format PNM.
- **Modèle canonique** (`src/models.py`, à créer) : `LigneJournal` et `TransactionOM`.

**Tests :** remplace les deux tests actuellement en échec.

**Définition de terminé :** aucun `float` sur un chemin monétaire, tous les formats du §5 testés.

---

## Phase 2 — Lecture & mapping des colonnes

**Objectif :** transformer deux classeurs hétérogènes en deux tables canoniques normalisées.

- **Journal** : la table démarre en ligne 2 ; écarter sous-totaux, note de bas de page,
  pagination et bloc « Récapitulatif ». Lire la période dans la cellule `C1`.
  **Filtrer sur la colonne « Encaissement » = `Orange Money`.**
- **Relevé** : découper les sous-relevés par compte, détecter les lignes de données par leur
  **forme** (colonne A entière, statut ∈ {Succès, Echec}), écarter soldes et totaux.
  Retenir `Merchant Payment`, écarter `C2C Transfer`, isoler les lignes de commission.
  `Statut = Echec` → `STATUT_OM_INVALIDE`.
- **Colonnes par alias**, pas en dur : ce relevé est un export daté, sa mise en forme bougera.
- Rapport d'import : lignes lues, écartées, motif de chaque rejet.

**Définition de terminé :** les 177 transactions sont extraites et ventilées par compte, et
chaque ligne écartée est justifiée.

---

## Phase 3 — Moteur de rapprochement

**Objectif :** le cœur de l'application, recentré sur ce que les sources permettent réellement.

- Cascade sur le **reliquat**, avec **consommation** des lignes appariées — démontré nécessaire
  par le cas du 16/04 (deux fois 90 200 des deux côtés).
- Priorité aux **niveaux 2 et 4** (`date + montant`, puis tolérance). Tolérance de dates
  **étroite** : le même montant réapparaît à plusieurs dates du mois.
- Niveaux 1 et 3 implémentés pour les sources futures, non optimisés.
- `group_match.py` (niveau 5) : borner le nombre de lignes (`max_group_size`) et la fenêtre.
- Détection des doublons des deux côtés.
- **Traçabilité** : chaque appariement porte son niveau et son score.

**Définition de terminé :** le 16/04/2026 est rapproché 3 sur 3, chaque appariement justifié par
une règle nommée. Validation à l'échelle du mois dès que B12 est levé.

---

## Phase 4 — Analyse, statuts & observations

- Table unifiée, une ligne par opération, colonnes du §9.
- Affectation des 9 statuts ; `BLOCKING_STATUSES` détermine ce qui remontera en P7.
- Observations automatiques (§7) par générateur paramétré.
- `monthly_summary.py` + les 11 contrôles globaux du §8, avec l'invariant
  `total rapproché + total non rapproché = total journal`.
- Les commissions OM sont suivies séparément : elles ne sont pas un écart de rapprochement.

---

## Phase 5 — Rapport Excel d'audit

- Les 7 feuilles du §9, mise en forme par statut, format FCFA, volets figés, filtres.
- Nommage `Rapprochement_OM_<Mois>_<Année>.xlsx`, génération en mémoire.
- **Ventilation par compte OM** dans la synthèse : quatre comptes, quatre points de vente.

**🏁 Jalon J1 : le moteur produit le rapport d'audit complet sans interface.**

---

## Phase 6 — UI Streamlit du contrôle (étapes 1 → 3)

- Import, période, lancement ; KPI de l'étape 2 ; table de rapprochement ; anomalies filtrables.
- `st.session_state` comme source de vérité unique, `@st.cache_data`, barre de progression.
- Filtre par compte OM, les quatre points de vente étant dans le même fichier.

---

## Phase 7 — Validation humaine & verrou d'export

> Application de la **règle métier fondamentale du §19**. Phase non optionnelle.

- États `EN_ATTENTE` / `VALIDÉ` / `REJETÉ` par ligne, avec auteur, horodatage et motif.
- Verrou piloté par `BLOCKING_STATUSES` : export désactivé **avec motif affiché**, pas une
  erreur après coup.
- Seules les lignes `CONFORME` ou explicitement validées alimentent P8.
- Journal des décisions persisté.

**Définition de terminé :** un test prouve qu'une anomalie non validée rend l'export impossible
et qu'une ligne rejetée n'apparaît jamais dans l'écriture.

**🏁 Jalon J2 : V1 Contrôle.**

---

## Phase 8 — Écriture comptable & exports

> Nécessite B7 à B11.

- `mapper.py` : transactions validées → lignes comptables. Gabarit `AVCE <NOM CLIENT> <date>`
  relevé dans le grand livre client. Contrôle d'**équilibre bloquant** par pièce et sur le lot.
- `pnm_exporter.py` : piloté par `PNM_LAYOUT`, jamais par des concaténations codées en dur.
  Réduction ASCII obligatoire. Dépassement de champ → **échec explicite ou troncature tracée**,
  jamais silencieux.
- `xlsx_exporter.py` et `txt_exporter.py` : formats de confort, paramétrables (§11).
- `ui/sage_export_view.py` : étape 5 du §14.

**Tests :** rejouer les quatre échantillons octet à octet ; équilibre débit/crédit ; troncature.

**Définition de terminé :** le `.pnm` généré est **effectivement importé par Sage 100** — pas
seulement comparé aux échantillons.

---

## Phase 9 — Durcissement

- **Sécurité (§16)** : traitement local, `browser.gatherUsageStats = false`, suppression des
  temporaires, purge configurable des sorties, masquage des numéros dans les logs.
- **Performance** : le niveau 5 est la seule étape combinatoire, la borner et la mesurer.
- **Documentation** : installation, mode d'emploi contrôleur, glossaire des 9 statuts.

**🏁 Jalon J3 : V1 Complète.**

---

## Phase 10 — Évolutivité (post-V1, §18)

À ne pas anticiper en code, mais à ne pas empêcher par l'architecture :

- **MTN MoMo, banque, caisse** → `readers/` et `normalization/` restent indépendants de la
  source ; le moteur ne connaît que le modèle canonique. Le compte Sage étant déjà un compte
  « MOMO », MTN est l'extension la plus proche.
- **Multi-comptes OM** → déjà nécessaire en V1 : le relevé en contient quatre.
- **Multi-sociétés** → rendre `SageConfig` sélectionnable plutôt que global.
- **Historique, archivage, utilisateurs, validation multi-niveaux** → persistance (SQLite) ;
  le journal des décisions de P7 en est l'amorce.

---

## Règles transverses (toutes phases)

1. **Séparation CONTRÔLE / COMPTABILISATION (§19)** — aucun module de `analysis/` ou `reports/`
   n'importe `sage/`. Le seul point de passage est l'état « validé » de P7.
2. **`Decimal` partout** — aucun `float` entre la lecture et l'export.
3. **Le format relevé fait foi** — `PNM_LAYOUT` est la seule source de vérité des positions.
4. **Ne rien inventer** — ce qui n'est pas démontré par un échantillon est marqué « à confirmer »
   dans `docs/`, pas codé en dur comme un fait.
5. **Traçabilité** — tout appariement porte sa règle et son score ; toute validation son auteur
   et son horodatage.
6. **Un test par règle métier** — chaque statut, chaque niveau, chaque invariant de total.
7. **Les données client ne quittent pas `data/input/`**, exclu de git.
