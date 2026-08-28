from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import Patient
from apps.patients.permissions import medecin_suit_patient
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT

from .logique import verifier_interactions
from .serializers import VerificationInteractionsSerializer


class VerificationInteractionsView(APIView):
    """
    GET /api/v1/patients/<id>/verifier-interactions/

    Vérifie les interactions entre les médicaments actuellement prescrits
    à ce patient. Même périmètre d'accès que la fiche patient elle-même :
    admin (tous), médecin (ses patients suivis), patient (lui-même).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise NotFound()

        user = request.user
        autorise = (
            user.role == ROLE_ADMIN
            or (user.role == ROLE_MEDECIN and medecin_suit_patient(user, patient))
            or (user.role == ROLE_PATIENT and patient.utilisateur_id == user.id)
        )
        if not autorise:
            raise NotFound()  # ne pas révéler l'existence du patient hors périmètre

        interactions = verifier_interactions(patient)
        serializer = VerificationInteractionsSerializer({"interactions": interactions})
        return Response(serializer.data)
