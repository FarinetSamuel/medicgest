"""
Crée les trois groupes métier utilisés comme rôles applicatifs.

Convention du projet : chaque utilisateur appartient à exactement un de
ces groupes (voir Utilisateur.role dans apps/utilisateurs/models.py).
"""

from django.db import migrations

NOMS_GROUPES = ["admin", "medecin", "patient"]


def creer_groupes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nom in NOMS_GROUPES:
        Group.objects.get_or_create(name=nom)


def supprimer_groupes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=NOMS_GROUPES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("utilisateurs", "0001_initial"),
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(creer_groupes, supprimer_groupes),
    ]
