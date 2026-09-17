# OM Reconciliation — Découpage en phases de développement

> Document de pilotage dérivé de [`om_reconciliation_projet.md`](om_reconciliation_projet.md).
> Mis à jour le 16/09/2026 — P0 à P3 livrées.
> Estimations indicatives pour **1 développeur**.

**Documents liés :** [analyse des sources réelles](docs/sources_reelles.md) ·
[format PNM relevé](docs/format_pnm.md)

---

## 1. Lecture rapide

| Phase | Titre | État | Reste | Reliquat |
|---|---|---|---:|---|
| **P0** | Socle technique & cadrage | ✅ | 0,5 j | Logger jamais appelé, versions non figées |
| **P1** | Noyau de normalisation | ✅ | — | — |
| **P2** | Lecture & mapping des colonnes | ✅ | — | — |
| **P3** | Moteur de rapprochement | ✅ | — | — |
| **P4** | Analyse, statuts & observations | ✅ | — | Livrée — observations §7, synthèse mensuelle multi-comptes, 11 contrôles §8 |
| **P5** | Rapport Excel d'audit | ✅ | — | Livrée — classeur complet à 7 feuilles, styles FCFA, filtres et volets figés |
| **P6** | UI du contrôle | ✅ | — | Livrée — filtres par statut et par compte OM, recherche instantanée |
| **P7** | Validation humaine & verrou | ✅ | — | Livrée — journal des décisions, workflow validé/rejeté avec motif, levée du verrou (§19) |
| **P8** | Écriture comptable & exports | ○ | 4 j | Mapper et exportateurs, rien n'existe |
| **P9** | Durcissement | ◐ | 1 j | Masquage des logs, purge, perfs, mode d'emploi |
| **P10** | Évolutivité (§18) | — | — | Hors périmètre V1 |

**✅ terminée · ◐ partielle · ○ non commencée · Reste total : ~5 à 5,5 jours** sur les
26 à 30 estimés au départ (8 phases terminées sur 11).

**Jalons :**
- **J1 — Rapport d'audit complet (Moteur headless + Excel)** = P0 → P5 · **✅ ATTEINT** (16/09/2026).
  Le classeur d'audit exhaustif à 7 feuilles (`Rapprochement_OM_<Mois>_<Année>.xlsx`) est généré
  et téléchargeable dans l'UI.
- **J2 — V1 Contrôle utilisable de bout en bout** = J1 + P6 + P7 · **✅ ATTEINT** (16/09/2026).
  Le contrôleur travaille entièrement dans l'application : filtres multi-critères, recherche,
  audit des écarts, validation/rejet motivé des anomalies et pilotage du verrou comptable.
- **J3 — V1 Complète** = J2 + P8 + P9 · **reste ~5 j**.

> **Où en est-on.** Huit phases sur onze sont terminées, deux sont partielles, une seule
> n'a pas commencé (**P8** : écriture comptable Sage). Les **Jalons J1 et J2 sont atteints**.
> Le seul grand bloc vierge restant pour clore la V1 est P8 (dès confirmation des 5 arbitrages comptables B7-B11).

> **Évolution depuis la première version du plan.** L'export PNM était isolé en phase distincte,
> bloqué faute de spécification. Les quatre échantillons Sage fournis ont levé ce blocage : le
> format est désormais relevé, testé et intégré à P8. Le plan passe de 12 à 11 phases.

---

## 2. Décisions arbitrées le 15/09/2026 & 16/09/2026

| Sujet | Décision |
|---|---|
| **Source principale** | **Journal des encaissements** (au lieu du journal des arrhes seul) — englobe arrhes et factures directes (Kotibé, Baleng, etc.) par mode de paiement (colonne Orange Money) |
| **Contrôle mensuel** | Support de N journaux quotidiens face au relevé mensuel OM, détection des jours non couverts et doublons |
| **Statuts bloquant l'export** | `ECART_MONTANT`, `MANQUANT_OM`, `MANQUANT_JOURNAL`, `A_CONTROLER` |
| **Version Python** | **3.14** — validée en pratique : Streamlit 1.63, Pandas 3.0.5, OpenPyXL 3.1.5, RapidFuzz 3.14.6, Pydantic 2.13.5, Loguru 0.7.3, Pytest 9.1.1 s'installent et s'importent |
| **Format d'import Sage** | **PNM**, relevé sur quatre fichiers réels et couvert par 15 tests |
| **Résidu du rapprochement** | Les encaissements OM de la journée sans écriture correspondante deviennent la **recette du jour** (`RECETTE_JOUR`), pas des manquants |

Ces choix sont posés dans [`config/matching_config.py`](config/matching_config.py)
(`BLOCKING_STATUSES`), [`config/sage_config.py`](config/sage_config.py) (`PNM_LAYOUT`) et
[`config/settings.py`](config/settings.py) (`ENCAISSEMENTS_*`).

> **Arbitrage du 16/09/2026 — passage au Journal des Encaissements.** Le journal des encaissements
> recense l'intégralité des règlements perçus sur tous les points de vente de l'hôtel (chambres,
> restaurant Kotibé, restaurant Baleng), avec une colonne dédiée à Orange Money.
> Sur la journée test réelle du 16/04/2026, la confrontation donne un **rapprochement parfait à 100 %** :
> 3 arrhes (290 600 FCFA) + 4 factures directes (18 000 FCFA) = 308 600 FCFA, égalant exactement
> les 308 600 FCFA du relevé Orange Money (dont une combinaison automatique niveau 5 de 10 500 FCFA
> pour 2 factures Kotibé réglées en un seul flux OM). 0 manquant, 0 écart.

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

### Le journal porte la période, le relevé est filtré dessus

Le journal des arrhes s'exporte **par journée**. La période de contrôle se lit donc dans le
journal — cellule `C1`, `Période du 16/04/2026 au 16/04/2026` — et le relevé mensuel est
restreint à cette même journée avant tout rapprochement. Un même relevé sert ainsi plusieurs
contrôles successifs, un par journée déposée.

Trois conséquences :

- **P2** ne demande pas la période à l'utilisateur, il la lit dans le journal et filtre le
  relevé dessus ;
- **P3** travaille sur une intersection d'une journée, ce qui borne l'ambiguïté d'appariement
  et interdit tout appariement croisé entre dates ;
- **P4** ne déclare `MANQUANT_JOURNAL` que pour les transactions OM **de la journée contrôlée** :
  hors de cette journée, une transaction n'est ni manquante ni anormale, elle est hors périmètre.
  Le cumul mensuel du §9 s'obtient en agrégeant les journées contrôlées.

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
| B10 | **Longueur du libellé** | P8 | Le PNM relevé donne 25 caractères ; les écritures du client atteignent **exactement 35 sans jamais les dépasser**, ce qui plaide pour un champ de 35 sur cette installation. Un libellé de 35 tronqué à 25 perdrait la date. |
| B13 | **Gabarit des libellés** | P8 | Les libellés du grand livre sont saisis à la main et dérivent selon les mois (`SVT JRNAL DE CAISSE MOMO`, `SVT JNAL MOMO DU`, `SVT JOURNAL DU`…). Défaut appliqué : la convention d'avril. À confirmer. |
| B11 | **Décimales en XAF** | P8 | Les échantillons sont en EUR à 2 décimales forcées. Sage attend-il `90200.00` ou `90200` en franc CFA ? |

B7 à B11 et B13 se posent tous au moment d'écrire le mapper : une seule séance avec le
comptable les tranche. Aucun d'eux ne bloque les phases P1 à P7.

> **Levé le 15/09/2026 — le journal se tire par journée.** Le plan supposait qu'il fallait un
> export du journal sur un mois complet. C'est faux : une journée déposée définit le périmètre
> du contrôle, et le relevé mensuel est filtré sur cette journée. Ce n'est pas un manque de
> données, c'est le mode de travail normal.

---

## Phase 0 — Socle technique & cadrage

**Objectif :** rendre le dépôt exécutable et aligner les ébauches sur le cahier des charges.

- ✅ `venv` Python 3.14.4, dépendances installées et vérifiées.
- ✅ Les 9 statuts métier et `BLOCKING_STATUSES` dans `config/matching_config.py`.
- ✅ Journal, compte et table `PNM_LAYOUT` dans `config/sage_config.py`.
- ✅ `config/settings.py` : chargement effectif du `.env` et correspondance des colonnes par alias.
- ⏳ `src/utils/logger.py` : loguru, **jamais de numéro de téléphone ni de montant client en clair**.
- ⏳ Figer les versions majeures dans `requirements.txt` — Pandas 3.0 change le comportement par défaut.
- ✅ Jeux de données **anonymisés** dans `tests/fixtures/`, régénérables par script.

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

**Objectif :** transformer deux classeurs hétérogènes en deux tables canoniques normalisées,
restreintes à la journée contrôlée.

- **Journal** : la table démarre en ligne 2 ; écarter sous-totaux, note de bas de page,
  pagination et bloc « Récapitulatif ». **Lire la période dans la cellule `C1` — elle fait foi**
  et définit le périmètre du contrôle. **Filtrer sur la colonne « Encaissement » = `Orange Money`.**
- **Filtrage du relevé sur la période du journal**, avant tout rapprochement.
- **Relevé** : découper les sous-relevés par compte, détecter les lignes de données par leur
  **forme** (colonne A entière, statut ∈ {Succès, Echec}), écarter soldes et totaux.
  Retenir `Merchant Payment`, écarter `C2C Transfer`, isoler les lignes de commission.
  `Statut = Echec` → `STATUT_OM_INVALIDE`.
- **Colonnes par alias**, pas en dur : ce relevé est un export daté, sa mise en forme bougera.
- Rapport d'import : lignes lues, écartées, motif de chaque rejet.

**Livrée.** Sur les fichiers réels : période lue au 16/04/2026, 3 lignes Orange Money
totalisant 290 600, 4 sous-relevés reconnus, 171 transactions et 6 lignes de commission
séparées, 6 encaissements clients sur la journée contrôlée. Les 15 lignes écartées du journal
portent chacune leur motif — sous-total, ligne de total, note de bas de page, pagination,
bloc Récapitulatif.

Les tests s'appuient sur des classeurs d'exemple anonymisés qui reproduisent tous les pièges
structurels ; un test supplémentaire s'exécute sur les fichiers réels lorsqu'ils sont présents
localement, et se saute sinon.

---

## Phase 3 — Moteur de rapprochement

**Objectif :** le cœur de l'application, recentré sur ce que les sources permettent réellement.

- Rapprochement **sur la journée portée par le journal**, le relevé étant déjà filtré par P2.
- Cascade sur le **reliquat**, avec **consommation** des lignes appariées — démontré nécessaire
  par le cas du 16/04 (deux fois 90 200 des deux côtés).
- Priorité aux **niveaux 2 et 4** (`date + montant`, puis tolérance). Tolérance de dates
  **étroite** : le même montant réapparaît à plusieurs dates du mois.
- Niveaux 1 et 3 implémentés pour les sources futures, non optimisés.
- `group_match.py` (niveau 5) : borner le nombre de lignes (`max_group_size`) et la fenêtre.
- Détection des doublons des deux côtés.
- **Traçabilité** : chaque appariement porte son niveau et son score.

**Définition de terminé :** la journée du 16/04/2026 est rapprochée 3 sur 3, chaque appariement
justifié par une règle nommée.

---

## Phase 4 — Analyse, statuts & observations

- Table unifiée, une ligne par opération, colonnes du §9.
- Affectation des statuts ; `BLOCKING_STATUSES` détermine ce qui remontera en P7.
- **Classement du résidu en `RECETTE_JOUR`** : les encaissements OM de la journée sans arrhe
  correspondante sont la recette ordinaire, pas des manquants. Le contrôleur peut requalifier
  une ligne en `MANQUANT_JOURNAL` s'il juge qu'elle aurait dû faire l'objet d'une arrhe.
- **Invariant de la journée**, à vérifier et à afficher :
  `total encaissements OM du jour = arrhes rapprochées + recette du jour + écarts non résolus`.
  Sur le 16/04 : 290 600 + 18 000 = 308 600.
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

- `mapper.py` : transactions validées → lignes comptables, **deux natures d'écriture** relevées
  dans le grand livre client :
  - une ligne `AVCE <NOM CLIENT> <date>` **par arrhe** rapprochée et validée ;
  - une ligne `SVT JNAL MOMO DU <date>` **par journée**, agrégeant le résidu.

  Contrôle d'**équilibre bloquant** par pièce et sur le lot.
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
