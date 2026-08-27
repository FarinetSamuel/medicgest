from rest_framework import viewsets

from .models import Utilisateur
from .permissions import EstAdmin
from .serializers import UtilisateurCreationSerializer, UtilisateurSerializer


class UtilisateurViewSet(viewsets.ModelViewSet):
    """
    Gestion des comptes utilisateurs.

    Réservé aux administrateurs (voir matrice de permissions du palier 1 :
    seul un admin peut créer/modifier un utilisateur).
    """

    queryset = Utilisateur.objects.all().order_by("email")
    permission_classes = [EstAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UtilisateurCreationSerializer
        return UtilisateurSerializer
