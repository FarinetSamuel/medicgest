"""
Détecte les prises attendues prochainement et envoie les rappels
correspondants (in_app + email).

Destiné à tourner fréquemment (cron toutes les 5-15 minutes) tant que
Celery Beat n'est pas mis en place.

Usage :
    python manage.py envoyer_rappels_prises --fenetre-minutes 15
"""

from django.core.management.base import BaseCommand

from apps.notifications.canaux import envoyer_notification
from apps.notifications.logique import generer_rappels_prises_a_venir


class Command(BaseCommand):
    help = "Envoie les rappels de prise pour les prises attendues dans la fenêtre donnée."

    def add_arguments(self, parser):
        parser.add_argument("--fenetre-minutes", type=int, default=None)

    def handle(self, *args, **options):
        notifications = generer_rappels_prises_a_venir(options["fenetre_minutes"])
        for notification in notifications:
            envoyer_notification(notification)

        self.stdout.write(self.style.SUCCESS(f"{len(notifications)} notification(s) de rappel traitée(s)."))
