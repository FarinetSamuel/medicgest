#!/bin/sh
# Point d'entrée du conteneur backend : démarre cron en tâche de fond
# (paliers 2/4, voir backend/cron/crontab) puis lance le serveur Django
# au premier plan. Les deux tournent dans le même conteneur — Arcane
# résout les images par service et ne sait pas réutiliser localement
# l'image d'un service sœur sans registre, donc un second service "cron"
# séparé tentait un `docker pull` inexistant plutôt qu'un build local.
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
# Les logs cron sont mêlés à ceux du serveur Django (mêmes stdout/stderr),
# visibles ensemble via `docker compose logs -f backend`.
tail -F /var/log/cron/cron.log &

exec python manage.py runserver 0.0.0.0:8000
