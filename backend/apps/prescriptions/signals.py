"""
Reporte toute modification de l'heure, de la quantité ou du rythme d'un
HoraireProgramme, ainsi que sa désactivation ou sa suppression, sur ses
prises attendues à venir, quel que soit le chemin de modification (API,
admin Django via l'inline « Horaires » de la prescription, shell). Il en va
de même pour l'arrêt d'une Prescription ou le changement de sa période.

Auparavant la synchronisation n'était appelée que depuis
HoraireProgrammeViewSet.perform_update : une quantité modifiée via l'admin
Django laissait l'ancienne valeur sur les prises déjà générées, que la
confirmation recopiait ensuite dans quantite_prise (stock et rappels
erronés).
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .logique import (
    decaler_prises_attendues_a_la_nouvelle_heure,
    supprimer_prises_attendues_a_venir,
    supprimer_prises_attendues_hors_prescription,
    supprimer_prises_attendues_hors_rythme,
    synchroniser_quantite_prises_attendues,
)
from .models import HoraireProgramme, Prescription


@receiver(post_save, sender=HoraireProgramme)
def synchroniser_prises_a_la_sauvegarde_horaire(sender, instance, created, **kwargs):
    if created:
        # Aucune prise n'est encore rattachée à un horaire tout juste créé.
        return
    if not instance.actif:
        supprimer_prises_attendues_a_venir(instance)
        return
    supprimer_prises_attendues_hors_rythme(instance)
    decaler_prises_attendues_a_la_nouvelle_heure(instance)
    synchroniser_quantite_prises_attendues(instance)


@receiver(pre_delete, sender=HoraireProgramme)
def supprimer_prises_a_la_suppression_horaire(sender, instance, **kwargs):
    # pre_delete et non post_delete : après la suppression, la clé
    # étrangère Prise.horaire_programme (SET_NULL) est déjà vidée et les
    # prises de cet horaire ne sont plus identifiables.
    supprimer_prises_attendues_a_venir(instance)


@receiver(post_save, sender=Prescription)
def synchroniser_prises_a_la_sauvegarde_prescription(sender, instance, created, **kwargs):
    if created:
        # Aucune prise n'est encore rattachée à une prescription tout juste créée.
        return
    supprimer_prises_attendues_hors_prescription(instance)
