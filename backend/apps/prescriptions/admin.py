from django.contrib import admin

from .models import HoraireProgramme, Prescription, Prise


class HoraireProgrammeInline(admin.TabularInline):
    model = HoraireProgramme
    extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("patient", "medicament", "type_prise", "statut", "date_debut", "date_fin")
    list_filter = ("type_prise", "statut")
    search_fields = ("patient__numero_dossier", "medicament__denomination")
    inlines = [HoraireProgrammeInline]


@admin.register(Prise)
class PriseAdmin(admin.ModelAdmin):
    list_display = (
        "prescription",
        "statut",
        "date_heure_prevue",
        "date_heure_reelle",
        "alerte_depassement",
    )
    list_filter = ("statut", "alerte_depassement")
