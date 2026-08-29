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


from rest_framework.permissions import IsAuthenticated as _IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class UtilisateurConnecteView(APIView):
    """
    GET /api/v1/auth/me/ — identité de l'utilisateur connecté (email, nom,
    rôle, et l'id de sa fiche Patient si le rôle est 'patient'). Le
    frontend en a besoin juste après connexion pour adapter la navigation
    et les permissions affichées, sans avoir à deviner le rôle.
    """

    permission_classes = [_IsAuthenticated]

    def get(self, request):
        user = request.user
        donnees = {
            "id": str(user.id),
            "email": user.email,
            "prenom": user.first_name,
            "nom": user.last_name,
            "role": user.role,
        }
        if user.role == "patient" and hasattr(user, "fiche_patient"):
            donnees["patient_id"] = str(user.fiche_patient.id)
        return Response(donnees)
