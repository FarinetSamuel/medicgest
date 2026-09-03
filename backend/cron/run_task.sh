#!/bin/sh
# Exécute une commande de management Django depuis cron avec l'environnement
# du conteneur (cron ne l'hérite pas nativement, voir entrypoint.sh).
set -e

. /etc/cron-env.sh
cd /app
exec python manage.py "$@"
