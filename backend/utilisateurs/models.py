import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

# Noms des groupes métier, centralisés pour éviter les chaînes "magiques"
# dupliquées dans le reste du code.
ROLE_ADMIN = "admin"
ROLE_MEDECIN = "medecin"
ROLE_PATIENT = "patient"


class Utilisateur(AbstractUser):
    """
    Utilisateur de l'application.

    Le rôle n'est PAS un champ libre : il est porté par les Groups natifs
    de Django ("admin", "medecin", "patient"), afin de réutiliser le
    système de permissions éprouvé de Django plutôt que d'en réinventer un.

    On garde une propriété `role` en lecture seule pour simplifier l'accès
    côté API/serializers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    actif = models.BooleanField(
        default=True,
        help_text="Permet de désactiver un compte sans le supprimer (traçabilité).",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    # Connexion par email plutôt que par username.
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.role})"

    @property
    def role(self) -> str:
        """
        Rôle principal déduit du Group. Convention : un utilisateur
        n'appartient qu'à un seul des groupes métier (appliqué à la
        création du compte, pas contraint en base par Django).
        """
        noms_groupes = set(self.groups.values_list("name", flat=True))
        for role in (ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT):
            if role in noms_groupes:
                return role
        return "sans_role"
