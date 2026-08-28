from django.apps import AppConfig


class StockConfig(AppConfig):
    name = "apps.stock"
    verbose_name = "Stock"

    def ready(self):
        # Connecte les signaux qui décrémentent/réajustent automatiquement
        # le stock à chaque prise enregistrée (import ici pour éviter les
        # imports circulaires au chargement des apps).
        from . import signals  # noqa: F401
