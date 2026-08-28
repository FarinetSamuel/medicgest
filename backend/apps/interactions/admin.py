from django.contrib import admin

from .models import InteractionMedicamenteuse, InteractionNonImportee


@admin.register(InteractionMedicamenteuse)
class InteractionMedicamenteuseAdmin(admin.ModelAdmin):
    list_display = ("protagoniste_a", "protagoniste_b", "niveau", "date_publication_source")
    list_filter = ("niveau",)
    search_fields = ("protagoniste_a", "protagoniste_b")


@admin.register(InteractionNonImportee)
class InteractionNonImporteeAdmin(admin.ModelAdmin):
    list_display = ("protagoniste_a", "protagoniste_b", "raison_exclusion")
    search_fields = ("protagoniste_a", "protagoniste_b")
