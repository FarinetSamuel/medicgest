from django.apps import AppConfig


class PrescriptionsConfig(AppConfig):
    name = 'apps.prescriptions'

    def ready(self):
        # Reporte la quantité d'un horaire modifié sur ses prises attendues
        # à venir, y compris depuis l'admin Django (voir signals.py).
        from . import signals  # noqa: F401
