# Gestion des médicaments

Application web open source de gestion des médicaments pour plusieurs
patients : suivi des prises, gestion du stock, alertes de réapprovisionnement,
vérification des interactions médicamenteuses et export des données pour les
professionnels de santé.

> **Statut** : projet en développement actif — Paliers 1 (socle), 2 (suivi
> des prises), 3 (stock) et 4 (notifications) terminés et testés (90 tests
> automatisés). Palier 5 (interactions médicamenteuses) à venir. Voir
> [`docs/`](./docs) et la feuille de route ci-dessous pour le détail.

## ⚠️ Avertissement — À lire avant toute utilisation

**Ce logiciel est un projet personnel/communautaire en développement, sans
certification médicale ni validation clinique.** Il n'est ni un dispositif
médical, ni un service certifié pour un usage professionnel de santé en
l'état.

- **Aucune garantie n'est fournie**, explicite ou implicite, quant à
  l'exactitude, la fiabilité ou l'exhaustivité des informations produites par
  l'application (y compris les alertes de stock, les rappels de prise, les
  calculs de dosage ou toute future vérification d'interactions
  médicamenteuses).
- **L'utilisation se fait entièrement aux risques et périls de
  l'utilisateur.** En cas de bug, d'erreur d'affichage, de calcul incorrect
  ou de dysfonctionnement, ni les auteurs ni les contributeurs du projet ne
  pourront être tenus responsables des conséquences, y compris en matière de
  santé.
- **Ce logiciel ne remplace en aucun cas l'avis, le suivi ou les
  prescriptions d'un professionnel de santé.** Ne jamais modifier un
  traitement, un dosage ou un horaire de prise sur la seule base d'une
  information affichée par l'application, sans confirmation d'un médecin ou
  d'un pharmacien.
- En cas de doute sur un médicament, un dosage ou une interaction, consultez
  toujours un professionnel de santé ou les sources officielles (BDPM, ANSM,
  votre pharmacien).
- Voir aussi la licence [MIT](./LICENSE), qui inclut une clause de
  non-garantie standard ("AS IS").

Cette limitation de responsabilité s'applique à l'ensemble du logiciel,
présent et futur, y compris les modules de vérification d'interactions
médicamenteuses qui seront ajoutés ultérieurement.

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

L'API est ensuite disponible sur `http://localhost:8000` (adaptez le port si
vous l'avez modifié dans `docker-compose.yml`).

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

### Lancer les tests

```bash
python manage.py test
```

## Import du référentiel médicaments (BDPM)

Le référentiel des médicaments n'est jamais saisi manuellement : il est
importé depuis les fichiers officiels de la BDPM
(https://base-donnees-publique.medicaments.gouv.fr/telechargement.php,
section « Téléchargement »).

Téléchargez au moins `CIS_bdpm.txt` (spécialités) et, pour obtenir le
dosage, `CIS_COMPO_bdpm.txt` (compositions) :

```bash
python manage.py import_bdpm --fichier ./CIS_bdpm.txt --fichier-composition ./CIS_COMPO_bdpm.txt
```

La commande est idempotente (relancer met à jour sans dupliquer) et continue
sur les lignes suivantes en cas de ligne malformée, avec un rapport d'erreurs
en fin d'exécution.

> **Limitation connue** : le code ATC n'est pas renseigné par cet import — il
> n'est disponible dans les fichiers en téléchargement libre que pour le
> sous-ensemble des médicaments d'intérêt thérapeutique majeur (MITM), non
> encore importé.

## Fonctionnement du suivi des prises et du stock (paliers 2 et 3)

- Chaque **prescription** est soit **régulière** (horaires fixes, via
  `HoraireProgramme`) soit **réserve** (usage ponctuel, avec un plafond
  journalier optionnel).
- Pour les prescriptions régulières, les prises attendues des prochains
  jours sont **générées à l'avance** :
  ```bash
  python manage.py generer_prises_attendues --jours 30
  ```
  À exécuter régulièrement (cron quotidien recommandé — automatisation
  prévue au palier 4).
- Chaque prise enregistrée avec le statut `prise` **décrémente
  automatiquement** le stock (boîtes actives, épuisement de la boîte qui
  périme le plus tôt en premier). Un patient peut librement corriger ou
  supprimer une prise déjà enregistrée : le stock est réajusté en
  conséquence.
- Le stock déclenche une alerte (`en_alerte`) sur un seuil de quantité
  restante et/ou sur un nombre de jours restants estimé à partir de la
  consommation réelle récente.

## Notifications (palier 4)

Trois canaux, à des degrés de maturité différents :

| Canal | État |
|---|---|
| **E-mail** | Fonctionnel. Backend "console" en développement (les e-mails s'affichent dans les logs) ; à remplacer par un vrai SMTP en production. |
| **In-app** | Fonctionnel. Consultable via `/api/v1/notifications/`, marquable comme lue (`PATCH` avec `statut: "lue"`). |
| **SMS** | Interface prête mais **désactivée** (`SMS_BACKEND_ACTIVE=False`) : aucun fournisseur (Twilio, OVHcloud SMS...) n'est configuré, faute de compte payant. Une notification SMS est explicitement marquée en échec plutôt que faussement "envoyée" — voir `apps/notifications/canaux.py` pour le point d'extension. |

Deux commandes à exécuter régulièrement (cron recommandé, Celery Beat en
alternative future) :

```bash
# Toutes les 5 à 15 minutes : rappels de prise à venir
python manage.py envoyer_rappels_prises --fenetre-minutes 15

# Une fois par jour : alertes de stock bas
python manage.py verifier_alertes_stock --delai-relance-heures 24
```

## Vérification des interactions médicamenteuses (palier 5)

⚠️ **Point critique à comprendre avant d'activer cette fonctionnalité** :
l'ANSM a **arrêté la mise à jour** du Thésaurus des interactions
médicamenteuses. La version importée ici (15/09/2023) est la **dernière
publiée et ne sera plus jamais actualisée par l'ANSM**. Le Thésaurus reste
accessible sur son site jusqu'au 15/06/2027, sans garantie d'exhaustivité
par rapport aux RCP (résumés des caractéristiques du produit) actuels, qui
sont désormais la seule référence officiellement opposable.

Il n'existe, à ce jour, aucune base d'interactions française à la fois
gratuite, structurée et activement maintenue (Thériaque et Vidal, agréées
HAS, nécessitent une licence commerciale payante pour une intégration
logicielle).

### Ce qui est importé, et ce qui ne l'est pas

- Seules les entrées à **niveau de gravité non ambigu** sont importées
  automatiquement (`InteractionMedicamenteuse`).
- Les entrées à **niveau conditionnel** selon la dose ou le contexte
  clinique (codes composés type `CI - ASDEC - APEC`) sont volontairement
  **exclues** de l'import automatique et conservées à part
  (`InteractionNonImportee`) pour une revue manuelle — jamais de niveau
  deviné.
- La correspondance entre les médicaments prescrits et les protagonistes
  du Thésaurus se fait par **nom de substance active exact**. Les
  interactions définies au niveau d'une **classe thérapeutique** (ex.
  "INDUCTEURS ENZYMATIQUES PUISSANTS") ne sont pas résolues vers leurs
  substances membres dans cette version — donc pas détectées
  automatiquement dans ce cas.

### Importer le Thésaurus

```bash
# 1. Télécharger le PDF officiel depuis ansm.sante.fr
#    (rechercher "Thésaurus des interactions médicamenteuses")

# 2. Le convertir en texte en conservant la mise en page
pdftotext -layout thesaurus.pdf thesaurus.txt

# 3. Importer
python manage.py import_thesaurus --fichier thesaurus.txt
```

### Vérifier les interactions d'un patient

```
GET /api/v1/patients/<id>/verifier-interactions/
```

La réponse inclut systématiquement un champ `avertissement` rappelant la
date de fige du Thésaurus — jamais uniquement documenté à part.

## Exemples d'utilisation

- **Administrateur** : se connecte via `/admin`, crée les comptes, importe le
  référentiel médicaments, supervise l'ensemble des patients.
- **Médecin** : crée un patient (devient automatiquement son médecin
  suiveur), rédige ses prescriptions, consulte le journal de consommation et
  le stock des patients qu'il suit.
- **Patient** : consulte son propre dossier et ses prescriptions, enregistre
  librement ses prises et gère son propre stock de boîtes.

L'API est consultable et utilisable directement via l'interface navigable de
Django REST Framework (`/api/v1/...`), en attendant le frontend du palier 6.

## Feuille de route (paliers)

1. ✅ Terminé — Socle : auth, rôles, patients, référentiel médicaments (import BDPM)
2. ✅ Terminé — Suivi : prescriptions, prises programmées, journal de consommation
3. ✅ Terminé — Stock : boîtes, décompte automatique, alertes de réapprovisionnement
4. ✅ Terminé — Notifications : e-mail et in-app fonctionnels ; SMS en attente d'un fournisseur
5. ✅ Terminé — Vérification des interactions médicamenteuses (Thésaurus ANSM, figé depuis sept. 2023 — voir avertissement ci-dessus)
6. ⏳ À venir — Exports (PDF/Excel) et finitions UX (frontend, tableau de bord, thème clair/sombre)

Le détail de chaque palier est documenté dans [`docs/`](./docs).

## Contribuer

Les contributions sont bienvenues ! Voir [`CONTRIBUTING.md`](./CONTRIBUTING.md)
pour le processus (organisation par palier, style de code, Pull Requests).

## Licence

Ce projet est distribué sous licence [MIT](./LICENSE) — libre d'utilisation,
de modification et de redistribution, **fournie "telle quelle", sans
garantie d'aucune sorte** (voir l'avertissement en début de document et le
texte complet de la licence).

## Contributeurs

- *(à compléter au fil des contributions)*

