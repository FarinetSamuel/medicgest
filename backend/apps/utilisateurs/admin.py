from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "actif", "is_staff")
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name")

    # Le formulaire d'ajout par défaut de UserAdmin (hérité tel quel)
    # ne demande que username + mot de passe : email n'y figure pas,
    # alors que c'est le USERNAME_FIELD réel (connexion) ET un champ
    # unique obligatoire en base. Résultat observé en production : un
    # premier compte créé avec email="" en base, puis IntegrityError
    # (doublon) dès la tentative suivante. On force explicitement email,
    # prénom et nom sur l'écran d'ajout pour empêcher ce cas.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name")}),
        (
            "Rôle et statut",
            {
                "fields": (
                    "actif",
                    "specialite",
                    "specialite_autre",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
