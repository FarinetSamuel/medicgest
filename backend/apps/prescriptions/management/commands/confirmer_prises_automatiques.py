"""
Confirme automatiquement les prises programmées (prescriptions
régulières) dont l'heure prévue est atteinte, pour les prescriptions
ayant l'option `confirmation_automatique` activée (valeur par défaut) —
voir apps.prescriptions.logique.confirmer_prises_automatiques pour la
décision de conception détaillée.

Usage :
    python manage.py confirmer_prises_automatiques

Destinée à être exécutée fréquemment (cron, voir README) pour que le
basculement Attendue -> Prise ait lieu peu après l'heure prévue.
"""

from django.core.management.base import BaseCommand

from apps.prescriptions.logique import confirmer_prises_automatiques


class Command(BaseCommand):
    help = (
        "Confirme automatiquement les prises programmées dont l'heure prévue est atteinte "
        "(prescriptions régulières avec confirmation_automatique=True)."
    )

    def handle(self, *args, **options):
        confirmees = confirmer_prises_automatiques()
        self.stdout.write(
            self.style.SUCCESS(f"{len(confirmees)} prise(s) confirmée(s) automatiquement.")
        )
