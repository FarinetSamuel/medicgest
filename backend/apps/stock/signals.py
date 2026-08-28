"""
Connecte le cycle de vie des Prise (app prescriptions) au stock, SANS que
l'app prescriptions ait besoin de connaître l'existence de l'app stock —
c'est le stock qui s'abonne aux événements, pas l'inverse. Permet de
retirer/désactiver le module stock plus tard sans toucher prescriptions.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.prescriptions.models import Prise

from .logique import _annuler_mouvements, appliquer_mouvement_stock


@receiver(post_save, sender=Prise)
def gerer_stock_a_la_sauvegarde_prise(sender, instance, **kwargs):
    appliquer_mouvement_stock(instance)


@receiver(pre_delete, sender=Prise)
def gerer_stock_a_la_suppression_prise(sender, instance, **kwargs):
    # pre_delete (pas post_delete) : la relation MouvementStock.prise
    # (on_delete=SET_NULL) est déjà détachée par Django AVANT que le
    # signal post_delete ne soit envoyé, ce qui empêcherait de retrouver
    # les mouvements à annuler. En pre_delete, la relation est encore
    # intacte.
    _annuler_mouvements(instance)
