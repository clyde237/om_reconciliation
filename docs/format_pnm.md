# Format PNM Sage 100 — spécification relevée

Source : quatre fichiers `.pnm` réels fournis le 15/09/2026, copiés dans
[`data/templates/pnm_samples/`](../data/templates/pnm_samples/).

> Cette spécification est **relevée par rétro-ingénierie**, pas issue d'une documentation Sage.
> Les champs marqués « à confirmer » n'apparaissent qu'avec une seule valeur dans les échantillons :
> leur signification est déduite, pas prouvée. Validation finale = import effectif dans Sage 100.

## 1. Enveloppe du fichier

| Propriété | Valeur relevée |
|---|---|
| Encodage | **ASCII strict** — aucun octet > 127 dans les quatre fichiers |
| Fin de ligne | **CRLF** (`\r\n`), y compris après la dernière ligne |
| Ligne 1 | En-tête : raison sociale cadrée à gauche sur **30 caractères** |
| Lignes 2..n | Écritures, **199 caractères fixes**, complétées par des espaces |

Conséquence directe : **les accents doivent être supprimés**. Les échantillons écrivent
`Achats matieres 19,6 %` et non `Achats matières`.

## 2. Découpage des 199 caractères

Positions en base 0, bornes incluses.

| Début | Lg | Champ | Cadrage | Valeurs relevées |
|---:|---:|---|---|---|
| 0 | 3 | Code journal | gauche | `ACH` |
| 3 | 6 | Date de la pièce `JJMMAA` | — | `110103` |
| 9 | 1 | Indicateur 1 *(à confirmer)* | — | `F` constant |
| 10 | 1 | Indicateur 2 *(à confirmer)* | — | `F` constant |
| 11 | 13 | Compte général | gauche | `601000`, `601019`, `4456619`, `4010000` |
| 24 | 1 | Type de la ligne complémentaire *(déduit)* | — | `X` tiers · `E` échéance · `A` section analytique · vide |
| 25 | 13 | Code tiers ou section analytique | gauche | `SAPHIRA`, `BILLO`, `JASER`, `922LY3`, `9301AR` |
| 38 | 13 | N° de pièce | gauche | `FA1234`, `FA1236`, `FA12346` |
| 51 | 25 | **Libellé écriture** | gauche | `TVA deductible B/S 19,6 %` (exactement 25 car.) |
| 76 | 1 | Indicateur d'échéance | — | `L` ou vide |
| 77 | 6 | Date d'échéance `JJMMAA` | — | `120303`, `150203` |
| 83 | 1 | **Sens** | — | `D` ou `C` |
| 84 | 20 | **Montant** — 2 décimales, séparateur `.` | droite, fin en pos. 103 | `1196.00`, `19.60` |
| 104 | 1 | Indicateur de lettrage *(à confirmer)* | — | `N` constant |
| 109 | 3 | N° d'écriture | gauche | `574`, `729`, `731` |
| 138 | 3 | Devise de tenue | gauche | `EUR` |
| 154 | 7 | Montant en devise | droite | `1219.92`, `120.00` |
| 161 | 3 | Code devise | gauche | `USD` |
| 164 | 1 | N° d'axe analytique | — | `1`, `2` |
| 165 | 34 | Réservé | — | espaces |

Les intervalles non listés (18–23, 32–37, 44–50, 105–108, 112–137, 141–153) sont vides
dans les quatre échantillons.

## 3. Regroupement des lignes

Le champ **N° d'écriture** (pos. 109) identifie la ligne comptable. Une ligne et ses lignes
complémentaires — ventilations analytiques `A`, échéances supplémentaires `E` — **partagent le
même numéro**. Vérifié sur les quatre fichiers :

```text
ecritures sage.pnm
  729  601019  D 1000.00        ← ligne mère
  729  601019  A922LY3   550.00 ← ventilation analytique, axe 1
  729  601019  A922ME3   450.00 ← ventilation analytique, axe 1
  729  601019  A9301AR   600.00 ← ventilation analytique, axe 2
  730  4456619 D  196.00        ← TVA
  731  4010000 XSAPHIRA C 1196.00 ← contrepartie tiers
  731  4010000 ESAPHIRA C  598.00 ← échéance 1
  731  4010000 ESAPHIRA C  598.00 ← échéance 2
```

Le numéro s'incrémente par ligne comptable et non par pièce : les trois lignes de `FA1236`
portent 729, 730, 731.

## 4. Points à valider avant d'écrire l'exportateur

| # | Question | Pourquoi ça compte |
|---|---|---|
| 1 | **Longueur réelle du libellé** | Les échantillons donnent 25 caractères. Or le grand livre du client contient des libellés qui atteignent **exactement 35 caractères sans jamais les dépasser** — `AVCE NJINI BERLINDA MUNGHI 04/04/26`, `SVT JNAL MOMO 03/04/26 RECU LE16/04`. Cette borne nette plaide pour un champ de 35 sur cette installation, les échantillons provenant d'une version plus ancienne. À trancher avant l'export : un libellé de 35 tronqué à 25 perdrait la date. |
| 2 | **Décimales en XAF** | Les échantillons sont en EUR avec 2 décimales forcées. Le franc CFA n'a pas de sous-unité : reste à savoir si Sage attend `90200.00` ou `90200`. |
| 3 | **Largeur exacte du champ montant** | Tous les montants des échantillons sont inférieurs à 10 000. La borne gauche du champ (84 ?) n'est pas démontrée. Les arrhes OM vont jusqu'à 6 000 000 : à tester. |
| 4 | **Indicateurs `F`, `F`, `N`** | Constants sur les quatre fichiers, donc leur sémantique reste inconnue. À reprendre tels quels par défaut. |
| 5 | **Zone devise** | À laisser vide si la comptabilité est tenue en XAF sans devise secondaire, ou à remplir avec `XAF`. |

## 5. Implications pour l'export

- L'exportateur doit être **piloté par une table de positions déclarative**, pas par des
  concaténations codées en dur — les points de la section 4 changeront des largeurs.
- Toute chaîne passe par une normalisation ASCII : suppression des accents, des caractères
  non imprimables et de l'espace insécable.
- Toute valeur trop longue pour son champ doit **échouer explicitement ou être tronquée de
  façon tracée**, jamais silencieusement.
- Un test compare octet à octet la sortie de l'exportateur aux quatre échantillons rejoués.
