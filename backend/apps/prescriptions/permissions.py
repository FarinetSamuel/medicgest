from rest_framework import permissions

from apps.patients.permissions import medecin_suit_patient
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT


class PeutAccederALaPrescription(permissions.BasePermission):
    """
    - admin : accès total
    - médecin : accès aux prescriptions des patients qu'il suit activement
    - patient : lecture seule de ses propres prescriptions
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
            return obj.patient.utilisateur_id == user.id and request.method in permissions.SAFE_METHODS
        return False


class PeutAccederALaPrise(permissions.BasePermission):
    """
    - admin : accès total
    - médecin : accès aux prises des patients qu'il suit activement
    - patient : accès total (lecture + écriture SANS restriction, y
      compris modification/suppression) sur ses propres prises —
      décision validée avec le porteur du projet.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == ROLE_ADMIN:
            return True
        if user.role == ROLE_MEDECIN:
            return medecin_suit_patient(user, obj.prescription.patient)
        if user.role == ROLE_PATIENT:
            return obj.prescription.patient.utilisateur_id == user.id
        return False
