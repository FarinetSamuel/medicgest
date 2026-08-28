import uuid

from django.db import models


class Medicament(models.Model):
    """
    Référentiel des médicaments.

    Règle non négociable : ces enregistrements sont importés depuis la
    BDPM (Base de Données Publique des Médicaments, ANSM/data.gouv.fr) via
    la commande `import_bdpm`, jamais saisis manuellement. Le champ
    `source` sert de garde-fou traçable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_cis = models.CharField(
        max_length=20,
        unique=True,
        help_text="Code Identifiant de Spécialité officiel (BDPM).",
    )
    denomination = models.CharField(max_length=255)
    forme_pharmaceutique = models.CharField(max_length=255, blank=True)
    dosage = models.CharField(
        max_length=500,
        blank=True,
        help_text="Concaténation de toutes les substances actives (SA) et leur dosage — "
        "peut être long pour les médicaments combinant plusieurs substances.",
    )
    laboratoire = models.CharField(max_length=255, blank=True)
    code_atc = models.CharField(
        max_length=10,
        blank=True,
        help_text="Classification anatomique, thérapeutique et chimique — "
        "utile pour le futur module de vérification des interactions.",
    )
    source = models.CharField(max_length=20, default="BDPM", editable=False)
    date_import = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Médicament"
        verbose_name_plural = "Médicaments"
        ordering = ["denomination"]

    def __str__(self):
        return f"{self.denomination} ({self.dosage})".strip()
