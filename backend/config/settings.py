"""
Réglages Django du projet "Gestion des médicaments".

Les valeurs sensibles (clé secrète, identifiants base de données, etc.)
sont lues depuis les variables d'environnement via django-environ, jamais
codées en dur — voir le fichier .env.example à la racine du dépôt.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Origines autorisées à appeler l'API depuis un navigateur (frontend React
# servi séparément, cf. docker-compose.yml). Aucune valeur par défaut
# risquée : liste vide tant que CORS_ALLOWED_ORIGINS n'est pas explicitement
# renseigné dans le .env (voir .env.example), pour ne jamais ouvrir l'API
# à une origine non voulue par accident.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "rest_framework",
    "corsheaders",
    # Applications métier
    "apps.utilisateurs",
    "apps.patients",
    "apps.medicaments",
    "apps.prescriptions",
    "apps.stock",
    "apps.notifications",
    "apps.interactions",
    "apps.exports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware doit être placé le plus haut possible, et en tout cas
    # avant CommonMiddleware, pour pouvoir ajouter ses en-têtes avant
    # qu'une autre réponse (y compris une erreur) ne soit générée.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de données : PostgreSQL en développement comme en production, pour
# éviter les écarts de comportement entre environnements (contraintes,
# types de champs) — pas de SQLite, même en local.
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/gestion_medicaments"),
}

AUTH_USER_MODEL = "utilisateurs.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        # BasicAuthentication : pratique pour tester l'API en local (curl,
        # Postman) sans configurer de session. À retirer ou restreindre en
        # production réelle si l'API est exposée publiquement sans HTTPS.
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# Durées de vie volontairement explicites plutôt que de laisser les
# valeurs par défaut de simplejwt (5 min / 1 jour) implicites — le
# frontend gère déjà le rafraîchissement silencieux (voir lib/api.ts).
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Backend "console" par défaut (écrit l'email dans les logs, n'envoie
# rien réellement) : comportement sûr et inchangé tant que EMAIL_HOST
# n'est pas configuré. Pour un envoi réel, régler EMAIL_BACKEND sur
# "django.core.mail.backends.smtp.EmailBackend" et les EMAIL_* ci-dessous
# dans le .env, avec n'importe quel fournisseur SMTP (hébergeur, Gmail,
# SendGrid, Mailgun...) — voir .env.example.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@gestion-medicaments.local")

# SMS : désactivé tant qu'aucun fournisseur (Twilio, OVHcloud SMS...) n'est
# configuré avec de vrais identifiants — voir apps/notifications/canaux.py.
SMS_BACKEND_ACTIVE = env.bool("SMS_BACKEND_ACTIVE", default=False)

# Fenêtre par défaut (minutes) avant l'heure prévue d'une prise régulière
# pour déclencher un rappel — voir apps/notifications/logique.py.
RAPPEL_PRISE_FENETRE_MINUTES = env.int("RAPPEL_PRISE_FENETRE_MINUTES", default=15)
