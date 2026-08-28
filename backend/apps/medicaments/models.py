import uuid

from django.db import models


class SubstanceActive(models.Model):
    """
    Substance active (principe actif), normalisée pour permettre le
    croisement avec les protagonistes du Thésaurus des interactions
    (apps.interactions), qui raisonne en substances/classes, pas en noms
    commerciaux de médicaments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=255, unique=True, help_text="Nom normalisé en MAJUSCULES.")

    class Meta:
        verbose_name = "Substance active"
        verbose_name_plural = "Substances actives"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        self.nom = self.nom.strip().upper()
        super().save(*args, **kwargs)


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
    substances_actives = models.ManyToManyField(
        SubstanceActive,
        blank=True,
        related_name="medicaments",
        help_text="Renseigné par import_bdpm --fichier-composition. "
        "Utilisé par apps.interactions pour croiser avec le Thésaurus ANSM.",
    )
    source = models.CharField(max_length=20, default="BDPM", editable=False)
    date_import = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Médicament"
        verbose_name_plural = "Médicaments"
        ordering = ["denomination"]

    def __str__(self):
        return f"{self.denomination} ({self.dosage})".strip()
