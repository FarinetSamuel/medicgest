import uuid

from django.conf import settings
from django.db import models


class Patient(models.Model):
    """
    Un patient suivi dans l'application.

    Décision validée : tout patient possède un compte Utilisateur
    (relation OneToOne obligatoire, pas de patient "fantôme" sans compte).
    """

    class Sexe(models.TextChoices):
        FEMININ = "F", "Féminin"
        MASCULIN = "M", "Masculin"
        AUTRE = "A", "Autre / non précisé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fiche_patient",
        help_text="Compte utilisateur associé (obligatoire).",
    )
    numero_dossier = models.CharField(max_length=32, unique=True)
    date_naissance = models.DateField()
    sexe = models.CharField(max_length=1, choices=Sexe.choices)

    # --- Contact d'urgence (facultatif) ---
    contact_urgence_nom = models.CharField(max_length=150, blank=True)
    contact_urgence_telephone = models.CharField(max_length=20, blank=True)
    contact_urgence_lien = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex. : conjoint, enfant, aidant...",
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["numero_dossier"]

    def __str__(self):
        return f"{self.utilisateur.get_full_name()} (dossier {self.numero_dossier})"


class NoteMedicale(models.Model):
    """
    Notes médicales structurées d'un patient.

    Décision validée : les notes sont structurées par catégorie plutôt
    qu'un unique champ de texte libre, pour permettre plus tard des
    filtres/recherches fiables (ex. : alerter sur une allergie précise
    lors d'une prescription).
    """

    class Categorie(models.TextChoices):
        ALLERGIE = "allergie", "Allergie"
        ANTECEDENT = "antecedent", "Antécédent médical"
        OBSERVATION = "observation", "Observation générale"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="notes_medicales"
    )
    categorie = models.CharField(max_length=20, choices=Categorie.choices)
    contenu = models.TextField()
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notes_saisies",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Note médicale"
        verbose_name_plural = "Notes médicales"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"[{self.get_categorie_display()}] {self.patient} — {self.contenu[:40]}"


class PatientMedecin(models.Model):
    """
    Relation de suivi entre un patient et un médecin, avec historique.

    Un médecin ne doit voir/modifier que les patients pour lesquels cette
    relation existe et est active (appliqué au niveau des permissions API,
    pas seulement en base).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="medecins_suivi"
    )
    medecin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patients_suivis",
    )
    actif = models.BooleanField(default=True)
    date_debut = models.DateField(auto_now_add=True)
    date_fin = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Suivi médecin-patient"
        verbose_name_plural = "Suivis médecin-patient"
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "medecin"],
                condition=models.Q(actif=True),
                name="un_seul_suivi_actif_par_couple_patient_medecin",
            )
        ]

    def __str__(self):
        statut = "actif" if self.actif else "terminé"
        return f"{self.medecin} suit {self.patient} ({statut})"
