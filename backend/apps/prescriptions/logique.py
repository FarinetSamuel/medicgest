"""
Logique métier isolée du framework (facile à tester unitairement).
"""

from django.db.models import Sum
from django.utils import timezone

from .models import Prescription, Prise


def calculer_alerte_depassement(prise: Prise) -> bool:
    """
    Vrai si cette prise, cumulée aux autres prises 'prise' du même jour
    pour la même prescription 'réserve', dépasse dose_max_par_jour.

    Ne s'applique qu'aux prescriptions de type RESERVE avec un plafond
    défini ; sinon retourne toujours False (pas d'alerte).
    """
    prescription = prise.prescription
    if prescription.type_prise != Prescription.TypePrise.RESERVE:
        return False
    if prescription.dose_max_par_jour is None:
        return False
    if prise.statut != Prise.Statut.PRISE or prise.date_heure_reelle is None:
        return False

    jour = prise.date_heure_reelle.date()
    total_autres = (
        Prise.objects.filter(
            prescription=prescription,
            statut=Prise.Statut.PRISE,
            date_heure_reelle__date=jour,
        )
        .exclude(pk=prise.pk)
        .aggregate(total=Sum("quantite_prise"))["total"]
        or 0
    )
    total = total_autres + (prise.quantite_prise or 0)
    return total > prescription.dose_max_par_jour


def confirmer_prises_automatiques(maintenant=None) -> list[Prise]:
    """
    Bascule en 'prise' toute Prise ATTENDUE dont l'heure prévue est
    atteinte, pour les prescriptions régulières dont l'option
    confirmation_automatique est activée (valeur par défaut).

    Décision validée avec le porteur du projet : le basculement a lieu dès
    que l'heure prévue est atteinte, sans délai de grâce — pour laisser une
    chance à une confirmation manuelle préalable, exécuter cette commande
    à une cadence adaptée (voir README, section cron). Quand l'option est
    désactivée, la prise n'est JAMAIS basculée automatiquement : elle
    reste 'attendue' indéfiniment jusqu'à une action manuelle (pas de
    passage auto en 'oubliée').

    Sauvegarde chaque Prise individuellement (plutôt qu'un .update() en
    masse) pour déclencher le signal post_save qui décompte le stock
    (apps.stock.signals) — le stock n'est donc décrémenté qu'au moment où
    la prise est réellement considérée comme effectuée, pas dès sa
    génération à l'avance.
    """
    maintenant = maintenant or timezone.now()
    prises_a_confirmer = Prise.objects.filter(
        statut=Prise.Statut.ATTENDUE,
        date_heure_prevue__lte=maintenant,
        prescription__type_prise=Prescription.TypePrise.REGULIERE,
        prescription__confirmation_automatique=True,
    ).select_related("prescription")

    confirmees = []
    for prise in prises_a_confirmer:
        prise.statut = Prise.Statut.PRISE
        prise.date_heure_reelle = prise.date_heure_prevue
        prise.quantite_prise = prise.quantite_prevue
        if not prise.commentaire:
            prise.commentaire = "Confirmée automatiquement (option activée sur la prescription)."
        prise.save()
        confirmees.append(prise)
    return confirmees
