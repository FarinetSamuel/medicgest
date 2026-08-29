from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import UtilisateurConnecteView, UtilisateurViewSet

router = DefaultRouter()
router.register("utilisateurs", UtilisateurViewSet, basename="utilisateur")

urlpatterns = router.urls + [
    path("auth/me/", UtilisateurConnecteView.as_view(), name="utilisateur-connecte"),
]
