"""
Génère à l'avance les Prise (statut ATTENDUE) pour toutes les
prescriptions régulières actives, sur une fenêtre de N jours.

Décision validée avec le porteur du projet : les prises attendues sont
générées à l'avance (calendrier complet), pas calculées à la volée.

Usage :
    python manage.py generer_prises_attendues --jours 30

Destiné à être exécuté quotidiennement (cron ou tâche planifiée Celery
au palier 4) pour maintenir la fenêtre glissante à jour.
"""

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.prescriptions.models import HoraireProgramme, Prescription, Prise


class Command(BaseCommand):
    help = "Génère à l'avance les prises attendues des prescriptions régulières actives."

    def add_arguments(self, parser):
        parser.add_argument(
            "--jours",
            type=int,
            default=30,
            help="Nombre de jours à couvrir à partir d'aujourd'hui (défaut : 30).",
        )

    def handle(self, *args, **options):
        nb_jours = options["jours"]
        aujourdhui = timezone.localdate()
        jours_a_couvrir = [aujourdhui + datetime.timedelta(days=i) for i in range(nb_jours)]

        horaires = HoraireProgramme.objects.filter(
            actif=True,
            prescription__type_prise=Prescription.TypePrise.REGULIERE,
            prescription__statut=Prescription.Statut.ACTIVE,
        ).select_related("prescription")

        creees = 0
        for horaire in horaires:
            prescription = horaire.prescription
            for jour in jours_a_couvrir:
                if jour < prescription.date_debut:
                    continue
                if prescription.date_fin and jour > prescription.date_fin:
                    continue

                date_heure_prevue = timezone.make_aware(
                    datetime.datetime.combine(jour, horaire.heure)
                )
                _, cree = Prise.objects.get_or_create(
                    prescription=prescription,
                    horaire_programme=horaire,
                    date_heure_prevue=date_heure_prevue,
                    defaults={
                        "quantite_prevue": horaire.quantite,
                        "statut": Prise.Statut.ATTENDUE,
                    },
                )
                creees += int(cree)

        self.stdout.write(self.style.SUCCESS(f"{creees} prise(s) attendue(s) créée(s)."))
