# Règles et caractéristiques d'un bon code pour une application professionnelle

## Objectif

Ce document définit les règles qu'un code d'application professionnel doit respecter. Il est destiné à servir de référence pour un développeur humain ou une IA chargée de concevoir, générer, corriger, refactoriser, auditer ou maintenir une application.

L'objectif n'est pas uniquement de produire un code fonctionnel. Le code doit également être lisible, simple, modulaire, sécurisé, testable, maintenable, évolutif, performant, documenté, traçable et correctement versionné.

---

# 1. Lisibilité

Le code doit être compréhensible rapidement par un autre développeur.

## Règles

- Utiliser des noms de variables explicites.
- Utiliser des noms de fonctions explicites.
- Utiliser des noms de classes explicites.
- Éviter les abréviations incompréhensibles.
- Respecter une indentation cohérente.
- Respecter les conventions de nommage du langage utilisé.
- Éviter les fonctions inutilement longues.
- Éviter les blocs de code excessivement complexes.
- Écrire des commentaires uniquement lorsqu'ils apportent une véritable explication.
- Ne pas commenter ce que le code dit déjà clairement.
- Organiser les fichiers de manière logique.
- Garder une cohérence de style dans tout le projet.

## Exemple

### Mauvais

```python
x = u.prix * u.q
```

### Bon

```python
total_ligne = produit.prix * produit.quantite
```

Le deuxième exemple permet de comprendre immédiatement ce que représente chaque donnée.

---

# 2. Simplicité

Le code doit privilégier la solution la plus simple qui répond correctement au besoin.

## Règles

- Ne pas complexifier inutilement une fonctionnalité.
- Éviter les abstractions prématurées.
- Éviter les dépendances inutiles.
- Éviter les conditions imbriquées excessivement.
- Éviter les fonctions gigantesques.
- Éviter les architectures inutilement complexes.
- Ne pas utiliser un design pattern uniquement parce qu'il existe.
- Ne pas créer une classe lorsque quelques fonctions simples suffisent.
- Ne pas créer une abstraction avant d'avoir identifié un besoin réel.
- Préférer un code explicite à un code artificiellement compact.

## À éviter

```text
Une fonction de 500 lignes
Une logique métier dispersée dans 10 fichiers
Des conditions imbriquées sur 7 niveaux
Des dépendances inutiles
Une architecture complexe pour une petite fonctionnalité
```

## À privilégier

```text
Fonctions courtes
Responsabilités claires
Logique directe
Architecture compréhensible
Dépendances justifiées
```

Important :

> Simple ne signifie pas simpliste. Le code doit rester capable de gérer correctement les cas réels.

---

# 3. Modularité

L'application doit être divisée en composants et modules cohérents.

## Exemple

```text
app/
├── auth/
├── users/
├── products/
├── payments/
├── reports/
├── audit/
└── settings/
```

Chaque module doit avoir une responsabilité clairement définie.

## Règles

- Organiser le projet par domaine fonctionnel lorsque cela est pertinent.
- Éviter les fichiers contenant des responsabilités sans rapport.
- Limiter les dépendances entre modules.
- Éviter les dépendances circulaires.
- Concevoir des composants pouvant évoluer indépendamment.
- Garder les interfaces entre modules explicites.
- Ne pas mélanger inutilement les responsabilités.

Exemple :

Une modification du module `payments` ne devrait pas nécessiter une réécriture du module `products` si les deux domaines sont correctement séparés.

---

# 4. Séparation des responsabilités

Chaque partie du programme doit faire ce qu'elle est censée faire.

Une architecture typique peut suivre ce principe :

```text
Frontend
   ↓
API
   ↓
Services métier
   ↓
Repository / accès aux données
   ↓
Base de données
```

## Règles

- Le frontend ne doit pas contenir toute la logique métier.
- Les routes API ne doivent pas contenir toute la logique métier.
- L'accès à la base de données doit être séparé lorsque l'architecture le justifie.
- Les services doivent gérer les règles métier.
- Les validateurs doivent gérer la validation.
- Les composants UI doivent gérer l'affichage et les interactions UI.
- Les mécanismes d'authentification et d'autorisation doivent être clairement séparés.
- Les fonctions doivent avoir une responsabilité identifiable.

## À éviter

Mettre dans une seule fonction :

```text
SQL
+
calcul métier
+
validation
+
HTML
+
gestion des erreurs
+
authentification
```

Une telle fonction devient difficile à tester, maintenir et modifier.

---

# 5. Réutilisabilité

Éviter de copier-coller le même code.

## Mauvais

```python
total1 = prix1 * quantite1
total2 = prix2 * quantite2
total3 = prix3 * quantite3
```

## Bon

```python
def calculer_total(prix, quantite):
    return prix * quantite
```

Puis :

```python
calculer_total(prix1, quantite1)
calculer_total(prix2, quantite2)
calculer_total(prix3, quantite3)
```

## Règles

- Éviter la duplication inutile.
- Centraliser les règles métier communes.
- Créer des fonctions réutilisables lorsque cela améliore réellement la conception.
- Éviter de dupliquer les validations.
- Éviter de dupliquer les calculs.
- Éviter de dupliquer les requêtes complexes.
- Ne pas transformer chaque ligne répétée en abstraction artificielle.

La réutilisation doit améliorer le projet, pas le rendre plus complexe.

---

# 6. Robustesse

Le programme doit gérer les situations inattendues.

Le code ne doit pas supposer que toutes les opérations réussiront.

Il doit anticiper notamment :

```text
Utilisateur inexistant
Fichier absent
Base de données indisponible
Valeur vide
Valeur incorrecte
Type incorrect
Connexion interrompue
Données invalides
Doublon
Timeout
Réponse API invalide
Permission insuffisante
Ressource supprimée
Donnée partiellement disponible
```

## Règles

- Valider les entrées.
- Vérifier les résultats des opérations critiques.
- Gérer les exceptions pertinentes.
- Prévoir les erreurs réseau.
- Prévoir les erreurs de base de données.
- Prévoir les erreurs de fichiers.
- Prévoir les données manquantes.
- Ne jamais considérer qu'une opération externe réussira toujours.
- Retourner des erreurs compréhensibles.

---

# 7. Gestion des erreurs

Les erreurs doivent être contrôlées, correctement journalisées et compréhensibles.

## Mauvais

```python
try:
    ...
except:
    pass
```

Ce code masque les problèmes.

## Bon

```python
try:
    enregistrer_paiement()
except DatabaseError as error:
    logger.error(
        "Erreur lors de l'enregistrement du paiement : %s",
        error
    )
    raise
```

## Règles

- Ne pas utiliser `except` sans raison précise.
- Ne pas ignorer silencieusement une exception importante.
- Attraper les exceptions appropriées.
- Fournir des messages d'erreur utiles.
- Journaliser les erreurs importantes.
- Ne jamais exposer d'informations sensibles dans les erreurs retournées aux utilisateurs.
- Différencier les erreurs utilisateur des erreurs système.
- Utiliser les codes HTTP appropriés dans une API.
- Prévoir une stratégie de gestion des erreurs cohérente dans toute l'application.

---

# 8. Sécurité

La sécurité doit être intégrée dès la conception.

## Authentification

L'application doit notamment prévoir :

- une authentification correctement conçue ;
- des mots de passe hashés avec un algorithme adapté ;
- une gestion sécurisée des sessions ou tokens ;
- une gestion des expirations ;
- une protection contre les tentatives abusives lorsque nécessaire ;
- une procédure sécurisée de récupération de compte.

## Autorisation

Il faut distinguer :

```text
Qui est l'utilisateur ?
```

de :

```text
Qu'a-t-il le droit de faire ?
```

Le système doit gérer les rôles et permissions lorsque cela est nécessaire.

Exemple :

```text
Administrateur
Gestionnaire
Auditeur
Utilisateur
Lecture seule
```

## Protection des données

Le code doit notamment se protéger contre :

- SQL Injection ;
- XSS ;
- CSRF lorsque pertinent ;
- attaques par force brute ;
- exposition accidentelle de secrets ;
- accès non autorisés ;
- manipulation des paramètres ;
- upload de fichiers dangereux ;
- accès direct à des ressources protégées.

## Secrets

Ne jamais mettre directement dans le code :

```python
password = "123456"
api_key = "ma-cle-secrete"
secret_key = "secret"
```

Préférer les variables d'environnement ou un système sécurisé de gestion des secrets.

Exemple :

```text
DATABASE_URL
SECRET_KEY
API_KEY
SMTP_HOST
```

---

# 9. Validation des données

Toutes les données provenant d'une source externe doivent être considérées comme potentiellement invalides.

Sources concernées :

```text
Formulaires
API
URL
Paramètres
Fichiers
CSV
JSON
Base de données externe
Webhooks
Services tiers
```

## Règles

- Valider les types.
- Valider les formats.
- Valider les longueurs.
- Valider les plages de valeurs.
- Valider les champs obligatoires.
- Nettoyer les données lorsque nécessaire.
- Ne jamais faire confiance aux données reçues du frontend.
- Refaire les validations critiques côté backend.
- Retourner des erreurs de validation précises.

Important :

> Le frontend améliore l'expérience utilisateur, mais le backend doit rester la source de confiance pour les règles de sécurité et de validation.

---

# 10. Testabilité

Un bon code doit pouvoir être testé facilement.

## Structure possible

```text
tests/
├── test_auth.py
├── test_users.py
├── test_payments.py
├── test_products.py
└── test_reports.py
```

## Types de tests

Selon le projet :

- tests unitaires ;
- tests d'intégration ;
- tests API ;
- tests de validation ;
- tests de sécurité ;
- tests end-to-end ;
- tests de régression.

## Règles

- Tester les fonctionnalités critiques.
- Tester les cas normaux.
- Tester les cas limites.
- Tester les erreurs.
- Tester les permissions.
- Tester les règles métier.
- Éviter de rendre les tests dépendants inutilement les uns des autres.
- Garder les tests reproductibles.
- Exécuter automatiquement les tests dans le pipeline CI lorsque possible.

---

# 11. Performance

Le code doit utiliser raisonnablement :

```text
CPU
Mémoire
Réseau
Base de données
Stockage
```

## Règles

- Éviter les requêtes SQL inutiles.
- Éviter les appels réseau inutiles.
- Utiliser la pagination pour les grandes collections.
- Charger uniquement les données nécessaires.
- Utiliser des index de base de données lorsque nécessaire.
- Éviter les traitements répétitifs coûteux.
- Utiliser le cache lorsque cela est justifié.
- Mesurer les performances avant d'optimiser une partie non critique.

## Exemple de problème

```text
1000 requêtes SQL
```

alors qu'une requête correctement conçue pourrait suffire.

Important :

> Ne pas sacrifier la lisibilité pour une optimisation prématurée.

L'optimisation doit être guidée par des mesures et par les vrais goulots d'étranglement.

---

# 12. Maintenabilité

Le code doit pouvoir être repris et modifié facilement dans plusieurs mois ou plusieurs années.

## Règles

- Utiliser une architecture cohérente.
- Limiter les dépendances inutiles.
- Éviter le code spaghetti.
- Éviter les fonctions géantes.
- Éviter les variables globales inutiles.
- Centraliser les règles importantes.
- Garder les conventions cohérentes.
- Documenter les décisions architecturales importantes.
- Écrire des tests pour les fonctionnalités critiques.
- Ne pas créer de dette technique inutile.

Exemple de scénario :

```text
Aujourd'hui :
Gestion des utilisateurs
Paiements
Facturation
Rapports

Dans 2 ans :
Il faut modifier les mêmes fonctionnalités.
```

Un bon code doit permettre ces modifications sans devoir réécrire toute l'application.

---

# 13. Évolutivité

L'application doit pouvoir évoluer avec les besoins.

Exemple :

```text
Aujourd'hui :
10 utilisateurs
1 000 transactions

Demain :
500 utilisateurs
1 000 000 transactions
```

## Règles

- Concevoir une architecture permettant l'évolution.
- Éviter les choix qui bloquent inutilement la croissance.
- Séparer correctement les domaines métier.
- Prévoir l'évolution des données.
- Utiliser des migrations de base de données.
- Prévoir l'évolution des API.
- Éviter de coupler inutilement les composants.
- Prévoir les changements de configuration.

L'objectif n'est pas de construire dès le départ une architecture gigantesque, mais de ne pas créer volontairement des blocages futurs.

---

# 14. Documentation

Un projet professionnel doit expliquer son fonctionnement.

Le projet doit idéalement documenter :

```text
Installation
Configuration
Variables d'environnement
Lancement
Tests
Architecture
API
Base de données
Migrations
Déploiement
Maintenance
```

## README

Un `README.md` doit généralement expliquer :

```text
Nom du projet
Description
Prérequis
Installation
Configuration
Variables d'environnement
Lancement en développement
Lancement des tests
Construction pour production
Déploiement
Structure du projet
Documentation API
Informations importantes
```

## Documentation du code

Documenter particulièrement :

- les fonctions complexes ;
- les décisions architecturales ;
- les règles métier non évidentes ;
- les intégrations externes ;
- les formats de données ;
- les comportements particuliers.

Ne pas documenter inutilement chaque ligne évidente.

---

# 15. Cohérence

Le projet doit utiliser des conventions constantes.

## Mauvais

```text
get_user()
getProduct()
GetClient()
recuperer_paiement()
```

sans raison.

## Bon

Choisir une convention et la respecter.

Par exemple :

```text
get_user()
get_product()
get_client()
get_payment()
```

## Règles

- Utiliser une convention de nommage.
- Utiliser une convention de structure de fichiers.
- Utiliser une convention de formatage.
- Utiliser une convention de gestion des erreurs.
- Utiliser une convention pour les réponses API.
- Utiliser une convention pour les logs.
- Utiliser une convention pour les commits.
- Automatiser le formatage lorsque possible.

---

# 16. Gestion des logs

Une application professionnelle doit permettre de comprendre ce qui s'est passé.

Exemple :

```text
INFO  User 25 logged in
INFO  Payment #458 created
WARNING Payment #458 duplicated
ERROR Database connection failed
```

## Règles

- Utiliser plusieurs niveaux de logs lorsque pertinent.
- Ne pas enregistrer les mots de passe.
- Ne pas enregistrer inutilement les tokens ou secrets.
- Ne pas exposer des données personnelles sensibles sans nécessité.
- Ajouter un contexte utile aux erreurs.
- Inclure des identifiants techniques lorsque cela facilite le diagnostic.
- Utiliser des logs structurés pour les systèmes complexes lorsque pertinent.

Niveaux courants :

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

---

# 17. Traçabilité

Pour certaines applications, il est essentiel de savoir :

```text
Qui ?
A fait quoi ?
Quand ?
Sur quelle donnée ?
Quelle était l'ancienne valeur ?
Quelle est la nouvelle valeur ?
```

Exemple :

```text
Utilisateur : admin
Action      : Modification
Objet       : Paiement #458
Avant       : 150 000 FCFA
Après       : 175 000 FCFA
Date        : 17/09/2026 14:15
```

## Règles

Pour les opérations sensibles, enregistrer lorsque nécessaire :

- utilisateur ;
- action ;
- ressource concernée ;
- date et heure ;
- ancienne valeur ;
- nouvelle valeur ;
- résultat de l'opération ;
- contexte technique utile.

Cette fonctionnalité est particulièrement importante dans :

```text
Applications comptables
Applications financières
Applications d'audit
Applications RH
Applications administratives
Applications de gestion
Applications médicales
Applications avec données sensibles
```

---

# 18. Versionnement

Le code doit être géré avec un système de contrôle de version, généralement Git.

## Exemple

```text
main
│
├── develop
│
├── feature/authentication
├── feature/payments
└── fix/payment-duplicate
```

## Règles

- Faire des commits fréquents et cohérents.
- Éviter les commits contenant des changements sans rapport.
- Utiliser des messages de commit explicites.
- Utiliser des branches lorsque le workflow du projet le justifie.
- Éviter de travailler directement sur la branche principale pour toutes les modifications importantes.
- Ne jamais versionner les secrets.
- Utiliser `.gitignore`.
- Maintenir un historique compréhensible.

## Exemples de commits

```text
feat: add payment reconciliation
fix: prevent duplicate transactions
refactor: simplify audit service
docs: update installation guide
test: add payment validation tests
```

---

# 19. Configuration séparée du code

Les paramètres qui changent selon l'environnement ne doivent généralement pas être codés en dur.

Exemple :

```text
Développement
    ↓
.env

Production
    ↓
Variables d'environnement / gestionnaire de secrets
```

Paramètres possibles :

```text
DATABASE_URL
SECRET_KEY
API_KEY
SMTP_HOST
SMTP_PORT
APP_ENV
LOG_LEVEL
```

## Règles

- Séparer la configuration de la logique métier.
- Utiliser des variables d'environnement pour les secrets.
- Fournir un fichier d'exemple comme `.env.example`.
- Ne jamais versionner les vraies valeurs secrètes.
- Différencier les environnements de développement, test et production.

---

# 20. Dépendances maîtrisées

Chaque dépendance externe représente une charge supplémentaire.

Elle implique potentiellement :

```text
Maintenance
Sécurité
Compatibilité
Mises à jour
Taille
Performance
Risque de dépendance abandonnée
```

## Règles

- N'ajouter une dépendance que lorsqu'elle apporte une vraie valeur.
- Vérifier sa maintenance.
- Vérifier sa licence.
- Vérifier sa réputation et sa sécurité.
- Éviter les bibliothèques inutiles.
- Mettre régulièrement les dépendances à jour selon une stratégie maîtrisée.
- Tester l'application après les mises à jour importantes.
- Verrouiller les versions lorsque le projet l'exige.
- Supprimer les dépendances inutilisées.

Principe :

> Une dépendance doit être justifiée.

---

# 21. Principe DRY

DRY signifie :

```text
Don't Repeat Yourself
```

Le même concept métier ne doit pas être défini inutilement à plusieurs endroits.

## Mauvais

Une règle de calcul du montant d'une facture est copiée dans :

```text
frontend
route API
service
rapport
export Excel
```

avec des implémentations légèrement différentes.

Cela crée un risque d'incohérence.

## Bon

Centraliser la règle métier dans un endroit approprié et réutiliser cette logique.

Attention :

DRY ne signifie pas qu'il faut absolument fusionner deux morceaux de code simplement parce qu'ils se ressemblent visuellement.

---

# 22. Principe KISS

KISS signifie :

```text
Keep It Simple
```

## Règles

- Préférer une solution compréhensible.
- Éviter les abstractions inutiles.
- Éviter les architectures surdimensionnées.
- Éviter la magie excessive.
- Préférer la clarté.
- Préférer une solution explicite lorsqu'elle est plus facile à maintenir.

---

# 23. Principe SRP

SRP signifie :

```text
Single Responsibility Principle
```

Une classe ou un module doit avoir une responsabilité claire.

## Mauvais

Une classe `UserManager` qui :

```text
crée les utilisateurs
envoie les emails
génère les PDF
gère les paiements
fait les statistiques
gère les fichiers
```

## Bon

Séparer les responsabilités :

```text
UserService
EmailService
PdfService
PaymentService
ReportService
FileService
```

---

# 24. Principes SOLID

Lorsque le langage et l'architecture s'y prêtent, appliquer les principes SOLID.

## S — Single Responsibility Principle

Une classe doit avoir une responsabilité claire.

## O — Open/Closed Principle

Le code doit pouvoir être étendu sans nécessiter de modifications risquées dans du code existant.

## L — Liskov Substitution Principle

Les implémentations dérivées doivent pouvoir être utilisées conformément au contrat attendu par leur abstraction.

## I — Interface Segregation Principle

Préférer plusieurs interfaces spécifiques à une interface gigantesque.

## D — Dependency Inversion Principle

Les composants de haut niveau doivent dépendre d'abstractions appropriées plutôt que de détails concrets lorsque cela apporte une vraie valeur.

Important :

SOLID ne doit pas devenir une excuse pour sur-architecturer une petite application.

---

# 25. Gestion de la base de données

La base de données doit être traitée comme une partie essentielle de l'application.

## Règles

- Définir clairement les modèles de données.
- Utiliser des contraintes appropriées.
- Utiliser des clés primaires.
- Utiliser des clés étrangères lorsque nécessaire.
- Éviter les duplications inutiles.
- Utiliser des index lorsque nécessaire.
- Prévoir les migrations.
- Utiliser des transactions pour les opérations qui doivent être atomiques.
- Valider les données.
- Prévoir les sauvegardes dans les environnements appropriés.
- Éviter les requêtes inutiles.
- Ne jamais construire des requêtes SQL dangereuses à partir de chaînes utilisateur non contrôlées.

---

# 26. Transactions et intégrité des données

Lorsqu'une opération implique plusieurs modifications qui doivent réussir ou échouer ensemble, utiliser une transaction appropriée.

Exemple :

```text
Création d'une facture
+
Création des lignes de facture
+
Mise à jour du stock
+
Enregistrement du paiement
```

Si une étape critique échoue, l'application doit éviter de laisser les données dans un état incohérent lorsque l'opération doit être atomique.

---

# 27. API propres et cohérentes

Pour une application utilisant une API, les endpoints doivent être cohérents.

Exemple :

```text
GET    /api/users
GET    /api/users/25
POST   /api/users
PUT    /api/users/25
DELETE /api/users/25
```

## Règles

- Utiliser des méthodes HTTP cohérentes.
- Utiliser des codes HTTP appropriés.
- Valider les entrées.
- Documenter les endpoints.
- Définir des formats de réponse cohérents.
- Définir une stratégie de gestion des erreurs.
- Contrôler les permissions.
- Versionner l'API lorsque nécessaire.
- Ne pas exposer des informations internes inutiles.

---

# 28. Frontend

Le frontend doit être structuré et ne doit pas devenir un ensemble de composants impossibles à maintenir.

## Règles

- Réutiliser les composants.
- Éviter les composants gigantesques.
- Séparer les composants de présentation et la logique lorsque pertinent.
- Centraliser les appels API lorsque cela améliore la cohérence.
- Gérer correctement les états de chargement.
- Gérer les erreurs.
- Gérer les états vides.
- Gérer les états de succès.
- Valider les formulaires côté frontend pour l'expérience utilisateur.
- Toujours refaire les contrôles de sécurité côté backend.
- Éviter les appels API inutiles.
- Gérer correctement les permissions dans l'interface sans considérer le frontend comme une barrière de sécurité.

---

# 29. UX et états d'interface

Une application professionnelle doit prévoir les différents états d'une interface.

Pour une page de données :

```text
Chargement
↓
Succès avec données
↓
Succès sans données
↓
Erreur
```

Il faut également prévoir :

```text
Bouton désactivé pendant une opération
Message de confirmation
Message d'erreur
Validation du formulaire
État vide
Pagination
Recherche
Filtrage
```

---

# 30. Accessibilité

Lorsque l'application possède une interface utilisateur, elle doit être accessible autant que possible.

## Règles

- Utiliser une structure HTML sémantique.
- Utiliser des labels pour les champs.
- Assurer une navigation au clavier.
- Fournir des textes alternatifs pertinents aux images.
- Maintenir une lisibilité suffisante.
- Ne pas transmettre une information uniquement par la couleur.
- Utiliser des contrôles accessibles.
- Gérer correctement le focus.
- Fournir des messages d'erreur compréhensibles.

---

# 31. Gestion des fichiers

Si l'application permet d'importer des fichiers :

## Règles

- Vérifier le type réel du fichier lorsque nécessaire.
- Vérifier la taille.
- Limiter les extensions autorisées.
- Renommer les fichiers de manière sûre.
- Ne pas faire confiance au nom fourni par l'utilisateur.
- Ne pas exécuter les fichiers uploadés.
- Stocker les fichiers dans un emplacement approprié.
- Contrôler l'accès aux fichiers.
- Prévoir les fichiers manquants.
- Journaliser les opérations sensibles.

---

# 32. Traitement des données sensibles

Les données sensibles doivent être traitées avec précaution.

## Règles

- Collecter uniquement les données nécessaires.
- Limiter l'accès.
- Éviter de les afficher inutilement dans les logs.
- Chiffrer les données lorsque nécessaire.
- Utiliser HTTPS pour les communications réseau.
- Ne pas exposer les secrets dans les réponses API.
- Contrôler les exports.
- Contrôler les téléchargements.
- Appliquer le principe du moindre privilège.

---

# 33. Principe du moindre privilège

Chaque utilisateur, service ou composant doit avoir uniquement les permissions nécessaires à son rôle.

Exemple :

```text
Utilisateur :
lecture de ses données

Gestionnaire :
lecture + modification

Auditeur :
lecture + consultation des historiques

Administrateur :
gestion complète
```

Ne pas donner systématiquement des permissions administrateur.

---

# 34. Gestion des environnements

Un projet professionnel doit distinguer autant que nécessaire :

```text
Development
Testing
Staging
Production
```

## Règles

- Ne pas utiliser les données de production pour tester sans précautions.
- Séparer les secrets.
- Séparer les bases de données.
- Adapter la configuration à chaque environnement.
- Tester les déploiements avant production.
- Prévoir une procédure de rollback lorsque nécessaire.

---

# 35. CI/CD

Lorsque le projet le justifie, automatiser les contrôles.

Pipeline possible :

```text
Push Git
   ↓
Lint
   ↓
Type checking
   ↓
Tests
   ↓
Build
   ↓
Security checks
   ↓
Deploy
```

## Règles

- Ne pas déployer du code non testé lorsque les tests automatisés sont disponibles.
- Exécuter le lint.
- Exécuter les tests.
- Vérifier le build.
- Contrôler les erreurs.
- Déployer automatiquement uniquement selon une stratégie maîtrisée.

---

# 36. Linting et formatage

Utiliser les outils adaptés au langage.

Objectifs :

```text
Style cohérent
Erreurs détectées tôt
Code uniforme
Maintenance facilitée
```

## Règles

- Utiliser un formateur automatique lorsque disponible.
- Utiliser un linter.
- Configurer les règles au niveau du projet.
- Éviter les débats de style inutiles.
- Faire respecter automatiquement les conventions lorsque possible.

---

# 37. Typage

Lorsque le langage le permet, utiliser un typage suffisamment explicite.

Exemple Python :

```python
def calculer_total(prix: float, quantite: int) -> float:
    return prix * quantite
```

Le typage permet :

- une meilleure compréhension ;
- une meilleure autocomplétion ;
- une détection plus précoce des erreurs ;
- une maintenance facilitée.

Pour TypeScript, éviter de désactiver inutilement le système de types avec des `any` partout.

---

# 38. Gestion des dates et heures

Les dates et heures sont une source fréquente d'erreurs.

## Règles

- Définir clairement les fuseaux horaires.
- Utiliser un format standard pour le stockage.
- Éviter les conversions implicites.
- Distinguer date et date-heure.
- Tester les changements de jour.
- Tester les changements de mois et d'année.
- Tester les différences de fuseaux horaires lorsque l'application est internationale.
- Afficher les dates selon les besoins de l'utilisateur.

---

# 39. Gestion de l'argent

Pour les applications financières, comptables, commerciales ou de paiement :

## Règles

- Éviter les calculs monétaires naïfs avec des nombres flottants lorsque cela peut produire des erreurs d'arrondi.
- Utiliser une représentation monétaire appropriée.
- Définir clairement la devise.
- Définir les règles d'arrondi.
- Conserver une précision suffisante.
- Tester les cas d'arrondi.
- Journaliser les modifications importantes.
- Ne jamais modifier silencieusement une transaction financière.
- Utiliser des transactions de base de données lorsque nécessaire.
- Prévoir les mécanismes de rapprochement et de traçabilité lorsque le domaine l'exige.

---

# 40. Idempotence

Certaines opérations doivent pouvoir être répétées sans créer plusieurs fois le même résultat.

Exemple :

```text
Un webhook de paiement est envoyé deux fois.
```

L'application ne doit pas créer deux paiements si les deux événements correspondent à la même transaction.

## Règles

- Identifier les opérations qui doivent être idempotentes.
- Utiliser des identifiants uniques d'opération lorsque nécessaire.
- Ajouter des contraintes uniques dans la base de données lorsque pertinent.
- Vérifier les doublons.
- Ne pas dépendre uniquement d'une vérification côté frontend.

---

# 41. Concurrence

Plusieurs utilisateurs peuvent modifier une donnée en même temps.

Le code doit prévoir les problèmes possibles :

```text
Modification simultanée
Double validation
Double paiement
Double réservation
Conflit de mise à jour
Lecture de données obsolètes
```

## Règles

- Utiliser des transactions lorsque nécessaire.
- Utiliser des contraintes en base.
- Prévoir des stratégies de verrouillage lorsque nécessaire.
- Vérifier les conditions au moment de l'écriture.
- Ne pas considérer qu'un utilisateur est toujours seul sur une donnée.

---

# 42. Cache

Le cache doit être utilisé lorsque cela est pertinent.

## Règles

- Ne pas mettre en cache toutes les données sans raison.
- Définir la durée de validité.
- Prévoir l'invalidation.
- Éviter de servir des données sensibles à un mauvais utilisateur.
- Mesurer le bénéfice du cache.

Un mauvais système de cache peut produire des données obsolètes ou incorrectes.

---

# 43. Dépendances externes et services tiers

Lorsqu'une application utilise :

```text
API externe
Paiement
Email
SMS
Stockage cloud
Cartographie
Authentification externe
```

il faut prévoir les pannes de ces services.

## Règles

- Gérer les timeouts.
- Gérer les erreurs.
- Prévoir les réponses invalides.
- Prévoir les limitations de débit.
- Ne pas supposer qu'un service externe sera toujours disponible.
- Journaliser les erreurs utiles.
- Prévoir une stratégie de reprise lorsque nécessaire.
- Ne pas exposer les clés API.
- Documenter les dépendances externes.

---

# 44. Timeouts et retries

Les opérations réseau doivent avoir des limites.

## Règles

- Définir des timeouts.
- Ne pas attendre indéfiniment une réponse.
- Réessayer uniquement les opérations qui peuvent l'être sans danger.
- Utiliser un backoff approprié lorsque nécessaire.
- Éviter de multiplier les requêtes lors d'une panne externe.
- Respecter les limites des services externes.

---

# 45. Architecture des fichiers

La structure doit être logique et prévisible.

Exemple pour une application backend :

```text
app/
├── api/
├── models/
├── schemas/
├── services/
├── repositories/
├── core/
├── utils/
├── tests/
└── main.py
```

Exemple pour une application frontend :

```text
src/
├── components/
├── routes/
├── lib/
├── services/
├── stores/
├── types/
└── assets/
```

La structure exacte dépend du framework et du projet. Il n'existe pas une architecture universelle obligatoire.

---

# 46. Ne pas mélanger les couches

Éviter les situations où :

```text
Component UI
    ↓
SQL direct
```

ou :

```text
Route API
    ↓
200 lignes de logique métier
```

Préférer une séparation claire :

```text
UI
 ↓
API
 ↓
Service
 ↓
Repository
 ↓
Database
```

Lorsque cette séparation est adaptée à la taille et aux besoins du projet.

---

# 47. Gestion des constantes

Éviter les valeurs magiques dispersées dans le code.

## Mauvais

```python
if status == 7:
    ...
```

si `7` représente une valeur métier non évidente.

## Bon

```python
STATUS_APPROVED = 7

if status == STATUS_APPROVED:
    ...
```

ou utiliser un type adapté, comme un enum, lorsque pertinent.

---

# 48. Fonctions

Une fonction doit avoir une responsabilité claire.

## Règles

- Éviter les fonctions trop longues.
- Éviter trop de paramètres.
- Éviter les effets secondaires cachés.
- Utiliser des noms explicites.
- Retourner des résultats prévisibles.
- Éviter les variables globales.
- Tester les cas limites.
- Extraire les parties complexes lorsque cela améliore la compréhension.

---

# 49. Classes

Une classe doit représenter un concept cohérent.

## Règles

- Éviter les classes gigantesques.
- Éviter les classes qui font tout.
- Limiter les responsabilités.
- Définir des interfaces claires.
- Masquer les détails internes lorsque cela apporte une vraie valeur.
- Préférer la composition à une hiérarchie d'héritage inutilement complexe.

---

# 50. Commentaires

Les commentaires doivent expliquer pourquoi lorsque ce pourquoi n'est pas évident.

## Mauvais

```python
# Incrémente i
i += 1
```

Le commentaire n'apporte rien.

## Plus utile

```python
# Nous conservons temporairement cette valeur pour maintenir
# la compatibilité avec les anciennes transactions importées.
```

## Règles

- Ne pas commenter l'évidence.
- Expliquer les décisions non évidentes.
- Expliquer les contraintes externes.
- Mettre à jour les commentaires lorsqu'une logique change.
- Ne jamais laisser des commentaires faux ou obsolètes.

---

# 51. Refactoring

Le code doit être régulièrement amélioré lorsque cela est nécessaire.

## Signes indiquant un besoin de refactoring

```text
Fonction trop longue
Code dupliqué
Conditions complexes
Classe gigantesque
Dépendances circulaires
Noms incompréhensibles
Tests difficiles
Modification d'une fonctionnalité qui casse plusieurs autres fonctionnalités
```

## Règles

- Refactoriser progressivement.
- Ne pas changer le comportement sans raison lorsqu'un refactoring est présenté comme tel.
- Exécuter les tests après le refactoring.
- Garder les changements de refactoring séparés des nouvelles fonctionnalités lorsque possible.

---

# 52. Dette technique

La dette technique doit être identifiée plutôt que cachée.

Exemples :

```text
TODO
FIXME
Solution temporaire
Dépendance obsolète
Code dupliqué
Architecture provisoire
```

## Règles

- Documenter les compromis importants.
- Éviter d'accumuler des solutions temporaires sans suivi.
- Prioriser les problèmes qui présentent un risque réel.
- Ne pas transformer chaque imperfection en chantier inutile.

---

# 53. Compatibilité et migrations

Lorsqu'une application évolue :

```text
Version 1
↓
Version 2
↓
Version 3
```

il faut prévoir les changements.

## Règles

- Utiliser des migrations de base de données.
- Documenter les changements incompatibles.
- Prévoir la migration des données.
- Tester les migrations.
- Prévoir un rollback lorsque possible.
- Ne pas supprimer brutalement des champs ou API utilisés sans stratégie de migration.

---

# 54. Sauvegarde et récupération

Pour les applications qui manipulent des données importantes :

## Règles

- Prévoir des sauvegardes.
- Tester la restauration.
- Définir une fréquence adaptée.
- Stocker les sauvegardes de manière appropriée.
- Protéger les sauvegardes.
- Définir une politique de rétention.
- Documenter la procédure de récupération.

Une sauvegarde qui n'a jamais été testée n'est pas une garantie suffisante.

---

# 55. Monitoring

Pour une application en production, surveiller lorsque nécessaire :

```text
Disponibilité
Temps de réponse
Erreurs
Utilisation CPU
Mémoire
Base de données
Espace disque
Services externes
```

## Règles

- Détecter rapidement les erreurs critiques.
- Surveiller les ressources importantes.
- Définir des alertes pertinentes.
- Éviter les alertes excessives et inutiles.
- Utiliser les logs et métriques pour diagnostiquer les problèmes.

---

# 56. Déploiement

Le déploiement doit être reproductible autant que possible.

## Règles

- Documenter le déploiement.
- Automatiser les étapes répétitives.
- Utiliser des variables d'environnement.
- Vérifier la configuration.
- Exécuter les migrations de manière contrôlée.
- Vérifier l'état de l'application après déploiement.
- Prévoir une procédure de rollback.

---

# 57. Principe de moindre surprise

Le comportement du code doit être prévisible.

Exemple :

Une fonction nommée :

```text
delete_user()
```

ne devrait pas également :

```text
supprimer les factures
envoyer des emails
supprimer les fichiers
modifier les permissions
```

sans que cela soit clairement défini et nécessaire.

## Règles

- Les noms doivent correspondre au comportement.
- Éviter les effets secondaires inattendus.
- Éviter les comportements implicites difficiles à deviner.
- Documenter les comportements importants.

---

# 58. Gestion des permissions

Toutes les actions sensibles doivent être protégées côté serveur.

Exemple :

```text
GET /users/25
```

ne doit pas automatiquement permettre à n'importe quel utilisateur connecté de consulter l'utilisateur 25.

Le backend doit vérifier :

```text
Utilisateur authentifié ?
        ↓
Permission suffisante ?
        ↓
Accès à cette ressource autorisé ?
```

Important :

> Masquer un bouton dans le frontend n'est pas une mesure de sécurité suffisante.

---

# 59. Sécurité des endpoints

Chaque endpoint protégé doit vérifier :

```text
Authentification
Autorisation
Validation
Accès à la ressource
```

Ne jamais faire confiance à :

```text
user_id
role
permission
price
amount
status
```

envoyés par le frontend sans vérification serveur.

---

# 60. Sécurité des exports

Les exports Excel, CSV, PDF ou autres peuvent contenir des informations sensibles.

## Règles

- Vérifier les permissions avant l'export.
- Exporter uniquement les données autorisées.
- Contrôler les filtres.
- Contrôler les gros volumes.
- Journaliser les exports sensibles lorsque nécessaire.
- Éviter d'inclure des informations confidentielles sans nécessité.

---

# 61. Qualité du code généré par une IA

Lorsqu'une IA génère ou modifie du code, elle doit suivre les mêmes exigences qu'un développeur professionnel.

L'IA ne doit pas :

- inventer des API ;
- inventer des bibliothèques ;
- inventer des paramètres ;
- inventer des fonctions du framework ;
- supprimer une fonctionnalité existante sans raison ;
- modifier silencieusement le comportement métier ;
- introduire des dépendances inutiles ;
- générer des secrets ;
- ignorer les erreurs ;
- utiliser `any` ou des équivalents sans nécessité ;
- générer des fichiers inutiles ;
- dupliquer du code ;
- contourner les permissions ;
- désactiver les mécanismes de sécurité pour résoudre rapidement un problème.

## L'IA doit :

- analyser le code existant avant de le modifier ;
- comprendre l'architecture existante ;
- respecter les conventions du projet ;
- préserver les fonctionnalités existantes ;
- expliquer les changements importants lorsque nécessaire ;
- vérifier les dépendances disponibles avant d'en ajouter ;
- vérifier les types ;
- vérifier les erreurs ;
- ajouter ou mettre à jour les tests ;
- éviter les modifications hors périmètre ;
- conserver la compatibilité lorsque cela est demandé ;
- signaler clairement les hypothèses ;
- ne jamais inventer une information technique.

---

# 62. Règles spécifiques lors d'une modification de code existant

Avant de modifier un projet existant :

1. Comprendre la structure du projet.
2. Identifier les fichiers concernés.
3. Identifier les dépendances.
4. Identifier les conventions.
5. Identifier les tests existants.
6. Comprendre le comportement actuel.
7. Déterminer précisément le changement demandé.
8. Éviter de modifier les parties non concernées.
9. Vérifier les conséquences du changement.
10. Exécuter les tests disponibles.
11. Ajouter les tests nécessaires.
12. Vérifier le résultat final.

Une modification ne doit pas être effectuée uniquement sur la base d'un extrait isolé lorsque le reste du projet est nécessaire pour comprendre le comportement.

---

# 63. Règles contre les régressions

Une nouvelle fonctionnalité ne doit pas casser les fonctionnalités existantes.

## Avant une modification

Identifier :

```text
Fonctionnalité actuelle
Entrées
Sorties
Dépendances
Cas limites
Tests
```

## Après une modification

Vérifier :

```text
Nouvelle fonctionnalité
Fonctionnalités existantes
Tests
Build
Types
Lint
Erreurs
```

---

# 64. Principe du changement minimal

Lorsqu'une demande concerne une fonctionnalité précise, ne pas réécrire inutilement toute l'application.

## Exemple

Si le problème concerne :

```text
Calcul du total d'une facture
```

éviter de modifier simultanément :

```text
Authentification
Navigation
Base de données
Design
API
Configuration
```

sans raison.

Le changement doit rester aussi limité que raisonnablement possible.

---

# 65. Gestion des dépendances entre fonctionnalités

Avant de modifier une fonctionnalité, rechercher les endroits qui l'utilisent.

Exemple :

```text
PaymentService
    ↓
InvoiceService
    ↓
ReportService
    ↓
ExportService
```

Modifier `PaymentService` peut avoir des conséquences sur plusieurs composants.

Il faut donc identifier les dépendances avant un refactoring important.

---

# 66. Contrats et interfaces

Les modules doivent communiquer via des contrats clairs.

Exemple :

```text
PaymentService
    ↓
create_payment(data)
    ↓
Payment
```

Le contrat doit préciser autant que nécessaire :

```text
Entrées
Types
Valeurs obligatoires
Valeurs facultatives
Sorties
Erreurs possibles
Effets secondaires
```

---

# 67. Gestion des états

Les applications doivent définir clairement les états possibles des entités.

Exemple :

```text
DRAFT
PENDING
APPROVED
REJECTED
CANCELLED
COMPLETED
```

## Règles

- Ne pas utiliser des chaînes incohérentes partout.
- Centraliser les états lorsque pertinent.
- Définir les transitions autorisées.
- Empêcher les transitions invalides.
- Tester les transitions.

---

# 68. Machines à états lorsque nécessaire

Pour une logique métier complexe, définir explicitement les transitions.

Exemple :

```text
DRAFT
  ↓
SUBMITTED
  ↓
APPROVED
  ↓
COMPLETED
```

Une opération ne devrait pas permettre arbitrairement :

```text
COMPLETED → DRAFT
```

si cette transition n'est pas autorisée par les règles métier.

---

# 69. Audit des actions sensibles

Pour les applications de gestion, conserver un historique lorsque le domaine le nécessite.

Exemple :

```text
2026-09-17 14:00
Utilisateur: 15
Action: UPDATE
Objet: Invoice #452
Champ: total
Ancienne valeur: 100000
Nouvelle valeur: 125000
```

L'historique doit être conçu pour être fiable et difficile à modifier accidentellement.

---

# 70. Prévention des doublons

Les doublons doivent être traités au niveau approprié.

Exemple :

```text
Deux utilisateurs créent simultanément
la même référence.
```

Ne pas compter uniquement sur :

```text
if not exists:
    create()
```

car deux requêtes concurrentes peuvent passer simultanément.

Lorsque nécessaire, utiliser une contrainte unique au niveau de la base de données.

---

# 71. Code et données : distinction

Le code ne doit pas confondre :

```text
Règle métier
Donnée
Configuration
Constante
Secret
```

Exemple :

```text
Taux de TVA
```

peut être une donnée configurable selon le contexte métier et ne doit pas forcément être codé en dur.

---

# 72. Internationalisation

Si l'application doit être multilingue :

## Règles

- Ne pas coder les textes directement partout.
- Utiliser un système de traduction adapté.
- Prévoir les textes plus longs.
- Gérer les formats de date.
- Gérer les formats numériques.
- Gérer les devises.
- Gérer les fuseaux horaires.

---

# 73. Localisation

Les valeurs affichées doivent respecter le contexte de l'utilisateur.

Exemple :

```text
Date
Montant
Devise
Nombre
Adresse
Langue
Fuseau horaire
```

Le stockage interne doit rester cohérent et indépendant de la présentation lorsque possible.

---

# 74. Gestion des gros volumes

Lorsque l'application peut traiter beaucoup de données :

## Règles

- Pagination.
- Filtrage côté serveur.
- Recherche optimisée.
- Indexation.
- Traitement par lots.
- Files de tâches lorsque nécessaire.
- Streaming pour certains fichiers volumineux.
- Éviter de charger inutilement toute la base en mémoire.

---

# 75. Tâches longues

Une opération longue ne doit pas nécessairement bloquer une requête HTTP.

Exemples :

```text
Génération d'un gros rapport
Import de 500 000 lignes
Envoi de milliers d'emails
Traitement d'un gros fichier
Calcul complexe
```

Selon l'architecture, utiliser :

```text
Background jobs
Queues
Workers
Tâches asynchrones
```

lorsque cela est approprié.

---

# 76. Observabilité

Une application complexe doit permettre de répondre à :

```text
Que s'est-il passé ?
Pourquoi ?
Quand ?
Pour quel utilisateur ?
Sur quelle requête ?
Avec quelle donnée ?
```

Les logs, métriques et traces peuvent être utilisés ensemble lorsque nécessaire.

---

# 77. Compatibilité mobile

Si l'application est destinée au mobile ou au responsive :

## Règles

- Tester plusieurs tailles d'écran.
- Éviter les éléments trop petits.
- Prévoir les interactions tactiles.
- Optimiser les performances réseau.
- Éviter les téléchargements inutiles.
- Prévoir les connexions lentes lorsque le contexte le justifie.

---

# 78. Gestion des connexions réseau instables

Pour les applications utilisées avec une connexion potentiellement instable :

## Règles

- Afficher clairement les états de chargement.
- Gérer les erreurs réseau.
- Éviter les doubles soumissions.
- Réessayer avec prudence.
- Préserver les données saisies lorsque possible.
- Informer l'utilisateur lorsqu'une opération n'a pas pu être confirmée.
- Vérifier côté serveur avant de considérer une opération comme réussie.

---

# 79. Sécurité par défaut

Le comportement par défaut doit être le plus sûr raisonnablement possible.

Exemples :

```text
Permission refusée par défaut
Données privées par défaut
HTTPS en production
Secrets hors du code
Validation activée
Logs sans secrets
```

Ne pas créer une sécurité qui dépend du fait qu'un développeur pense à activer manuellement une protection partout.

---

# 80. Fail safely

Lorsqu'une opération échoue, l'application doit revenir à un état sûr autant que possible.

Éviter :

```text
Erreur
↓
Données partiellement modifiées
↓
État incohérent
```

Préférer :

```text
Opération
↓
Validation
↓
Transaction
↓
Succès
```

ou :

```text
Opération
↓
Erreur
↓
Rollback / état cohérent
```

---

# 81. Principe de défense en profondeur

Une application ne doit pas dépendre d'une seule protection.

Exemple :

```text
Frontend validation
        +
Backend validation
        +
Authorization
        +
Database constraints
        +
Logging
```

Chaque couche apporte une protection supplémentaire.

---

# 82. Ne jamais faire confiance au frontend

Le frontend peut être manipulé.

Ne jamais considérer comme fiables :

```text
Prix
Montant
Role
User ID
Permissions
Statut
ID de propriétaire
```

Le backend doit recalculer ou vérifier les informations critiques.

---

# 83. Sécurité des paiements

Pour les applications qui gèrent des paiements :

## Règles

- Ne jamais considérer un paiement comme confirmé uniquement à partir du frontend.
- Vérifier les callbacks/webhooks.
- Vérifier les signatures lorsque le fournisseur en fournit.
- Gérer l'idempotence.
- Conserver les références de transaction.
- Journaliser les événements importants.
- Prévoir les transactions en attente.
- Prévoir les paiements échoués.
- Prévoir les paiements annulés.
- Prévoir les doublons.
- Ne jamais stocker des données bancaires sensibles sans nécessité et sans respecter les exigences applicables.

---

# 84. Sécurité des mots de passe

## Règles

- Ne jamais stocker les mots de passe en clair.
- Utiliser un algorithme de hash adapté.
- Ne jamais écrire les mots de passe dans les logs.
- Ne jamais les retourner dans une API.
- Prévoir une procédure sécurisée de récupération.
- Utiliser des protections contre les tentatives abusives lorsque nécessaire.

---

# 85. Sécurité des tokens

## Règles

- Ne pas exposer inutilement les tokens.
- Ne pas les écrire dans les logs.
- Définir leur durée de validité.
- Révoquer ou renouveler lorsque nécessaire.
- Utiliser un stockage adapté côté client.
- Protéger les secrets côté serveur.

---

# 86. Principe de zéro confiance pour les entrées

Toute donnée externe doit être considérée comme :

```text
Potentiellement incorrecte
Potentiellement malveillante
Potentiellement incomplète
```

Cela concerne également les données provenant :

```text
Frontend
API interne
API externe
Base de données
Fichiers
Webhooks
Administrateurs
Scripts
```

---

# 87. Qualité des noms

Les noms doivent communiquer l'intention.

## Mauvais

```text
data
tmp
x
foo
manager
process()
```

lorsque ces noms ne permettent pas de comprendre leur rôle.

## Bon

```text
customer_data
temporary_file_path
payment_amount
calculate_invoice_total()
validate_payment_reference()
```

---

# 88. Éviter les valeurs magiques

## Mauvais

```python
if amount > 1000000:
    ...
```

si `1000000` correspond à une règle métier importante.

## Bon

```python
MAX_TRANSACTION_AMOUNT = 1_000_000

if amount > MAX_TRANSACTION_AMOUNT:
    ...
```

Ou utiliser une configuration métier lorsque la valeur doit être modifiable.

---

# 89. Gestion des fichiers de configuration

Un projet doit distinguer autant que possible :

```text
Code
Configuration
Secrets
Données
Logs
Fichiers générés
```

Exemple :

```text
src/
config/
.env
data/
logs/
uploads/
```

Ne pas mélanger ces catégories sans raison.

---

# 90. Règle générale pour une IA développant une application

Avant de générer du code, l'IA doit chercher à comprendre :

```text
1. Le besoin fonctionnel
2. Les utilisateurs
3. Les rôles
4. Les règles métier
5. Les données
6. L'architecture
7. La stack technique
8. Les contraintes
9. Les intégrations externes
10. Les exigences de sécurité
11. Les exigences de performance
12. Les exigences de test
13. Les exigences de déploiement
```

Elle ne doit pas commencer immédiatement à produire des centaines de lignes de code si le contexte nécessaire n'est pas compris.

---

# 91. Règle générale pour une IA modifiant une application

Avant toute modification importante :

```text
Analyser
↓
Comprendre
↓
Identifier les dépendances
↓
Planifier
↓
Modifier
↓
Tester
↓
Vérifier
↓
Documenter si nécessaire
```

---

# 92. Règle de conservation du comportement

Lorsqu'une demande est formulée comme :

```text
corrige ce bug
refactorise ce fichier
optimise cette fonction
```

l'IA doit préserver le comportement fonctionnel existant sauf lorsqu'un changement de comportement est explicitement demandé.

---

# 93. Règle de transparence

Si l'IA n'est pas certaine d'une information technique, elle ne doit pas l'inventer.

Elle doit :

```text
Identifier l'incertitude
Vérifier la documentation disponible
Examiner le code existant
Proposer une hypothèse clairement indiquée
```

Elle ne doit pas inventer :

```text
API
Méthodes
Options
Paramètres
Bibliothèques
Versions
Fonctionnalités d'un framework
```

---

# 94. Règle de compatibilité avec la stack

Le code doit respecter les versions réellement utilisées.

Exemple :

```text
SvelteKit
FastAPI
Python
SQLite
PostgreSQL
Tailwind CSS
Odoo
Laravel
```

Il ne faut pas mélanger aveuglément des syntaxes appartenant à des versions différentes.

Avant d'utiliser une fonctionnalité spécifique à une version, vérifier la compatibilité lorsque l'information est disponible.

---

# 95. Règle de dépendance minimale

Avant d'ajouter une bibliothèque :

```text
1. Vérifier si le framework possède déjà la fonctionnalité.
2. Vérifier si une bibliothèque déjà installée peut répondre au besoin.
3. Évaluer la nécessité d'une nouvelle dépendance.
4. Vérifier sa maintenance.
5. Vérifier sa sécurité.
6. Vérifier sa compatibilité.
```

---

# 96. Règle de test après changement

Après une modification importante :

```text
Lint
↓
Type check
↓
Tests unitaires
↓
Tests d'intégration
↓
Build
↓
Vérification manuelle si nécessaire
```

La séquence exacte dépend du projet.

---

# 97. Règle de qualité avant livraison

Avant de considérer une fonctionnalité comme terminée, vérifier :

```text
Fonctionnement
Lisibilité
Architecture
Sécurité
Validation
Gestion des erreurs
Tests
Performance
Documentation
Logs
Permissions
Compatibilité
```

---

# 98. Checklist finale de qualité

## Fonctionnel

- [ ] La fonctionnalité répond au besoin.
- [ ] Les cas normaux fonctionnent.
- [ ] Les cas limites sont traités.
- [ ] Les erreurs sont gérées.
- [ ] Les permissions sont correctes.

## Code

- [ ] Le code est lisible.
- [ ] Les noms sont explicites.
- [ ] Les fonctions ont des responsabilités claires.
- [ ] Les classes ont des responsabilités claires.
- [ ] La duplication est limitée.
- [ ] Le code n'est pas inutilement complexe.
- [ ] Les dépendances sont maîtrisées.

## Architecture

- [ ] Les responsabilités sont séparées.
- [ ] Les modules sont cohérents.
- [ ] Les dépendances sont maîtrisées.
- [ ] Les couches sont correctement séparées.
- [ ] L'architecture peut évoluer.

## Sécurité

- [ ] Authentification correcte.
- [ ] Autorisation correcte.
- [ ] Validation côté backend.
- [ ] Secrets protégés.
- [ ] Mots de passe hashés.
- [ ] Protection contre les injections.
- [ ] Protection des données sensibles.
- [ ] Logs sans secrets.
- [ ] Principe du moindre privilège appliqué.

## Base de données

- [ ] Schéma cohérent.
- [ ] Contraintes appropriées.
- [ ] Index nécessaires.
- [ ] Migrations présentes.
- [ ] Transactions utilisées lorsque nécessaire.
- [ ] Doublons contrôlés.
- [ ] Intégrité des données protégée.

## Tests

- [ ] Tests unitaires.
- [ ] Tests d'intégration.
- [ ] Tests des erreurs.
- [ ] Tests des permissions.
- [ ] Tests des cas limites.
- [ ] Tests de régression.
- [ ] Tests automatisés lorsque possible.

## Performance

- [ ] Pas de requêtes inutiles.
- [ ] Pagination lorsque nécessaire.
- [ ] Requêtes optimisées.
- [ ] Gros volumes gérés correctement.
- [ ] Tâches longues traitées correctement.
- [ ] Cache utilisé uniquement lorsqu'il est pertinent.

## Documentation

- [ ] README présent.
- [ ] Installation documentée.
- [ ] Configuration documentée.
- [ ] Variables d'environnement documentées.
- [ ] API documentée.
- [ ] Architecture documentée lorsque nécessaire.
- [ ] Décisions importantes documentées.

## Production

- [ ] Configuration séparée.
- [ ] Secrets séparés.
- [ ] Logs disponibles.
- [ ] Monitoring lorsque nécessaire.
- [ ] Sauvegardes prévues lorsque nécessaire.
- [ ] Restauration testée lorsque nécessaire.
- [ ] Déploiement reproductible.
- [ ] Procédure de rollback lorsque nécessaire.

## Versionnement

- [ ] Git utilisé.
- [ ] Commits cohérents.
- [ ] Secrets absents du dépôt.
- [ ] `.gitignore` correctement configuré.
- [ ] Branches utilisées selon le workflow.
- [ ] Historique compréhensible.

---

# 99. Règle fondamentale

Un code professionnel doit satisfaire simultanément plusieurs dimensions :

```text
BON CODE
│
├── Fonctionnel
├── Lisible
├── Simple
├── Modulaire
├── Sécurisé
├── Robuste
├── Testable
├── Maintenable
├── Évolutif
├── Performant
├── Documenté
├── Traçable
├── Cohérent
└── Versionné
```

La qualité du code ne doit donc pas être évaluée uniquement par la question :

```text
"Est-ce que ça fonctionne ?"
```

Il faut également demander :

```text
"Est-ce que c'est compréhensible ?"
"Est-ce que c'est maintenable ?"
"Est-ce que c'est sécurisé ?"
"Est-ce que c'est testable ?"
"Est-ce que c'est robuste ?"
"Est-ce que cela peut évoluer ?"
"Est-ce que les erreurs sont correctement gérées ?"
"Est-ce que les données sont protégées ?"
"Est-ce que les comportements critiques sont traçables ?"
"Est-ce qu'un autre développeur pourra reprendre ce code facilement ?"
```

---

# 100. Principe final pour une IA de développement

Lorsqu'une IA conçoit, génère, modifie, corrige ou refactorise une application, elle doit systématiquement rechercher le meilleur équilibre entre :

```text
Correctness
+
Simplicity
+
Readability
+
Security
+
Maintainability
+
Testability
+
Performance
+
Scalability
+
Observability
+
Consistency
```

Elle doit privilégier un code :

```text
simple
compréhensible
prévisible
sécurisé
testable
maintenable
évolutif
```

plutôt qu'un code :

```text
complexe
court mais illisible
sur-architecturé
dépendant de nombreuses bibliothèques
fragile
non testé
difficile à maintenir
```

La finalité est de produire une application dont le code peut être compris, vérifié, testé, corrigé et étendu de manière fiable dans le temps.
