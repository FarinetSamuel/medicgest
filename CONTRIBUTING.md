# Contribuer au projet

Merci de votre intérêt pour ce projet ! Ce document explique comment participer.

## Organisation du développement

Le projet avance par **paliers** fonctionnels autonomes (voir `docs/`) :
1. Socle (auth, patients, référentiel médicaments) — en cours
2. Suivi (prescriptions, prises, journal)
3. Stock
4. Notifications
5. Vérification des interactions médicamenteuses
6. Exports et finitions UX

Merci de vérifier dans les *issues* GitHub à quel palier correspond votre contribution avant de commencer.

## Mise en place de l'environnement local

Voir la section "Installation" du `README.md`.

## Style de code

- **Backend (Python/Django)** : respecter PEP 8, formater avec `black`, trier les imports avec `isort`.
- **Commits** : messages clairs en français ou anglais, au présent (« Ajoute... » plutôt que « Ajouté... »).
- **Tests** : toute nouvelle fonctionnalité doit être accompagnée de tests (`python manage.py test`).

## Processus de contribution

1. Forker le dépôt et créer une branche depuis `develop` : `git checkout -b palier1/ma-fonctionnalite`
2. Développer + tester localement
3. Ouvrir une Pull Request vers `develop` en décrivant le changement et le palier concerné
4. Un mainteneur relit et fusionne après validation de la CI

## Signaler un bug ou proposer une idée

Utiliser les *issues* GitHub avec un modèle clair : contexte, comportement attendu, comportement observé.
