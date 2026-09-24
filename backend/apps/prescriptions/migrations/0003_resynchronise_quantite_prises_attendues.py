"""
Migration de données : répare les Prise ATTENDUE à venir dont la
quantite_prevue ne correspond plus à la quantité actuelle de leur
horaire (modifiée après génération, avant que la synchronisation
automatique n'existe — voir logique.synchroniser_quantite_prises_attendues).
"""

from django.db import migrations
from django.db.models import F
from django.utils import timezone


def resynchroniser(apps, schema_editor):
    Prise = apps.get_model("prescriptions", "Prise")
    a_corriger = (
        Prise.objects.filter(
            statut="attendue",
            date_heure_prevue__gte=timezone.now(),
            horaire_programme__isnull=False,
        )
        .exclude(quantite_prevue=F("horaire_programme__quantite"))
        .select_related("horaire_programme")
    )
    for prise in a_corriger:
        prise.quantite_prevue = prise.horaire_programme.quantite
        prise.save(update_fields=["quantite_prevue"])


class Migration(migrations.Migration):
    dependencies = [
        ("prescriptions", "0002_prescription_confirmation_automatique"),
    ]

    operations = [
        migrations.RunPython(resynchroniser, migrations.RunPython.noop),
    ]
