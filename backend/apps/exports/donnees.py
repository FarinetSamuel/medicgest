"""
Rassemble les données d'un patient nécessaires aux exports PDF/Excel, en
un seul endroit pour que les deux formats restent cohérents entre eux.
"""

import datetime
from collections import defaultdict
from decimal import Decimal
from itertools import groupby

from django.utils import timezone

from apps.interactions.logique import verifier_interactions
from apps.patients.models import Patient
from apps.prescriptions.models import Prescription, Prise
from apps.stock.models import Boite

FENETRE_HISTORIQUE_JOURS = 30

# Contenus proposés pour le PDF (paramètre ?contenu= de l'export).
CONTENU_COMPLET = "complet"
CONTENU_PRESCRIPTIONS = "prescriptions"
CONTENU_PRISES = "prises"
CONTENU_STOCK = "stock"
CONTENU_A_VENIR = "a_venir"
CONTENUS = (
    CONTENU_COMPLET,
    CONTENU_PRESCRIPTIONS,
    CONTENU_PRISES,
    CONTENU_STOCK,
    CONTENU_A_VENIR,
)


def nom_affiche(utilisateur) -> str:
    return utilisateur.get_full_name() or utilisateur.email


def _prescriptions_par_medecin(patient, medecin_id, inclure_inactives) -> list[dict]:
    """
    Prescriptions du patient regroupées par médecin prescripteur,
    éventuellement restreintes à un seul médecin. Par défaut seules les
    prescriptions actives sont retenues.
    """
    prescriptions = (
        Prescription.objects.filter(patient=patient)
        .select_related("medicament", "medecin_prescripteur")
        .prefetch_related("horaires")
        .order_by(
            "medecin_prescripteur__last_name",
            "medecin_prescripteur__first_name",
            "medecin_prescripteur__email",
            "-date_debut",
        )
    )
    if not inclure_inactives:
        prescriptions = prescriptions.filter(statut=Prescription.Statut.ACTIVE)
    if medecin_id:
        prescriptions = prescriptions.filter(medecin_prescripteur_id=medecin_id)

    groupes = []
    for _, groupe in groupby(prescriptions, key=lambda p: p.medecin_prescripteur_id):
        groupe = list(groupe)
        groupes.append(
            {"medecin": nom_affiche(groupe[0].medecin_prescripteur), "prescriptions": groupe}
        )
    return groupes


def _resume_prises(prises) -> list[dict]:
    """Nombre de prises et quantité totale par médicament (et unité de dose)."""
    totaux = defaultdict(lambda: {"nombre": 0, "quantite": Decimal("0")})
    for prise in prises:
        cle = (prise.prescription.medicament.denomination, prise.prescription.dose_unite)
        totaux[cle]["nombre"] += 1
        totaux[cle]["quantite"] += prise.quantite_prise or Decimal("0")
    return [
        {"medicament": medicament, "unite": unite, **valeurs}
        for (medicament, unite), valeurs in sorted(totaux.items())
    ]


def rassembler_donnees_patient(
    patient: Patient,
    date_debut: datetime.date | None = None,
    date_fin: datetime.date | None = None,
    medecin_id=None,
    inclure_inactives: bool = False,
) -> dict:
    """
    date_debut/date_fin (bornes incluses, à fournir ensemble) délimitent
    l'historique des prises ; sans elles, il couvre les
    FENETRE_HISTORIQUE_JOURS derniers jours. medecin_id et
    inclure_inactives ne concernent que prescriptions_par_medecin.
    """
    if date_debut and date_fin:
        periode = {
            "date_heure_reelle__date__gte": date_debut,
            "date_heure_reelle__date__lte": date_fin,
        }
    else:
        periode = {
            "date_heure_reelle__gte": timezone.now()
            - datetime.timedelta(days=FENETRE_HISTORIQUE_JOURS)
        }

    prescriptions_actives = (
        Prescription.objects.filter(patient=patient, statut=Prescription.Statut.ACTIVE)
        .select_related("medicament", "medecin_prescripteur")
        .order_by("-date_debut")
    )

    historique_prises = (
        Prise.objects.filter(
            prescription__patient=patient,
            statut=Prise.Statut.PRISE,
            **periode,
        )
        .select_related("prescription__medicament")
        .order_by("-date_heure_reelle")
    )

    boites_actives = (
        Boite.objects.filter(patient=patient, statut=Boite.Statut.ACTIVE)
        .select_related("medicament")
        .order_by("medicament__denomination")
    )

    historique_prises = list(historique_prises)

    return {
        "patient": patient,
        "date_generation": timezone.now(),
        "fenetre_historique_jours": FENETRE_HISTORIQUE_JOURS,
        "periode_debut": date_debut if date_debut and date_fin else None,
        "periode_fin": date_fin if date_debut and date_fin else None,
        "prescriptions_actives": list(prescriptions_actives),
        "prescriptions_par_medecin": _prescriptions_par_medecin(
            patient, medecin_id, inclure_inactives
        ),
        "inclure_inactives": inclure_inactives,
        "historique_prises": historique_prises,
        "resume_prises": _resume_prises(historique_prises),
        "boites_actives": list(boites_actives),
        "interactions": verifier_interactions(patient),
    }


def rassembler_besoins_a_venir(
    patient: Patient, date_debut: datetime.date, date_fin: datetime.date, maintenant=None
) -> dict:
    """
    Prises prévues sur une période à venir (bornes incluses) et stock
    correspondant, par médicament — la « liste de vacances » : ce qu'il
    faut emporter, et ce qui manquera.

    Les prises sont calculées à partir des horaires programmés (heure,
    quantité, rythme) et non des Prise déjà générées : celles-ci ne
    couvrent que la fenêtre de generer_prises_attendues (30 jours), alors
    que la période demandée peut aller au-delà. Seules les prises dont
    l'heure n'est pas encore passée sont comptées.

    Par médicament :
    - quantite_avant : consommation prévue d'ici le début de la période ;
    - stock_au_debut : stock actuel (boîtes actives) moins quantite_avant,
      jamais négatif ;
    - quantite : besoin sur la période ;
    - reste / manque : ce qui restera à la fin, ou ce qui manquera.

    Les prescriptions « réserve » n'ont pas d'horaire : leur consommation
    n'est pas prévisible et n'est jamais estimée. Elles sont listées à
    part avec leur stock actuel.
    """
    maintenant = maintenant or timezone.now()
    aujourdhui = timezone.localtime(maintenant).date()
    date_debut = max(date_debut, aujourdhui)

    prescriptions = (
        Prescription.objects.filter(patient=patient, statut=Prescription.Statut.ACTIVE)
        .select_related("medicament")
        .prefetch_related("horaires")
        .order_by("medicament__denomination")
    )

    stocks = defaultdict(lambda: Decimal("0"))
    boites_actives = Boite.objects.filter(
        patient=patient, statut=Boite.Statut.ACTIVE
    ).select_related("medicament")
    for boite in boites_actives:
        stocks[boite.medicament_id] += boite.quantite_restante

    besoins = {}
    reserves = []
    for prescription in prescriptions:
        if prescription.type_prise != Prescription.TypePrise.REGULIERE:
            reserves.append(
                {"prescription": prescription, "stock": stocks[prescription.medicament_id]}
            )
            continue

        besoin = besoins.setdefault(
            prescription.medicament_id,
            {
                "medicament": prescription.medicament.denomination,
                "unite": prescription.dose_unite,
                "nombre": 0,
                "quantite": Decimal("0"),
                "quantite_avant": Decimal("0"),
                "stock": stocks[prescription.medicament_id],
            },
        )
        jour = aujourdhui
        while jour <= date_fin:
            dans_la_prescription = jour >= prescription.date_debut and (
                prescription.date_fin is None or jour <= prescription.date_fin
            )
            if dans_la_prescription:
                for horaire in prescription.horaires.all():
                    if not horaire.actif or not horaire.est_prevu_le(jour):
                        continue
                    prevue = timezone.make_aware(datetime.datetime.combine(jour, horaire.heure))
                    if prevue < maintenant:
                        continue
                    if jour < date_debut:
                        besoin["quantite_avant"] += horaire.quantite
                    else:
                        besoin["nombre"] += 1
                        besoin["quantite"] += horaire.quantite
            jour += datetime.timedelta(days=1)

    for besoin in besoins.values():
        besoin["stock_au_debut"] = max(besoin["stock"] - besoin["quantite_avant"], Decimal("0"))
        ecart = besoin["stock_au_debut"] - besoin["quantite"]
        besoin["reste"] = max(ecart, Decimal("0"))
        besoin["manque"] = max(-ecart, Decimal("0"))

    return {
        "periode_debut": date_debut,
        "periode_fin": date_fin,
        "besoins": sorted(besoins.values(), key=lambda b: b["medicament"]),
        "reserves": reserves,
        "boites_perimees_avant_la_fin": [
            boite
            for boite in boites_actives
            if boite.date_peremption and boite.date_peremption <= date_fin
        ],
    }
