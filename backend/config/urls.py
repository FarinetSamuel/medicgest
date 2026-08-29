"""
URLconf racine.

L'API REST est regroupée sous /api/v1/. Chaque app expose son propre
urls.py, inclus ici, pour rester en accord avec le principe "évoluer
facilement" du cahier des charges (ajouter un module = ajouter une ligne).
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.utilisateurs.urls")),
    path("api/v1/", include("apps.patients.urls")),
    path("api/v1/", include("apps.medicaments.urls")),
    path("api/v1/", include("apps.prescriptions.urls")),
    path("api/v1/", include("apps.stock.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.interactions.urls")),
    path("api/v1/", include("apps.exports.urls")),
    # Authentification navigable (login/logout) pour l'API browsable DRF.
    path("api-auth/", include("rest_framework.urls")),
]
