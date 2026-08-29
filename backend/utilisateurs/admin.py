from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "actif", "is_staff")
    ordering = ("email",)
