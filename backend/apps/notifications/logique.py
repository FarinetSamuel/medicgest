"""
Détection des situations qui doivent déclencher une notification, et
création des Notification correspondantes (sans les envoyer directement —
voir canaux.envoyer_notification, appelé séparément par les commandes).
"""

import datetime

from django.conf import settings
from django.utils import timezone

from apps.prescriptions.models import Prescription, Prise
from apps.stock.models import Boite

from .models import Notification


def _destinataires_alerte_stock(patient) -> list:
    """
    Qui doit recevoir une alerte de stock pour ce patient, selon sa
    préférence `preference_alerte_stock` (choix laissé au patient — voir
    apps.patients.models.Patient et PatientViewSet.preference_alerte_stock).
    """
    from apps.patients.models import Patient

    pref = patient.preference_alerte_stock
    destinataires = []
    if pref in (Patient.PreferenceAlerteStock.PATIENT, Patient.PreferenceAlerteStock.LES_DEUX):
        destinataires.append(patient.utilisateur)
    if pref in (Patient.PreferenceAlerteStock.MEDECIN, Patient.PreferenceAlerteStock.LES_DEUX):
        destinataires.extend(
            suivi.medecin
            for suivi in patient.medecins_suivi.filter(actif=True).select_related("medecin")
        )
    return destinataires


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
    Crée une alerte (in_app + email) pour chaque Boite active en_alerte, à
    destination du/des destinataire(s) choisi(s) pour ce patient (voir
    _destinataires_alerte_stock), sauf si CE destinataire a déjà été
    notifié pour cette boîte il y a moins de `delai_relance_heures` —
    évite de spammer à chaque exécution de la commande (typiquement
    quotidienne ou plus fréquente). La relance est vérifiée par
    destinataire (et non plus globalement par boîte) : si la préférence
    passe de "patient" à "les_deux", le médecin nouvellement ajouté doit
    quand même recevoir une première alerte immédiatement.
    """
    limite_relance = timezone.now() - datetime.timedelta(hours=delai_relance_heures)

    boites_actives = Boite.objects.filter(statut=Boite.Statut.ACTIVE).select_related(
        "patient__utilisateur", "medicament"
    )

    creees = []
    for boite in boites_actives:
        if not boite.en_alerte:
            continue

        titre = f"Stock bas : {boite.medicament.denomination}"
        details = []
        if boite.en_alerte_quantite:
            details.append(f"{boite.quantite_restante} unité(s) restante(s)")
        if boite.en_alerte_jours:
            details.append("stock estimé bientôt épuisé selon la consommation récente")
        message = f"Le stock de {boite.medicament.denomination} est bas : {', '.join(details)}."

        for destinataire in _destinataires_alerte_stock(boite.patient):
            derniere_alerte = boite.notifications.filter(
                categorie=Notification.Categorie.ALERTE_STOCK, destinataire=destinataire
            ).order_by("-date_creation").first()
            if derniere_alerte and derniere_alerte.date_creation > limite_relance:
                continue

            for canal in (Notification.Canal.IN_APP, Notification.Canal.EMAIL):
                creees.append(
                    Notification.objects.create(
                        destinataire=destinataire,
                        canal=canal,
                        categorie=Notification.Categorie.ALERTE_STOCK,
                        titre=titre,
                        message=message,
                        boite=boite,
                    )
                )
    return creees


def generer_alertes_rupture_stock(delai_relance_heures: int = 24) -> list[Notification]:
    """
    Crée une alerte "rupture de stock" pour chaque prescription active
    (régulière ou réserve) dont le patient n'a AUCUNE boîte active de ce
    médicament — cas non couvert par generer_alertes_stock, qui ne
    parcourt que les Boite déjà existantes et ne peut donc jamais
    détecter une absence totale de boîte.
    """
    limite_relance = timezone.now() - datetime.timedelta(hours=delai_relance_heures)

    prescriptions_actives = Prescription.objects.filter(
        statut=Prescription.Statut.ACTIVE
    ).select_related("patient__utilisateur", "medicament")

    creees = []
    for prescription in prescriptions_actives:
        a_du_stock = Boite.objects.filter(
            patient=prescription.patient,
            medicament=prescription.medicament,
            statut=Boite.Statut.ACTIVE,
        ).exists()
        if a_du_stock:
            continue

        titre = f"Rupture de stock : {prescription.medicament.denomination}"
        message = (
            f"Aucune boîte de {prescription.medicament.denomination} n'est enregistrée "
            "alors que la prescription est active."
        )

        for destinataire in _destinataires_alerte_stock(prescription.patient):
            derniere_alerte = prescription.notifications.filter(
                categorie=Notification.Categorie.ALERTE_STOCK, destinataire=destinataire
            ).order_by("-date_creation").first()
            if derniere_alerte and derniere_alerte.date_creation > limite_relance:
                continue

            for canal in (Notification.Canal.IN_APP, Notification.Canal.EMAIL):
                creees.append(
                    Notification.objects.create(
                        destinataire=destinataire,
                        canal=canal,
                        categorie=Notification.Categorie.ALERTE_STOCK,
                        titre=titre,
                        message=message,
                        prescription=prescription,
                    )
                )
    return creees
