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
    Crée un rappel in_app pour chaque Prise ATTENDUE dont l'heure prévue
    tombe dans les `fenetre_minutes` prochaines minutes et qui n'a pas déjà
    de rappel associé (évite les doublons si la commande est relancée
    plusieurs fois avant l'heure prévue).

    Le canal in_app reste un rappel par prise (chacun peut être marqué lu
    séparément), mais l'e-mail est regroupé : un seul e-mail par
    destinataire, listant toutes ses prises à venir détectées lors de cet
    appel, plutôt qu'un e-mail par prise.
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
    lignes_par_destinataire: dict = {}
    for prise in prises_a_notifier:
        patient = prise.prescription.patient
        medicament = prise.prescription.medicament
        heure = timezone.localtime(prise.date_heure_prevue).strftime("%H:%M")
        quantite = prise.quantite_prevue or prise.prescription.dose_quantite
        unite = prise.prescription.dose_unite
        titre = f"Rappel de prise : {medicament.denomination}"
        message = (
            f"N'oubliez pas votre prise de {medicament.denomination} "
            f"({quantite} {unite}) prévue à {heure}."
        )
        creees.append(
            Notification.objects.create(
                destinataire=patient.utilisateur,
                canal=Notification.Canal.IN_APP,
                categorie=Notification.Categorie.RAPPEL_PRISE,
                titre=titre,
                message=message,
                prise=prise,
            )
        )
        lignes_par_destinataire.setdefault(patient.utilisateur, []).append(
            f"- {medicament.denomination} ({quantite} {unite}) à {heure}"
        )

    for destinataire, lignes in lignes_par_destinataire.items():
        titre = "Rappel de prise" if len(lignes) == 1 else f"Rappel de {len(lignes)} prises"
        message = "Prises à venir :\n\n" + "\n".join(lignes)
        creees.append(
            Notification.objects.create(
                destinataire=destinataire,
                canal=Notification.Canal.EMAIL,
                categorie=Notification.Categorie.RAPPEL_PRISE,
                titre=titre,
                message=message,
            )
        )
    return creees


def generer_alertes_stock(delai_relance_heures: int = 24) -> list[Notification]:
    """
    Crée une alerte in_app pour chaque Boite active en_alerte, à
    destination du/des destinataire(s) choisi(s) pour ce patient (voir
    _destinataires_alerte_stock), sauf si CE destinataire a déjà été
    notifié pour cette boîte il y a moins de `delai_relance_heures` —
    évite de spammer à chaque exécution de la commande (typiquement
    quotidienne ou plus fréquente). La relance est vérifiée par
    destinataire (et non plus globalement par boîte) : si la préférence
    passe de "patient" à "les_deux", le médecin nouvellement ajouté doit
    quand même recevoir une première alerte immédiatement.

    Comme pour les rappels de prise, l'e-mail est regroupé : un seul par
    destinataire couvrant toutes ses boîtes en alerte détectées lors de
    cet appel, plutôt qu'un e-mail par boîte.
    """
    limite_relance = timezone.now() - datetime.timedelta(hours=delai_relance_heures)

    boites_actives = Boite.objects.filter(statut=Boite.Statut.ACTIVE).select_related(
        "patient__utilisateur", "medicament"
    )

    creees = []
    lignes_par_destinataire: dict = {}
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

            creees.append(
                Notification.objects.create(
                    destinataire=destinataire,
                    canal=Notification.Canal.IN_APP,
                    categorie=Notification.Categorie.ALERTE_STOCK,
                    titre=titre,
                    message=message,
                    boite=boite,
                )
            )
            lignes_par_destinataire.setdefault(destinataire, []).append(
                f"- {boite.medicament.denomination} : {', '.join(details)}"
            )

    for destinataire, lignes in lignes_par_destinataire.items():
        titre = "Stock bas" if len(lignes) == 1 else f"Stock bas ({len(lignes)} médicaments)"
        message = "Les stocks suivants sont bas :\n\n" + "\n".join(lignes)
        creees.append(
            Notification.objects.create(
                destinataire=destinataire,
                canal=Notification.Canal.EMAIL,
                categorie=Notification.Categorie.ALERTE_STOCK,
                titre=titre,
                message=message,
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

    Comme pour generer_alertes_stock, l'e-mail est regroupé par
    destinataire plutôt qu'envoyé une fois par prescription en rupture.
    """
    limite_relance = timezone.now() - datetime.timedelta(hours=delai_relance_heures)

    prescriptions_actives = Prescription.objects.filter(
        statut=Prescription.Statut.ACTIVE
    ).select_related("patient__utilisateur", "medicament")

    creees = []
    lignes_par_destinataire: dict = {}
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

            creees.append(
                Notification.objects.create(
                    destinataire=destinataire,
                    canal=Notification.Canal.IN_APP,
                    categorie=Notification.Categorie.ALERTE_STOCK,
                    titre=titre,
                    message=message,
                    prescription=prescription,
                )
            )
            lignes_par_destinataire.setdefault(destinataire, []).append(
                f"- {prescription.medicament.denomination} : aucune boîte enregistrée"
            )

    for destinataire, lignes in lignes_par_destinataire.items():
        titre = "Rupture de stock" if len(lignes) == 1 else f"Rupture de stock ({len(lignes)} médicaments)"
        message = "Aucune boîte n'est enregistrée pour les prescriptions actives suivantes :\n\n" + "\n".join(
            lignes
        )
        creees.append(
            Notification.objects.create(
                destinataire=destinataire,
                canal=Notification.Canal.EMAIL,
                categorie=Notification.Categorie.ALERTE_STOCK,
                titre=titre,
                message=message,
            )
        )
    return creees
