from django import forms
from django.contrib import admin

from .models import ConfigurationEmail, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("titre", "destinataire", "canal", "categorie", "statut", "date_creation")
    list_filter = ("canal", "categorie", "statut")
    search_fields = ("titre", "destinataire__email")


class ConfigurationEmailForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe / clé API",
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Laisser vide pour conserver le mot de passe actuellement enregistré.",
    )

    class Meta:
        model = ConfigurationEmail
        fields = "__all__"

    def clean_mot_de_passe(self):
        # Le widget PasswordInput n'affiche jamais la valeur existante
        # (comportement voulu) : sans ce garde-fou, ne rien saisir lors
        # d'une modification effacerait le mot de passe déjà enregistré.
        valeur = self.cleaned_data["mot_de_passe"]
        if not valeur and self.instance.pk:
            return self.instance.mot_de_passe
        return valeur


@admin.register(ConfigurationEmail)
class ConfigurationEmailAdmin(admin.ModelAdmin):
    """
    Singleton (voir ConfigurationEmail.save) : une seule ligne éditable,
    pas de suppression, pas de second ajout une fois la première créée.
    """

    form = ConfigurationEmailForm
    list_display = ("actif", "hote", "port", "date_modification")

    def has_add_permission(self, request):
        return not ConfigurationEmail.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
