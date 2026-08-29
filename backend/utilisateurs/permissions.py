"""
Permissions DRF partagées, basées sur le rôle (Group) de l'utilisateur.

Centralisées ici car le rôle est porté par le modèle Utilisateur — les
autres apps (patients, medicaments...) les importent plutôt que de
redéfinir leur propre logique de rôle.
"""

from rest_framework import permissions

from .models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT


class EstAdmin(permissions.BasePermission):
    """Autorise uniquement les utilisateurs du groupe 'admin'."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == ROLE_ADMIN
        )


class EstAdminOuMedecin(permissions.BasePermission):
    """Autorise les utilisateurs des groupes 'admin' ou 'medecin', sans distinction de méthode HTTP."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (ROLE_ADMIN, ROLE_MEDECIN)
        )


class EstAdminOuMedecinEnLecture(permissions.BasePermission):
    """
    Lecture (GET/HEAD/OPTIONS) : admin ou médecin.
    Écriture : admin ou médecin uniquement (le filtrage fin sur "ses
    patients suivis" se fait au niveau du queryset et de perform_create,
    car un médecin ne doit voir/écrire que sur SES patients, pas tous).
    Un patient n'a jamais accès à cette permission (lecture de ses propres
    données gérée séparément, via le queryset).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return request.user.role in (ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT)
        return request.user.role in (ROLE_ADMIN, ROLE_MEDECIN)
