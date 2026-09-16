# Analyse des sources réelles

Fichiers analysés le 15/09/2026, copiés dans `data/input/` (**exclu de git** — données client).

| Fichier | Nature réelle |
|---|---|
| `004 RELEVE OM AVRIL 2026.xlsx` | Relevé Orange Money, avril 2026 — **4 sous-relevés concaténés** |
| `Journal des arrhes.xlsx` | Export du journal des arrhes — **une journée**, le 16/04/2026 |
| `OM SAGE.xlsx` | **Pas un modèle d'import.** Grand livre Sage 100c d'un compte |

---

## 1. Journal des arrhes

Feuille unique `A`, 25 lignes.

```text
ligne 1      bloc d'en-tête (société, période) dans la seule cellule C1
ligne 2      en-têtes de colonnes          ← la table commence ici, pas en ligne 1
lignes 3-10  détail des encaissements      ← 8 lignes, dont 3 en Orange Money
lignes 11-13 sous-totaux                   ← à écarter
lignes 14-15 note de bas de page, pagination ← à écarter
lignes 16-25 bloc « Récapitulatif »        ← à écarter
```

La période se lit dans `C1` : `Période du 16/04/2026 au 16/04/2026`.

| Col. | En-tête | Contenu réel |
|---|---|---|
| A | Date | **Sérial Excel avec heure** : `46128.552777777775` → 16/04/2026 13:16 |
| B | Compte / Réservation | Multi-ligne : nom du client + `Réservation N°8207 17/04/26` |
| C | Réintégration | `Facture N°TH-7206  90 200 FCFA 19/04/2026` — montant avec **espace insécable** |
| D | Encaissement | **Mode de paiement** — `Orange Money`, `Espèces`, `Virement Bancaire`, `CB Visa` |
| E | Montant Encaissé | entier |
| F | Montant Réintégré | entier |
| G | Solde non réintégré | entier |
| H | Réservation | vide sur cet export |

**La colonne D est le filtre de périmètre** : seules les lignes `Orange Money` concernent le
rapprochement. Sur cet export : 3 lignes, 90 200 + 110 200 + 90 200 = 290 600, ce que confirme
la ligne `Orange Money` du récapitulatif.

### Le journal porte la période de contrôle

Le journal des arrhes **se tire par journée**. Une journée déposée définit donc le périmètre du
contrôle : le relevé mensuel est **filtré sur cette même journée**, et le rapprochement ne
travaille que sur cette intersection.

```text
Journal du 16/04/2026  ──► période = 16/04/2026
                                │
Relevé d'avril 2026 ────────────┴──► filtré sur le 16/04/2026 ──► rapprochement
```

La période se lit dans la cellule `C1` (`Période du 16/04/2026 au 16/04/2026`) : c'est elle qui
fait foi, pas une saisie de l'utilisateur. Le relevé mensuel sert donc plusieurs contrôles
successifs, un par journée déposée, et le cumul mensuel s'obtient en agrégeant les journées
contrôlées.

Conséquences :

- l'ambiguïté d'appariement reste **confinée à une journée**, ce qui borne naturellement le
  coût du rapprochement et le risque d'appariement croisé entre dates ;
- une transaction OM de la journée absente du journal est un `MANQUANT_JOURNAL` **réel**, et
  non un artefact de périmètre ;
- les transactions OM hors de la journée contrôlée sont **hors périmètre**, ni manquantes ni
  anormales.

---

## 2. Relevé Orange Money

Feuille `Channel User Transaction Report`, 248 lignes utiles, **177 transactions** numérotées
de 1 à 177 en colonne A.

### Le fichier contient quatre sous-relevés

| Compte OM | Intitulé | Rôle |
|---|---|---|
| `698186110` | AGREGATEUR INTERNE OM | Compte pivot — alimente les points de vente |
| `656009773` | RELAIS DJELEN — RECEPTION | 101 transactions |
| `691829711` | HOTEL ZINGANA SA — KOTIBE | 58 transactions |
| `696948928` | HOTEL ZINGANA SA — RESTAURANT BALENG | 9 transactions |

Chaque sous-relevé répète tout le préambule, puis enchaîne des blocs
`Transactions échouées` / `Transactions réussies`, chacun encadré par une ligne de solde
initial et une ligne `Total activités` + `Solde final`.

> Le quatrième sous-relevé est intitulé `RELEVE MAI 2026` alors qu'il figure dans le fichier
> d'avril. Incohérence de libellé côté Orange : sans effet sur les dates des transactions,
> qui sont bien en avril.

### Colonnes des lignes de transaction — stables sur les quatre sous-relevés

| Col. | Champ | Exemple |
|---|---|---|
| A | N° | `65` |
| B | Date | `16/04/2026` (texte) |
| C | Heure | `13:11:20` |
| D | **Référence** | `MP260416.1311.A17517` |
| E | Service | `Merchant Payment`, `C2C Transfer`, `  Commissions` |
| F | Paiement | `Transaction` |
| G | **Statut** | `Succès` / `Echec` |
| H | Mode | `USSD` |
| I | Agent — n° de compte | `656009773` |
| J | Agent — wallet | `Normal` |
| K | N° pseudo | vide |
| L | **Correspondant** — n° de compte | `694697652` (téléphone du client) |
| M | Correspondant — wallet | `Normal` |
| N | Débit | sortie |
| O | **Crédit** | **entrée = encaissement client** |
| P | Commissions compte | `0` |
| Q | Sous-réseau | `-902` — commission prélevée, ~1 % |

**Les lignes d'en-tête sont inexploitables** : les cellules fusionnées y décalent les libellés
du préambule dans des colonnes arbitraires (`A='Agent'`, `L='Généré le :'`…). La détection des
lignes de données doit s'ancrer sur la **forme** — colonne A entière, colonne G ∈ {Succès, Echec} —
et non sur le texte des en-têtes.

### Règles de périmètre

| Filtre | Effet |
|---|---|
| `Service = Merchant Payment` | 160 lignes — **paiements clients**, seul périmètre du rapprochement |
| `Service = C2C Transfer` | 11 lignes — virements internes entre comptes du groupe, **hors périmètre** |
| `Service = Commissions` | 6 lignes — alimentent le compte de commissions, pas le rapprochement |
| `Statut = Echec` | 8 lignes → `STATUT_OM_INVALIDE` |
| Colonne O renseignée | encaissement ; colonne N = décaissement |

---

## 3. Confrontation des deux sources — ce que le test réel démontre

Journal du 16/04/2026, lignes Orange Money, face au relevé filtré sur le même jour :

| Journal (heure de saisie) | Montant | Relevé OM (heure réelle) | Référence OM | Écart de temps |
|---|---:|---|---|---|
| 13:16 | 90 200 | 13:11:20 | `MP260416.1311.A17517` | 5 min |
| 13:41 | 110 200 | 13:39:10 | `MP260416.1339.B43686` | 2 min |
| 16:30 | 90 200 | 15:23:58 | `MP260416.1523.A41832` | **1 h 07** |

Quatre conséquences pour le moteur de rapprochement :

1. **Le niveau 1 « référence exacte » est inutilisable.** Le journal ne contient aucune
   référence OM : sa colonne C porte un numéro de facture (`TH-7206`), sa colonne B un numéro
   de réservation. Aucun `MP2604…` nulle part. La cascade démarre en pratique au niveau 2.
2. **Le niveau 3 « client/correspondant » est inutilisable** de la même façon : le relevé
   identifie le client par son numéro de téléphone, le journal par son nom. Aucun champ commun.
   Le rapprochement flou sur les noms n'a rien sur quoi s'appuyer.
3. **L'heure n'est pas un critère.** Le journal horodate la saisie de l'arrhe, pas le paiement.
   L'écart va jusqu'à plus d'une heure.
4. **Le rapprochement repose donc sur `date + montant` + consommation.** Et ce cas réel le
   prouve nécessaire : le 16/04 comporte **deux encaissements de 90 200** côté relevé et
   **deux lignes de 90 200** côté journal. Aucune règle ne peut les distinguer — seule la règle
   « une ligne OM appariée est consommée » garantit un appariement 1-1 correct.

Le même montant réapparaît d'ailleurs à d'autres dates du mois — 110 200 les 11, 12 et 24 avril,
90 200 le 14 — ce qui confirme que **le montant seul ne discrimine pas** : la date est
indispensable, et la tolérance de dates doit rester étroite.

---

## 4. OM SAGE.xlsx — ce que le fichier est réellement

Feuille `Justificatif de solde général` : c'est un **grand livre exporté par Sage 100c
Comptabilité Premium**, pas un gabarit d'import. Il porte le compte `55300000`
« TRANSFERT VIA MTN MOMO2 », journal `MOMO`, arrêté au 46279 (13/09/2026), 114 lignes,
totaux débit 19 235 504 / crédit 29 955 622.

Il reste précieux : il montre **la forme exacte des écritures cibles**.

| Col. | Champ | Exemple |
|---|---|---|
| A | Date | sérial Excel — `46121` = 09/04/2026 |
| B | C.j — code journal | `MOMO` |
| C | N° pièce | `6479` |
| H | Libellé écriture | `AVCE VOUKING ZAMBOUS 09/04/2026` |
| M | Débit | `90200` |
| P | Crédit | `6082654` |
| R | Solde progressif | — |

Deux natures d'écriture cohabitent :

- **Recette agrégée du jour** — `SVT JNAL MOMO DU 06/04/2026`, une ligne par journée ;
- **Arrhes individuelles** — `AVCE <NOM CLIENT> <date>`, une ligne par encaissement.

C'est la seconde forme que l'export doit produire : les arrhes rapprochées et validées
deviennent une ligne `AVCE …` au débit du compte de transfert, journal `MOMO`.

### Questions ouvertes que ce fichier soulève

| # | Question |
|---|---|
| 1 | Le compte s'appelle « TRANSFERT VIA MTN **MOMO2** » et le journal est `MOMO`. **Existe-t-il un compte et un journal distincts pour Orange Money**, ou les deux opérateurs partagent-ils ce compte ? |
| 2 | Quelle est **la contrepartie** ? Le grand livre ne montre qu'un côté de l'écriture. |
| 3 | **Comment est attribué le n° de pièce** (6417, 6419, 6445…) ? Compteur Sage ou saisie manuelle ? L'export doit-il le fournir ou le laisser vide ? |
| 4 | Les libellés font jusqu'à **35 caractères**, au-delà des 25 relevés dans le format PNM (voir [`format_pnm.md`](format_pnm.md), §4). |
| 5 | Les libellés existants sont irréguliers : `SVT JOURNAL DU`, `SVT RECETTE MOMO DU`, `SVT JNAL MOMO DU`, `SVT JNAL RECETTE DU`, et un `10/04/*2026` avec une astérisque parasite. **Quel gabarit retenir** pour les écritures générées ? |
