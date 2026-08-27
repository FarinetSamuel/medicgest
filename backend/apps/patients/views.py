from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT
from apps.utilisateurs.permissions import EstAdmin, EstAdminOuMedecinEnLecture

from .models import NoteMedicale, Patient, PatientMedecin
from .permissions import PeutAccederAuPatient, medecin_suit_patient
from .serializers import NoteMedicaleSerializer, PatientMedecinSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD sur les patients, avec un périmètre différent par rôle :
    - admin : voit et modifie tous les patients
    - médecin : voit et modifie uniquement les patients qu'il suit
      activement (jamais la création — réservée à l'admin, car elle
      implique la création d'un compte utilisateur associé)
    - patient : voit uniquement sa propre fiche, en lecture seule
    """

    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, PeutAccederAuPatient]

    def get_queryset(self):
        user = self.request.user
        base = Patient.objects.select_related("utilisateur").prefetch_related(
            "notes_medicales"
        )
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                medecins_suivi__medecin=user, medecins_suivi__actif=True
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(utilisateur=user)
        return base.none()

    def get_permissions(self):
        # La création est réservée à l'admin (cf. docstring ci-dessus) ;
        # les autres actions passent par PeutAccederAuPatient (objet).
        if self.action == "create":
            return [IsAuthenticated(), EstAdmin()]
        return super().get_permissions()


class NoteMedicaleViewSet(viewsets.ModelViewSet):
    """
    Notes médicales structurées.
    - admin : accès total
    - médecin : lecture/écriture uniquement sur les notes des patients
      qu'il suit activement
    - patient : lecture seule de ses propres notes
    """

    serializer_class = NoteMedicaleSerializer
    permission_classes = [IsAuthenticated, EstAdminOuMedecinEnLecture]

    def get_queryset(self):
        user = self.request.user
        base = NoteMedicale.objects.select_related("patient", "saisi_par")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                patient__medecins_suivi__medecin=user,
                patient__medecins_suivi__actif=True,
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(patient__utilisateur=user)
        return base.none()

    def perform_create(self, serializer):
        user = self.request.user
        patient = serializer.validated_data["patient"]
        if user.role == ROLE_ADMIN or (
            user.role == ROLE_MEDECIN and medecin_suit_patient(user, patient)
        ):
            serializer.save(saisi_par=user)
        else:
            raise PermissionDenied(
                "Vous ne pouvez ajouter une note que pour un patient que vous suivez."
            )


class PatientMedecinViewSet(viewsets.ModelViewSet):
    """
    Relations de suivi patient-médecin.
    Gestion réservée à l'admin (établir/révoquer un suivi est une décision
    administrative) ; un médecin peut consulter ses propres relations.
    """

    serializer_class = PatientMedecinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = PatientMedecin.objects.select_related("patient", "medecin")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(medecin=user)
        return base.none()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), EstAdmin()]
        return [IsAuthenticated()]
