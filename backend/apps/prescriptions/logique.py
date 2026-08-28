"""
Logique métier isolée du framework (facile à tester unitairement).
"""

from django.db.models import Sum

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
