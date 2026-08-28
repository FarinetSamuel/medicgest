"""
Détection des situations qui doivent déclencher une notification, et
création des Notification correspondantes (sans les envoyer directement —
voir canaux.envoyer_notification, appelé séparément par les commandes).
"""

import datetime

from django.conf import settings
from django.utils import timezone

from apps.prescriptions.models import Prise
from apps.stock.models import Boite

from .models import Notification


def generer_rappels_prises_a_venir(fenetre_minutes: int | None = None) -> list[Notification]:
    """
    Crée un rappel (in_app + email) pour chaque Prise ATTENDUE dont
    l'heure prévue tombe dans les `fenetre_minutes` prochaines minutes et
    qui n'a pas déjà de rappel associé (évite les doublons si la commande
    est relancée plusieurs fois avant l'heure prévue).
    """
    fenetre_minutes = fenetre_minutes or getattr(settings, "RAPPEL_PRISE_FENETRE_MINUTES", 15)
    maintenant = timezone.now()
    limite = maintenant + datetime.timedelta(minutes=fenetre_minutes)

    prises_a_notifier = (
        Prise.objects.filter(
            statut=Prise.Statut.ATTENDUE,
            date_heure_prevue__gte=maintenant,
            date_heure_prevue__lte=limite,
        )
        .exclude(notifications__categorie=Notification.Categorie.RAPPEL_PRISE)
        .select_related("prescription__patient__utilisateur", "prescription__medicament")
    )

    creees = []
    for prise in prises_a_notifier:
        patient = prise.prescription.patient
        medicament = prise.prescription.medicament
        titre = f"Rappel de prise : {medicament.denomination}"
        message = (
            f"N'oubliez pas votre prise de {medicament.denomination} "
            f"({prise.quantite_prevue or prise.prescription.dose_quantite} "
            f"{prise.prescription.dose_unite}) prévue à "
            f"{timezone.localtime(prise.date_heure_prevue).strftime('%H:%M')}."
        )
        for canal in (Notification.Canal.IN_APP, Notification.Canal.EMAIL):
            creees.append(
                Notification.objects.create(
                    destinataire=patient.utilisateur,
                    canal=canal,
                    categorie=Notification.Categorie.RAPPEL_PRISE,
                    titre=titre,
                    message=message,
                    prise=prise,
                )
            )
    return creees


def generer_alertes_stock(delai_relance_heures: int = 24) -> list[Notification]:
    """
    Crée une alerte (in_app + email) pour chaque Boite active en_alerte,
    sauf si une alerte a déjà été notifiée pour cette boîte il y a moins
    de `delai_relance_heures` — évite de spammer le patient à chaque
    exécution de la commande (typiquement quotidienne ou plus fréquente).
    """
    limite_relance = timezone.now() - datetime.timedelta(hours=delai_relance_heures)

    boites_actives = Boite.objects.filter(statut=Boite.Statut.ACTIVE).select_related(
        "patient__utilisateur", "medicament"
    )

    creees = []
    for boite in boites_actives:
        if not boite.en_alerte:
            continue

        derniere_alerte = boite.notifications.filter(
            categorie=Notification.Categorie.ALERTE_STOCK
        ).order_by("-date_creation").first()
        if derniere_alerte and derniere_alerte.date_creation > limite_relance:
            continue

        titre = f"Stock bas : {boite.medicament.denomination}"
        details = []
        if boite.en_alerte_quantite:
            details.append(f"{boite.quantite_restante} unité(s) restante(s)")
        if boite.en_alerte_jours:
            details.append("stock estimé bientôt épuisé selon la consommation récente")
        message = f"Le stock de {boite.medicament.denomination} est bas : {', '.join(details)}."

        for canal in (Notification.Canal.IN_APP, Notification.Canal.EMAIL):
            creees.append(
                Notification.objects.create(
                    destinataire=boite.patient.utilisateur,
                    canal=canal,
                    categorie=Notification.Categorie.ALERTE_STOCK,
                    titre=titre,
                    message=message,
                    boite=boite,
                )
            )
    return creees
