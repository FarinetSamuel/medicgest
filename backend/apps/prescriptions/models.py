import uuid

from django.conf import settings
from django.db import models

from apps.medicaments.models import Medicament
from apps.patients.models import Patient


class Prescription(models.Model):
    """
    Prescription d'un médicament à un patient.

    type_prise distingue deux logiques très différentes :
    - 'reguliere' : horaires fixes, définis via HoraireProgramme, dont les
      prises attendues sont générées à l'avance (voir Prise).
    - 'reserve' : usage ponctuel ("au besoin"/PRN), pas d'horaire fixe,
      chaque prise est enregistrée librement par le patient. Un plafond
      journalier optionnel (dose_max_par_jour) peut être défini ; s'il est
      dépassé, la prise est quand même enregistrée mais signalée par une
      alerte (décision validée avec le porteur du projet — pas de blocage
      à ce stade).
    """

    class TypePrise(models.TextChoices):
        REGULIERE = "reguliere", "Régulière (horaires fixes)"
        RESERVE = "reserve", "Réserve (usage ponctuel)"

    class Statut(models.TextChoices):
        ACTIVE = "active", "Active"
        ARRETEE = "arretee", "Arrêtée"
        TERMINEE = "terminee", "Terminée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="prescriptions")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT, related_name="prescriptions")
    medecin_prescripteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prescriptions_redigees"
    )

    type_prise = models.CharField(max_length=20, choices=TypePrise.choices)
    dose_quantite = models.DecimalField(max_digits=6, decimal_places=2)
    dose_unite = models.CharField(max_length=30, help_text="Ex. : comprimé, ml, mg")
    frequence_par_jour = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Nombre de prises par jour (prescriptions régulières).",
    )
    dose_max_par_jour = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Plafond journalier pour une prescription 'réserve' (déclenche une alerte si dépassé).",
    )

    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True, help_text="Vide = traitement en cours.")
    instructions = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIVE)

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"
        ordering = ["-date_debut"]

    def __str__(self):
        return f"{self.medicament} pour {self.patient} ({self.get_type_prise_display()})"


class HoraireProgramme(models.Model):
    """
    Horaire fixe d'une prescription régulière (ex. : 08:00, 20:00).
    Sert de patron pour générer les Prise attendues à l'avance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="horaires"
    )
    heure = models.TimeField()
    quantite = models.DecimalField(max_digits=6, decimal_places=2)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Horaire programmé"
        verbose_name_plural = "Horaires programmés"
        ordering = ["heure"]

    def __str__(self):
        return f"{self.prescription} à {self.heure}"


class Prise(models.Model):
    """
    Une prise, attendue et/ou effectuée.

    Décision validée : pour les prescriptions régulières, les prises
    attendues sont générées À L'AVANCE (statut ATTENDUE, date_heure_prevue
    renseignée) par la commande `generer_prises_attendues`, plutôt que
    calculées à la volée — cela permet d'afficher un vrai calendrier.

    Quand la prise a réellement lieu, la même ligne est mise à jour
    (date_heure_reelle, quantite_prise, statut='prise') plutôt que d'en
    créer une nouvelle — évite la duplication attendue/effectuée.

    Pour une prescription 'réserve', il n'y a pas de ligne ATTENDUE
    préalable : la ligne est créée directement au statut PRISE au moment
    de l'enregistrement.
    """

    class Statut(models.TextChoices):
        ATTENDUE = "attendue", "Attendue"
        PRISE = "prise", "Prise"
        OUBLIEE = "oubliee", "Oubliée"
        REPORTEE = "reportee", "Reportée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="prises")
    horaire_programme = models.ForeignKey(
        HoraireProgramme, on_delete=models.SET_NULL, null=True, blank=True, related_name="prises"
    )

    date_heure_prevue = models.DateTimeField(null=True, blank=True)
    date_heure_reelle = models.DateTimeField(null=True, blank=True)
    quantite_prevue = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    quantite_prise = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ATTENDUE)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prises_enregistrees",
    )
    # Décision validée : une prise 'réserve' qui dépasse le plafond
    # journalier de la prescription est quand même enregistrée, mais
    # signalée par cette alerte (pas de blocage à ce stade).
    alerte_depassement = models.BooleanField(default=False)
    commentaire = models.TextField(blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prise"
        verbose_name_plural = "Prises"
        ordering = ["-date_heure_prevue", "-date_heure_reelle"]

    def __str__(self):
        moment = self.date_heure_reelle or self.date_heure_prevue
        return f"{self.prescription} — {self.get_statut_display()} ({moment})"
