from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.patients.models import Patient
from apps.patients.permissions import medecin_suit_patient
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT

from .excel import generer_excel_patient
from .pdf import generer_pdf_patient


def _recuperer_patient_autorise(request, patient_id) -> Patient:
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
        raise NotFound()
    return patient


class ExportPdfPatientView(APIView):
    """GET /api/v1/patients/<id>/export-pdf/ — rapport complet en PDF."""

    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = _recuperer_patient_autorise(request, patient_id)
        contenu_pdf = generer_pdf_patient(patient)

        reponse = HttpResponse(contenu_pdf, content_type="application/pdf")
        nom_fichier = f"rapport-{patient.numero_dossier}.pdf"
        reponse["Content-Disposition"] = f'attachment; filename="{nom_fichier}"'
        return reponse


class ExportExcelPatientView(APIView):
    """GET /api/v1/patients/<id>/export-excel/ — rapport complet en Excel."""

    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = _recuperer_patient_autorise(request, patient_id)
        contenu_excel = generer_excel_patient(patient)

        reponse = HttpResponse(
            contenu_excel,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        nom_fichier = f"rapport-{patient.numero_dossier}.xlsx"
        reponse["Content-Disposition"] = f'attachment; filename="{nom_fichier}"'
        return reponse
