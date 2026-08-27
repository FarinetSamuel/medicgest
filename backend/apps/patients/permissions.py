from rest_framework import permissions

from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT


def medecin_suit_patient(medecin, patient) -> bool:
    """Vrai si `medecin` a un suivi actif sur `patient` (relation PatientMedecin)."""
    return patient.medecins_suivi.filter(medecin=medecin, actif=True).exists()


class PeutAccederAuPatient(permissions.BasePermission):
    """
    Permission au niveau objet pour un `Patient` :
    - admin : accès total (lecture + écriture)
    - médecin : lecture + écriture uniquement sur les patients qu'il suit
      activement (voir PatientMedecin)
    - patient : lecture seule de sa propre fiche uniquement
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == ROLE_ADMIN:
            return True
        if user.role == ROLE_MEDECIN:
            return medecin_suit_patient(user, obj)
        if user.role == ROLE_PATIENT:
            return obj.utilisateur_id == user.id and request.method in permissions.SAFE_METHODS
        return False
