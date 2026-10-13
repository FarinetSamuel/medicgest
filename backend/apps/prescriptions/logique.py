"""
Logique métier isolée du framework (facile à tester unitairement).
"""

import datetime

from django.db.models import Q, Sum
from django.utils import timezone

from .models import HoraireProgramme, Prescription, Prise


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


def synchroniser_quantite_prises_attendues(horaire, maintenant=None) -> int:
    """
    Reporte la quantité actuelle d'un HoraireProgramme sur ses Prise
    encore ATTENDUE et à venir.

    Les prises attendues sont générées à l'avance (generer_prises_attendues)
    avec quantite_prevue = horaire.quantite au moment de la génération, et
    la génération ne réécrit jamais une prise existante. Sans cette
    synchronisation, modifier la quantité d'un horaire laissait l'ancienne
    valeur sur les prises déjà générées — que la confirmation (automatique
    ou manuelle) recopie ensuite dans quantite_prise, d'où un décompte de
    stock erroné.

    Seules les prises futures sont concernées : une prise attendue dont
    l'heure est déjà passée relevait de l'ancienne posologie, et les prises
    déjà effectuées/oubliées/reportées constituent l'historique, jamais
    réécrit. .update() en masse volontaire : une prise ATTENDUE n'a aucun
    mouvement de stock, le signal post_save n'a donc rien à recalculer.
    """
    maintenant = maintenant or timezone.now()
    return (
        Prise.objects.filter(
            horaire_programme=horaire,
            statut=Prise.Statut.ATTENDUE,
            date_heure_prevue__gte=maintenant,
        )
        .exclude(quantite_prevue=horaire.quantite)
        .update(quantite_prevue=horaire.quantite)
    )


def supprimer_prises_attendues_hors_rythme(horaire, maintenant=None) -> int:
    """
    Supprime les Prise encore ATTENDUE et à venir d'un HoraireProgramme qui
    ne tombent plus sur un jour prévu par son rythme (intervalle_jours /
    date_reference).

    Les prises attendues étant générées à l'avance sur une fenêtre de
    plusieurs jours, passer un horaire de « tous les jours » à « tous les
    2 jours » laisserait sinon les prises quotidiennes déjà générées :
    rappels envoyés et, avec la confirmation automatique, stock décompté
    les jours où rien ne doit être pris.

    Seules les prises futures au statut ATTENDUE sont concernées : les
    prises effectuées/oubliées/reportées et les prises attendues déjà
    échues constituent l'historique, jamais réécrit. Les jours
    nouvellement prévus par le rythme sont créés par la prochaine
    exécution de generer_prises_attendues.
    """
    maintenant = maintenant or timezone.now()
    a_venir = Prise.objects.filter(
        horaire_programme=horaire,
        statut=Prise.Statut.ATTENDUE,
        date_heure_prevue__gte=maintenant,
    )
    hors_rythme = [
        prise.pk
        for prise in a_venir
        if not horaire.est_prevu_le(timezone.localtime(prise.date_heure_prevue).date())
    ]
    if not hors_rythme:
        return 0
    Prise.objects.filter(pk__in=hors_rythme).delete()
    return len(hors_rythme)


def supprimer_prises_attendues_a_venir(horaire, maintenant=None) -> int:
    """
    Supprime toutes les Prise encore ATTENDUE et à venir d'un
    HoraireProgramme supprimé ou désactivé.

    Les prises attendues étant générées à l'avance sur une fenêtre de
    plusieurs jours, supprimer un horaire (la clé étrangère
    Prise.horaire_programme passe alors à NULL) ou le désactiver laisserait
    sinon ses prises déjà générées : rappels envoyés et, avec la
    confirmation automatique, stock décompté pour un horaire qui n'existe
    plus.

    Seules les prises futures au statut ATTENDUE sont concernées : les
    prises effectuées/oubliées/reportées et les prises attendues déjà
    échues constituent l'historique, jamais réécrit. Si l'horaire est
    réactivé, ses prises sont recréées par la prochaine exécution de
    generer_prises_attendues.
    """
    maintenant = maintenant or timezone.now()
    nb_supprimees, _ = Prise.objects.filter(
        horaire_programme=horaire,
        statut=Prise.Statut.ATTENDUE,
        date_heure_prevue__gte=maintenant,
    ).delete()
    return nb_supprimees


def decaler_prises_attendues_a_la_nouvelle_heure(horaire, ancienne_heure, maintenant=None) -> int:
    """
    Reporte le changement d'heure d'un HoraireProgramme (de ancienne_heure
    à horaire.heure) sur ses Prise encore ATTENDUE et à venir.

    La génération à l'avance identifie une prise par (prescription, horaire,
    date_heure_prevue) : sans ce décalage, passer un horaire de 20:00 à
    21:00 laisserait les prises de 20:00 déjà générées, auxquelles la
    prochaine exécution de generer_prises_attendues ajouterait celles de
    21:00 — rappels en double et, avec la confirmation automatique, stock
    décompté deux fois par jour.

    La prise est déplacée le même jour plutôt que supprimée, pour ne pas
    laisser de trou jusqu'à la prochaine génération. Exception : si la
    nouvelle heure est déjà passée ce jour-là, la prise est supprimée — la
    déplacer dans le passé la ferait confirmer automatiquement à une heure
    où rien n'était prévu.

    Seules les prises futures au statut ATTENDUE et placées à l'ancienne
    heure sont concernées : une prise dont l'heure prévue a été modifiée
    individuellement n'est pas ramenée à l'heure de l'horaire, et un
    enregistrement de l'horaire sans changement d'heure ne déplace rien.
    .update() volontaire : une prise
    ATTENDUE n'a aucun mouvement de stock, le signal post_save n'a donc rien
    à recalculer.
    """
    maintenant = maintenant or timezone.now()
    # L'instance peut porter l'heure sous forme de chaîne ("20:00") si elle
    # n'a pas été relue depuis la base.
    heure = HoraireProgramme._meta.get_field("heure").to_python(horaire.heure)
    if heure == ancienne_heure:
        return 0
    a_venir = Prise.objects.filter(
        horaire_programme=horaire,
        statut=Prise.Statut.ATTENDUE,
        date_heure_prevue__gte=maintenant,
    )
    modifiees = 0
    for prise in a_venir:
        prevue_locale = timezone.localtime(prise.date_heure_prevue)
        if prevue_locale.time() != ancienne_heure:
            continue
        nouvelle = timezone.make_aware(datetime.datetime.combine(prevue_locale.date(), heure))
        if nouvelle < maintenant:
            prise.delete()
        else:
            Prise.objects.filter(pk=prise.pk).update(date_heure_prevue=nouvelle)
        modifiees += 1
    return modifiees


def supprimer_prises_attendues_hors_prescription(prescription, maintenant=None) -> int:
    """
    Supprime les Prise encore ATTENDUE et à venir d'une Prescription qui ne
    sont plus couvertes par elle : toutes si elle n'est plus active
    (arrêtée/terminée), sinon celles qui tombent hors de la période
    date_debut/date_fin.

    Les prises attendues étant générées à l'avance, arrêter une
    prescription ou avancer sa date de fin laisserait sinon les prises déjà
    générées : rappels envoyés et, avec la confirmation automatique, stock
    décompté pour un traitement arrêté.

    Seules les prises futures au statut ATTENDUE sont concernées : les
    prises effectuées/oubliées/reportées et les prises attendues déjà
    échues constituent l'historique, jamais réécrit. Si la prescription est
    réactivée ou sa période rallongée, les prises sont recréées par la
    prochaine exécution de generer_prises_attendues.
    """
    maintenant = maintenant or timezone.now()
    a_venir = Prise.objects.filter(
        prescription=prescription,
        statut=Prise.Statut.ATTENDUE,
        date_heure_prevue__gte=maintenant,
    )
    if prescription.statut == Prescription.Statut.ACTIVE:
        hors_periode = Q(date_heure_prevue__date__lt=prescription.date_debut)
        if prescription.date_fin:
            hors_periode |= Q(date_heure_prevue__date__gt=prescription.date_fin)
        a_venir = a_venir.filter(hors_periode)
    nb_supprimees, _ = a_venir.delete()
    return nb_supprimees
