from django.core.exceptions import ValidationError
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.patients.models import Patient
from apps.patients.permissions import medecin_suit_patient
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT

from .models import Medicament
from .serializers import MedicamentSerializer


class MedicamentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Référentiel médicaments, consultable par tous les rôles authentifiés.
    ReadOnlyModelViewSet : aucune route de création/modification/suppression
    n'existe même dans l'URLconf — le référentiel ne peut être modifié que
    par la commande import_bdpm, jamais via l'API.

    filter_backends + SearchFilter : sans eux, `search_fields` ne fait
    STRICTEMENT RIEN (vérifié : ?search=... renvoyait la liste complète,
    non filtrée, avant cet ajout) — indispensable avec 15 857 médicaments
    réels pour permettre un vrai champ de recherche côté frontend plutôt
    que de parcourir des centaines de pages.
    """

    queryset = Medicament.objects.all()
    serializer_class = MedicamentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["denomination", "code_cis"]

    def get_queryset(self):
        """
        ?source=BDPM|SWISSMEDIC : le frontend choisit un pays (France ou
        Suisse) et ne doit voir que le référentiel correspondant — les
        deux catalogues ne sont jamais mélangés dans un même formulaire
        (noms de substances non rapprochables, voir
        Medicament.verification_interactions_fiable). Une valeur inconnue
        est ignorée plutôt que de lever une erreur 400 sur un simple
        filtre de confort.
        """
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            # ?patient=<uuid> : le référentiel est celui du patient
            # (Patient.referentiel_medicaments), décidé côté backend. Prime
            # sur ?source=. Un patient inaccessible à l'appelant donne une
            # liste vide, sans révéler son existence.
            patient = self._patient_accessible(patient_id)
            return queryset.filter(source=patient.referentiel_medicaments) if patient else queryset.none()
        source = self.request.query_params.get("source")
        if source in Medicament.Source.values:
            queryset = queryset.filter(source=source)
        return queryset

    def _patient_accessible(self, patient_id):
        user = self.request.user
        try:
            patient = Patient.objects.filter(pk=patient_id).first()
        except (ValueError, ValidationError):
            return None
        if patient is None:
            return None
        if user.role == ROLE_ADMIN:
            return patient
        if user.role == ROLE_MEDECIN and medecin_suit_patient(user, patient):
            return patient
        if user.role == ROLE_PATIENT and patient.utilisateur_id == user.id:
            return patient
        return None
