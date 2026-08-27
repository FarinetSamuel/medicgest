from django.contrib import admin

from .models import Medicament


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ("denomination", "dosage", "forme_pharmaceutique", "code_cis", "source")
    search_fields = ("denomination", "code_cis")
    # Lecture seule dans l'admin : le référentiel ne doit être modifié que
    # par la commande d'import BDPM, jamais saisi à la main.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
