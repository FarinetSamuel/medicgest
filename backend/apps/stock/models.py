import uuid

from django.db import models

from apps.medicaments.models import Medicament
from apps.patients.models import Patient
from apps.prescriptions.models import Prise


class Boite(models.Model):
    """
    Une boîte de médicament détenue par un patient.

    Décision validée : un patient peut avoir plusieurs boîtes actives du
    même médicament en même temps (ex. stock d'avance). Le décompte
    automatique consomme les boîtes en FEFO (First-Expired-First-Out :
    la boîte dont la péremption est la plus proche est utilisée en
    premier — plus sûr médicalement qu'un simple FIFO par date d'achat).
    """

    class Statut(models.TextChoices):
        ACTIVE = "active", "Active"
        EPUISEE = "epuisee", "Épuisée"
        PERIMEE = "perimee", "Périmée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="boites")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT, related_name="boites")

    quantite_initiale = models.DecimalField(max_digits=8, decimal_places=2)
    quantite_restante = models.DecimalField(max_digits=8, decimal_places=2)

    date_ouverture = models.DateField(null=True, blank=True)
    date_peremption = models.DateField(null=True, blank=True)
    delai_reappro_jours = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Délai habituel pour obtenir une nouvelle boîte."
    )

    # Décision validée : les deux types de seuil sont possibles, au choix
    # (indépendamment activables par boîte, selon ce qui a du sens pour ce
    # médicament précis).
    seuil_alerte_quantite = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Alerte si quantite_restante passe à ou sous ce seuil.",
    )
    seuil_alerte_jours = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Alerte si le stock restant (toutes boîtes actives de ce "
        "médicament) est estimé à ce nombre de jours ou moins, d'après la "
        "consommation réelle récente.",
    )

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIVE)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Boîte"
        verbose_name_plural = "Boîtes"
        ordering = ["date_peremption"]

    def __str__(self):
        return f"{self.medicament} — {self.patient} ({self.quantite_restante}/{self.quantite_initiale})"

    # --- Alertes ---

    @property
    def en_alerte_quantite(self) -> bool:
        if self.seuil_alerte_quantite is None:
            return False
        return self.quantite_restante <= self.seuil_alerte_quantite

    @property
    def en_alerte_jours(self) -> bool:
        if self.seuil_alerte_jours is None:
            return False
        from .logique import jours_restants_estimes

        jours = jours_restants_estimes(self.patient, self.medicament)
        if jours is None:
            return False
        return jours <= self.seuil_alerte_jours

    @property
    def en_alerte(self) -> bool:
        return self.en_alerte_quantite or self.en_alerte_jours


class MouvementStock(models.Model):
    """
    Trace chaque variation de quantite_restante d'une boîte.

    quantite est signée : négative pour une consommation (prise),
    positive pour un réapprovisionnement/ajustement manuel. Permet de
    reconstituer et d'annuler proprement l'effet d'une Prise sur le stock
    si elle est modifiée ou supprimée (le patient peut le faire sans
    restriction — voir Palier 2).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boite = models.ForeignKey(Boite, on_delete=models.CASCADE, related_name="mouvements")
    prise = models.ForeignKey(
        Prise, on_delete=models.SET_NULL, null=True, blank=True, related_name="mouvements_stock"
    )
    quantite = models.DecimalField(max_digits=8, decimal_places=2)
    motif = models.CharField(max_length=255, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"
        ordering = ["-date_creation"]

    def __str__(self):
        signe = "+" if self.quantite >= 0 else ""
        return f"{self.boite} : {signe}{self.quantite}"
