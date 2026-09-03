from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.patients.permissions import medecin_suit_patient
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT
from apps.utilisateurs.permissions import EstAdminOuMedecin

from .logique import calculer_alerte_depassement
from .models import HoraireProgramme, Prescription, Prise
from .permissions import PeutAccederALaPrescription, PeutAccederALaPrise
from .serializers import HoraireProgrammeSerializer, PrescriptionSerializer, PriseSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    - admin : accès total
    - médecin : crée/modifie des prescriptions pour ses patients suivis
      (devient automatiquement le medecin_prescripteur)
    - patient : lecture seule de ses propres prescriptions
    """

    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, PeutAccederALaPrescription]

    def get_queryset(self):
        user = self.request.user
        base = Prescription.objects.select_related("patient", "medicament", "medecin_prescripteur")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                patient__medecins_suivi__medecin=user, patient__medecins_suivi__actif=True
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(patient__utilisateur=user)
        return base.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), EstAdminOuMedecin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        patient = serializer.validated_data["patient"]
        if user.role == ROLE_MEDECIN:
            if not medecin_suit_patient(user, patient):
                raise PermissionDenied(
                    "Vous ne pouvez prescrire que pour un patient que vous suivez."
                )
            serializer.save(medecin_prescripteur=user)
        else:
            # Admin : le prescripteur doit être précisé côté client
            # (un admin peut rédiger une prescription au nom d'un médecin
            # existant, ex. import/rattrapage de données). Sans ce
            # contrôle explicite, une requête admin sans ce champ
            # provoquait une IntegrityError 500 (colonne NOT NULL en
            # base) au lieu d'un message d'erreur exploitable.
            if not serializer.validated_data.get("medecin_prescripteur"):
                raise ValidationError(
                    {"medecin_prescripteur": "Ce champ est requis lorsqu'un administrateur crée la prescription."}
                )
            serializer.save()


class HoraireProgrammeViewSet(viewsets.ModelViewSet):
    """Horaires fixes d'une prescription régulière. Même périmètre que Prescription."""

    serializer_class = HoraireProgrammeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = HoraireProgramme.objects.select_related("prescription__patient")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                prescription__patient__medecins_suivi__medecin=user,
                prescription__patient__medecins_suivi__actif=True,
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(prescription__patient__utilisateur=user)
        return base.none()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), EstAdminOuMedecin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        prescription = serializer.validated_data["prescription"]
        if user.role == ROLE_MEDECIN and not medecin_suit_patient(user, prescription.patient):
            raise PermissionDenied(
                "Vous ne pouvez ajouter un horaire que pour un patient que vous suivez."
            )
        serializer.save()


class PriseViewSet(viewsets.ModelViewSet):
    """
    - admin : accès total
    - médecin : accès aux prises des patients qu'il suit
    - patient : accès total (y compris modification/suppression, sans
      restriction) sur ses propres prises — décision validée.
    """

    serializer_class = PriseSerializer
    permission_classes = [IsAuthenticated, PeutAccederALaPrise]

    def get_queryset(self):
        user = self.request.user
        base = Prise.objects.select_related("prescription__patient", "horaire_programme")
        if user.role == ROLE_ADMIN:
            return base
        if user.role == ROLE_MEDECIN:
            return base.filter(
                prescription__patient__medecins_suivi__medecin=user,
                prescription__patient__medecins_suivi__actif=True,
            ).distinct()
        if user.role == ROLE_PATIENT:
            return base.filter(prescription__patient__utilisateur=user)
        return base.none()

    def perform_create(self, serializer):
        user = self.request.user
        prescription = serializer.validated_data["prescription"]
        # has_object_permission n'est jamais appelée à la création (pas
        # encore d'objet) : sans ce contrôle explicite, PeutAccederALaPrise
        # laisse passer n'importe quel utilisateur authentifié, qui pourrait
        # alors enregistrer une prise sur la prescription d'un autre
        # patient (et donc décrémenter le stock de ce patient via le signal
        # stock/signals.py).
        if user.role == ROLE_MEDECIN and not medecin_suit_patient(user, prescription.patient):
            raise PermissionDenied(
                "Vous ne pouvez enregistrer une prise que pour un patient que vous suivez."
            )
        if user.role == ROLE_PATIENT and prescription.patient.utilisateur_id != user.id:
            raise PermissionDenied(
                "Vous ne pouvez enregistrer une prise que sur vos propres prescriptions."
            )
        prise = serializer.save(enregistre_par=user)
        prise.alerte_depassement = calculer_alerte_depassement(prise)
        prise.save(update_fields=["alerte_depassement"])

    def perform_update(self, serializer):
        prise = serializer.save()
        prise.alerte_depassement = calculer_alerte_depassement(prise)
        prise.save(update_fields=["alerte_depassement"])
