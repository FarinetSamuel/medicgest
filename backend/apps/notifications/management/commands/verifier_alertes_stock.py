"""
Détecte les boîtes en alerte et envoie les notifications correspondantes
(in_app + email), sans relancer une alerte déjà notifiée récemment.

Destiné à tourner régulièrement (cron quotidien recommandé).

Usage :
    python manage.py verifier_alertes_stock --delai-relance-heures 24
"""

from django.core.management.base import BaseCommand

from apps.notifications.canaux import envoyer_notification
from apps.notifications.logique import generer_alertes_rupture_stock, generer_alertes_stock


class Command(BaseCommand):
    help = "Envoie les alertes de stock (quantité/jours bas, rupture totale)."

    def add_arguments(self, parser):
        parser.add_argument("--delai-relance-heures", type=int, default=24)

    def handle(self, *args, **options):
        notifications = generer_alertes_stock(options["delai_relance_heures"])
        notifications += generer_alertes_rupture_stock(options["delai_relance_heures"])
        for notification in notifications:
            envoyer_notification(notification)

        self.stdout.write(self.style.SUCCESS(f"{len(notifications)} notification(s) d'alerte traitée(s)."))
