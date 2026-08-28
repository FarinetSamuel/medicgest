from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("titre", "destinataire", "canal", "categorie", "statut", "date_creation")
    list_filter = ("canal", "categorie", "statut")
    search_fields = ("titre", "destinataire__email")
