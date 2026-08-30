from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import ROLE_MEDECIN, ROLE_PATIENT, Utilisateur
from .permissions import EstAdmin, EstAdminOuMedecin
from .serializers import UtilisateurCreationSerializer, UtilisateurSerializer


class UtilisateurViewSet(viewsets.ModelViewSet):
    """
    Gestion des comptes utilisateurs.

    Création/modification/désactivation : réservées aux administrateurs
    (décision validée dans le palier 1, non re-questionnée ici).

    Lecture (list/retrieve) : ouverte aux médecins, mais restreinte aux
    comptes de rôle "patient" actifs (voir get_queryset) — un médecin doit
    pouvoir associer un compte existant à une nouvelle fiche Patient sans
    pour autant parcourir la liste des autres comptes admin/médecin.
    """

    def get_queryset(self):
        base = Utilisateur.objects.all().order_by("email")
        if self.request.user.is_authenticated and self.request.user.role == ROLE_MEDECIN:
            return base.filter(groups__name=ROLE_PATIENT, actif=True)
        return base

    def get_serializer_class(self):
        if self.action == "create":
            return UtilisateurCreationSerializer
        return UtilisateurSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), EstAdminOuMedecin()]
        return [IsAuthenticated(), EstAdmin()]
