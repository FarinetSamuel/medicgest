# Gestion des médicaments

Application web open source de gestion des médicaments pour plusieurs
patients : suivi des prises, gestion du stock, alertes de réapprovisionnement,
vérification des interactions médicamenteuses et export des données pour les
professionnels de santé.

> **Statut** : projet en développement — Palier 1 (socle : authentification,
> patients, référentiel médicaments) en cours. Voir [`docs/`](./docs) pour le
> détail des paliers à venir.

## Fonctionnalités visées

- Gestion **multi-patients**, accessible depuis un navigateur
- Suivi de la consommation : date, heure, quantité, dosage de chaque prise
- Gestion du **stock** par boîte (quantité, délai de réapprovisionnement) avec
  alertes de commande
- Gestion des médicaments prescrits **en réserve** pour usage ponctuel
- **Notifications** de prise (e-mail, SMS, in-app)
- **Vérification des interactions** médicamenteuses, à partir des données
  officielles de l'ANSM (thésaurus des interactions) et de la BDPM
- **Export** des données (Excel, PDF) pour les partager avec un professionnel
  de santé
- **Rôles** différenciés : administrateur, médecin, patient, avec permissions
  spécifiques
- Interface avec **thème clair/sombre**, tableau de bord, navigation claire

## Stack technique

| Composant | Choix |
|---|---|
| Backend | Python / Django + Django REST Framework |
| Base de données | PostgreSQL |
| Frontend | React + TypeScript (à partir du palier 6) |
| Tâches planifiées | Celery + Redis (à partir du palier 4) |
| Conteneurisation | Docker / docker-compose |

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose
- Ou, pour un développement sans Docker : Python 3.12+, PostgreSQL 16+

## Installation et lancement en local

### Avec Docker (recommandé)

```bash
git clone https://github.com/<votre-organisation>/gestion-medicaments.git
cd gestion-medicaments
cp .env.example .env        # puis adapter les valeurs si besoin
docker compose up --build
```

L'API est ensuite disponible sur `http://localhost:8000`.

Pour appliquer les migrations et créer un compte administrateur :

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### Sans Docker

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example ../.env    # adapter DATABASE_URL vers votre PostgreSQL local
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Import du référentiel médicaments (BDPM)

Le référentiel des médicaments n'est jamais saisi manuellement : il est
importé depuis les fichiers officiels de la BDPM
(https://base-donnees-publique.medicaments.gouv.fr/telechargement.php).

```bash
python manage.py import_bdpm --fichier /chemin/vers/CIS_bdpm.txt
```

## Exemples d'utilisation

- **Administrateur** : se connecte via `/admin`, crée les comptes médecins et
  supervise l'ensemble des patients.
- **Médecin** : consulte et met à jour les dossiers des patients qu'il suit,
  ajoute des notes médicales structurées (allergies, antécédents).
- **Patient** : consulte son propre dossier, son planning de prises et ses
  alertes de stock une fois les paliers suivants disponibles.

## Feuille de route (paliers)

1. ✅ En cours — Socle : auth, rôles, patients, référentiel médicaments
2. Suivi : prescriptions, prises programmées, journal de consommation
3. Stock : boîtes, quantités, alertes de réapprovisionnement
4. Notifications : e-mail, in-app, SMS
5. Vérification des interactions médicamenteuses (thésaurus ANSM)
6. Exports (PDF/Excel) et finitions UX (tableau de bord, thème clair/sombre)

Le détail de chaque palier est documenté dans [`docs/`](./docs).

## Contribuer

Les contributions sont bienvenues ! Voir [`CONTRIBUTING.md`](./CONTRIBUTING.md)
pour le processus (organisation par palier, style de code, Pull Requests).

## Licence

Ce projet est distribué sous licence [MIT](./LICENSE) — libre d'utilisation,
de modification et de redistribution.

## Contributeurs

- *(à compléter au fil des contributions)*
