"""
Reporte toute modification de la quantité d'un HoraireProgramme sur ses
prises attendues à venir, quel que soit le chemin de modification (API,
admin Django via l'inline « Horaires » de la prescription, shell).

Auparavant la synchronisation n'était appelée que depuis
HoraireProgrammeViewSet.perform_update : une quantité modifiée via l'admin
Django laissait l'ancienne valeur sur les prises déjà générées, que la
confirmation recopiait ensuite dans quantite_prise (stock et rappels
erronés).
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .logique import synchroniser_quantite_prises_attendues
from .models import HoraireProgramme


@receiver(post_save, sender=HoraireProgramme)
def synchroniser_prises_a_la_sauvegarde_horaire(sender, instance, created, **kwargs):
    if created:
        # Aucune prise n'est encore rattachée à un horaire tout juste créé.
        return
    synchroniser_quantite_prises_attendues(instance)
