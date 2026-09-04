import uuid

from django.conf import settings
from django.db import models

from apps.prescriptions.models import Prescription, Prise
from apps.stock.models import Boite


class Notification(models.Model):
    """
    Une notification, quel que soit son canal de diffusion.

    Trois FK nullables (prise, boite, prescription) plutôt qu'une relation
    générique (GenericForeignKey) : on ne sert que trois cas d'usage pour
    l'instant (rappel de prise, alerte de stock bas sur une boîte, alerte
    de rupture totale sur une prescription sans aucune boîte) — un
    GenericForeignKey ajouterait de la complexité sans bénéfice réel tant
    qu'un quatrième cas n'existe pas. Ces FK servent aussi à éviter les
    doublons de notification (voir apps.notifications.logique).
    """

    class Canal(models.TextChoices):
        EMAIL = "email", "E-mail"
        SMS = "sms", "SMS"
        IN_APP = "in_app", "Dans l'application"

    class Categorie(models.TextChoices):
        RAPPEL_PRISE = "rappel_prise", "Rappel de prise"
        ALERTE_STOCK = "alerte_stock", "Alerte de stock"
        AUTRE = "autre", "Autre"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ENVOYEE = "envoyee", "Envoyée"
        ECHEC = "echec", "Échec"
        LUE = "lue", "Lue"  # in_app uniquement

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    canal = models.CharField(max_length=10, choices=Canal.choices)
    categorie = models.CharField(max_length=20, choices=Categorie.choices)
    titre = models.CharField(max_length=255)
    message = models.TextField()

    prise = models.ForeignKey(
        Prise, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    boite = models.ForeignKey(
        Boite, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    erreur = models.TextField(blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_envoi = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"[{self.get_canal_display()}] {self.titre} → {self.destinataire}"


class ConfigurationEmail(models.Model):
    """
    Réglages SMTP éditables depuis l'admin Django, sans toucher au .env ni
    redéployer. Ligne unique (singleton, voir save()) : "actif=False" (ou
    absente) retombe sur EMAIL_BACKEND de settings.py (console par défaut,
    ou un backend SMTP fixé via .env) — voir apps.notifications.canaux.
    """

    actif = models.BooleanField(
        default=False,
        help_text="Active l'envoi SMTP réel avec ces réglages. Décoché : "
        "les e-mails suivent la configuration du fichier .env (console par défaut).",
    )
    hote = models.CharField("Hôte SMTP", max_length=255, blank=True)
    port = models.PositiveIntegerField("Port", default=587)
    identifiant = models.CharField("Identifiant", max_length=255, blank=True)
    mot_de_passe = models.CharField("Mot de passe / clé API", max_length=255, blank=True)
    utiliser_tls = models.BooleanField("Utiliser TLS", default=True)
    utiliser_ssl = models.BooleanField("Utiliser SSL", default=False)
    adresse_expediteur = models.CharField(
        "Adresse d'expédition", max_length=255, blank=True,
        help_text="Laisser vide pour utiliser DEFAULT_FROM_EMAIL du .env.",
    )
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration e-mail"
        verbose_name_plural = "Configuration e-mail"

    def __str__(self):
        return "Configuration e-mail"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def charger(cls):
        return cls.objects.first()
