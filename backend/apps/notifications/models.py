import uuid

from django.conf import settings
from django.db import models

from apps.prescriptions.models import Prise
from apps.stock.models import Boite


class Notification(models.Model):
    """
    Une notification, quel que soit son canal de diffusion.

    Deux FK nullables (prise, boite) plutôt qu'une relation générique
    (GenericForeignKey) : on ne sert que deux cas d'usage pour l'instant
    (rappel de prise, alerte de stock) — un GenericForeignKey ajouterait
    de la complexité sans bénéfice réel tant qu'un troisième cas n'existe
    pas. Ces deux FK servent aussi à éviter les doublons de notification
    (voir apps.notifications.logique).
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
