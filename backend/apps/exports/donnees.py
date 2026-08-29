"""
Rassemble les données d'un patient nécessaires aux exports PDF/Excel, en
un seul endroit pour que les deux formats restent cohérents entre eux.
"""

import datetime

from django.utils import timezone

from apps.interactions.logique import verifier_interactions
from apps.patients.models import Patient
from apps.prescriptions.models import Prescription, Prise
from apps.stock.models import Boite

FENETRE_HISTORIQUE_JOURS = 30


def rassembler_donnees_patient(patient: Patient) -> dict:
    depuis = timezone.now() - datetime.timedelta(days=FENETRE_HISTORIQUE_JOURS)

    prescriptions_actives = (
        Prescription.objects.filter(patient=patient, statut=Prescription.Statut.ACTIVE)
        .select_related("medicament", "medecin_prescripteur")
        .order_by("-date_debut")
    )

    historique_prises = (
        Prise.objects.filter(
            prescription__patient=patient,
            statut=Prise.Statut.PRISE,
            date_heure_reelle__gte=depuis,
        )
        .select_related("prescription__medicament")
        .order_by("-date_heure_reelle")
    )

    boites_actives = (
        Boite.objects.filter(patient=patient, statut=Boite.Statut.ACTIVE)
        .select_related("medicament")
        .order_by("medicament__denomination")
    )

    return {
        "patient": patient,
        "date_generation": timezone.now(),
        "fenetre_historique_jours": FENETRE_HISTORIQUE_JOURS,
        "prescriptions_actives": list(prescriptions_actives),
        "historique_prises": list(historique_prises),
        "boites_actives": list(boites_actives),
        "interactions": verifier_interactions(patient),
    }
