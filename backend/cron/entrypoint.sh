#!/bin/sh
# Point d'entrée du service "cron" (docker-compose). Capture l'environnement
# du conteneur (DATABASE_URL, DJANGO_SECRET_KEY, ...) dans un fichier que
# run_task.sh source avant chaque tâche, car cron ne transmet pas
# l'environnement du process qui le lance à ses tâches planifiées.
set -e

# python -c avec shlex.quote plutôt qu'un sed naïf : des valeurs comme
# DJANGO_SECRET_KEY peuvent contenir $, ", ' ... qu'un export mal échappé
# romprait ou pire, réinterpréterait au moment du ". env.sh".
python -c "
import os, shlex
skip = {'HOME', 'HOSTNAME', 'PWD'}
with open('/app/cron/env.sh', 'w') as f:
    for k, v in os.environ.items():
        if k in skip:
            continue
        f.write('export %s=%s\n' % (k, shlex.quote(v)))
"
chmod 600 /app/cron/env.sh

mkdir -p /var/log/cron
touch /var/log/cron/cron.log

crontab /app/cron/crontab

cron
exec tail -f /var/log/cron/cron.log
