from django.contrib import admin

from .models import NoteMedicale, Patient, PatientMedecin


class NoteMedicaleInline(admin.TabularInline):
    model = NoteMedicale
    extra = 0


class PatientMedecinInline(admin.TabularInline):
    model = PatientMedecin
    fk_name = "patient"
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("numero_dossier", "utilisateur", "date_naissance", "sexe")
    search_fields = ("numero_dossier", "utilisateur__last_name", "utilisateur__email")
    inlines = [NoteMedicaleInline, PatientMedecinInline]
