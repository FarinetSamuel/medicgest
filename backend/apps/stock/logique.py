"""
Logique métier du stock, isolée du framework pour rester testable
facilement et indépendante des vues/signaux qui l'appellent.
"""

import datetime
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

FENETRE_CONSOMMATION_JOURS = 14


def consommation_moyenne_par_jour(patient, medicament, jours: int = FENETRE_CONSOMMATION_JOURS) -> Decimal:
    """
    Moyenne journalière réellement consommée pour ce patient/médicament,
    calculée sur les `jours` derniers jours de prises effectivement
    prises (statut PRISE). Ce n'est PAS basé sur la fréquence théorique
    de la prescription : on mesure la consommation réelle, plus fiable.
    """
    from apps.prescriptions.models import Prise

    depuis = timezone.now() - datetime.timedelta(days=jours)
    total = (
        Prise.objects.filter(
            prescription__patient=patient,
            prescription__medicament=medicament,
            statut=Prise.Statut.PRISE,
            date_heure_reelle__gte=depuis,
        ).aggregate(total=Sum("quantite_prise"))["total"]
        or Decimal("0")
    )
    return total / jours


def jours_restants_estimes(patient, medicament):
    """
    Estimation du nombre de jours de stock restant, toutes boîtes actives
    de ce médicament confondues pour ce patient, d'après la consommation
    réelle récente. Retourne None si la consommation moyenne est nulle
    (pas d'historique ou traitement non encore commencé) — impossible
    d'estimer sans diviser par zéro, et une valeur inventée serait une
    approximation trompeuse.
    """
    from .models import Boite

    conso = consommation_moyenne_par_jour(patient, medicament)
    if conso <= 0:
        return None

    stock_total = (
        Boite.objects.filter(
            patient=patient, medicament=medicament, statut=Boite.Statut.ACTIVE
        ).aggregate(total=Sum("quantite_restante"))["total"]
        or Decimal("0")
    )
    return stock_total / conso


def appliquer_mouvement_stock(prise) -> None:
    """
    Recalcule entièrement l'effet d'une Prise sur le stock : annule
    d'abord ses mouvements précédents (le cas échéant), puis, si son
    statut est PRISE, décompte à nouveau selon la quantité actuelle —
    approche idempotente qui gère correctement aussi bien la création
    que la modification d'une Prise (changement de quantité, de statut,
    correction d'une erreur de saisie...).
    """
    from .models import Boite, MouvementStock

    _annuler_mouvements(prise)

    if prise.statut != prise.Statut.PRISE or not prise.quantite_prise:
        return

    patient = prise.prescription.patient
    medicament = prise.prescription.medicament
    a_decompter = prise.quantite_prise

    boites = Boite.objects.filter(
        patient=patient,
        medicament=medicament,
        statut=Boite.Statut.ACTIVE,
        quantite_restante__gt=0,
    ).order_by("date_peremption", "date_creation")

    for boite in boites:
        if a_decompter <= 0:
            break
        pris_sur_cette_boite = min(boite.quantite_restante, a_decompter)
        boite.quantite_restante -= pris_sur_cette_boite
        if boite.quantite_restante <= 0:
            boite.statut = Boite.Statut.EPUISEE
        boite.save(update_fields=["quantite_restante", "statut"])

        MouvementStock.objects.create(
            boite=boite,
            prise=prise,
            quantite=-pris_sur_cette_boite,
            motif="Décompte automatique suite à une prise enregistrée.",
        )
        a_decompter -= pris_sur_cette_boite

    # Si a_decompter > 0 ici : stock insuffisant pour couvrir la prise.
    # Pas d'erreur bloquante (cohérent avec la décision du palier 2 de ne
    # jamais bloquer l'enregistrement d'une prise) — l'alerte de stock
    # (en_alerte_quantite/jours) signalera de toute façon la situation.


def _annuler_mouvements(prise) -> None:
    """Réinjecte dans les boîtes concernées la quantité des mouvements existants de cette prise, puis les supprime."""
    from .models import Boite, MouvementStock

    for mouvement in MouvementStock.objects.filter(prise=prise).select_related("boite"):
        boite = mouvement.boite
        boite.quantite_restante -= mouvement.quantite  # quantite est négative : soustraire l'annule
        if boite.quantite_restante > 0 and boite.statut == Boite.Statut.EPUISEE:
            boite.statut = Boite.Statut.ACTIVE
        boite.save(update_fields=["quantite_restante", "statut"])
    MouvementStock.objects.filter(prise=prise).delete()
