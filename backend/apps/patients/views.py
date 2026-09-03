from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT
from apps.utilisateurs.permissions import EstAdmin, EstAdminOuMedecin, EstAdminOuMedecinEnLecture

from .models import NoteMedicale, Patient, PatientMedecin
from .permissions import PeutAccederAuPatient, medecin_suit_patient
from .serializers import NoteMedicaleSerializer, PatientMedecinSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD sur les patients, avec un périmètre différent par rôle :
    - admin : voit et modifie tous les patients
    - médecin : voit et modifie les patients qu'il suit activement ; peut
      aussi CRÉER un nouveau patient — il devient alors automatiquement
      son médecin suiveur (voir perform_create). Le compte Utilisateur
      associé doit déjà exister (créé par un admin au préalable, car la
      création de comptes reste une action strictement admin) : le
      médecin référence cet utilisateur en créant la fiche Patient.
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
        # Création : admin ou médecin (cf. docstring). Les autres actions
        # passent par PeutAccederAuPatient (vérification au niveau objet).
        if self.action == "create":
            return [IsAuthenticated(), EstAdminOuMedecin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        patient = serializer.save()
        user = self.request.user
        if user.role == ROLE_MEDECIN:
            # Le médecin qui crée la fiche devient automatiquement son
            # médecin suiveur actif — évite une étape manuelle séparée
            # sur /suivis-medecin/ juste après la création.
            PatientMedecin.objects.create(patient=patient, medecin=user, actif=True)

    @action(detail=True, methods=["patch"], url_path="preference-alerte-stock")
    def preference_alerte_stock(self, request, pk=None):
        """
        Action dédiée plutôt qu'un PATCH générique sur la fiche : la fiche
        Patient reste en lecture seule pour le patient (voir
        PeutAccederAuPatient), mais ce champ précis lui appartient — c'est
        lui qui choisit qui est prévenu en cas de stock bas ou de rupture
        (voir apps.notifications.logique._destinataires_alerte_stock).
        get_queryset() applique déjà le bon périmètre par rôle (admin :
        tous, médecin : patients suivis, patient : lui-même), donc pas de
        contrôle d'autorisation supplémentaire à dupliquer ici.
        """
        patient = self.get_queryset().filter(pk=pk).first()
        if patient is None:
            raise NotFound("Patient introuvable.")

        valeur = request.data.get("preference_alerte_stock")
        valeurs_valides = [choix[0] for choix in Patient.PreferenceAlerteStock.choices]
        if valeur not in valeurs_valides:
            raise ValidationError(
                {"preference_alerte_stock": f"Doit être l'une de : {', '.join(valeurs_valides)}."}
            )

        patient.preference_alerte_stock = valeur
        patient.save(update_fields=["preference_alerte_stock"])
        return Response(PatientSerializer(patient).data)


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
