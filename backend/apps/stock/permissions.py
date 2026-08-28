from rest_framework import permissions

from apps.patients.permissions import medecin_suit_patient
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT


class PeutAccederAuStock(permissions.BasePermission):
    """
    - admin : accès total
    - médecin : accès aux boîtes des patients qu'il suit activement
    - patient : accès total à ses propres boîtes (cohérent avec la
      décision du palier 2 : le patient gère librement ses propres
      données de suivi quotidien, y compris ici son stock).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == ROLE_ADMIN:
            return True
        if user.role == ROLE_MEDECIN:
            return medecin_suit_patient(user, obj.patient)
        if user.role == ROLE_PATIENT:
            return obj.patient.utilisateur_id == user.id
        return False
