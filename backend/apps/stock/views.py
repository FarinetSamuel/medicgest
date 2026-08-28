from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT

from .models import Boite, MouvementStock
from .permissions import PeutAccederAuStock
from .serializers import BoiteSerializer, MouvementStockSerializer


class BoiteViewSet(viewsets.ModelViewSet):
    """
    CRUD sur les boîtes de stock.
    - admin : accès total
    - médecin : accès aux boîtes des patients qu'il suit
    - patient : accès total à ses propres boîtes (il gère lui-même son
      stock au quotidien — cohérent avec la liberté déjà accordée sur
      ses propres Prise au palier 2).
    """

    serializer_class = BoiteSerializer
    permission_classes = [IsAuthenticated, PeutAccederAuStock]

    def get_queryset(self):
        user = self.request.user
        base = Boite.objects.select_related("patient", "medicament")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                patient__medecins_suivi__medecin=user, patient__medecins_suivi__actif=True
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(patient__utilisateur=user)
        return base.none()


class MouvementStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Historique des mouvements de stock — lecture seule : un mouvement est
    une conséquence automatique d'une Prise (ou d'un ajustement manuel
    futur), jamais créé/modifié directement via cette route.
    """

    serializer_class = MouvementStockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = MouvementStock.objects.select_related("boite__patient", "boite__medicament")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                boite__patient__medecins_suivi__medecin=user,
                boite__patient__medecins_suivi__actif=True,
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(boite__patient__utilisateur=user)
        return base.none()
