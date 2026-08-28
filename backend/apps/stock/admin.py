from django.contrib import admin

from .models import Boite, MouvementStock


class MouvementStockInline(admin.TabularInline):
    model = MouvementStock
    extra = 0
    readonly_fields = ("prise", "quantite", "motif", "date_creation")
    can_delete = False


@admin.register(Boite)
class BoiteAdmin(admin.ModelAdmin):
    list_display = (
        "medicament", "patient", "quantite_restante", "quantite_initiale",
        "statut", "date_peremption", "en_alerte",
    )
    list_filter = ("statut",)
    search_fields = ("patient__numero_dossier", "medicament__denomination")
    inlines = [MouvementStockInline]

    @admin.display(boolean=True, description="En alerte")
    def en_alerte(self, obj):
        return obj.en_alerte
