import datetime
import uuid

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import Patient
from apps.patients.permissions import medecin_suit_patient
from apps.prescriptions.models import Prescription
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT

from .donnees import (
    CONTENU_A_VENIR,
    CONTENU_COMPLET,
    CONTENU_PRESCRIPTIONS,
    CONTENU_PRISES,
    CONTENU_STOCK,
    CONTENUS,
    nom_affiche,
)
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


def _lire_date(request, nom) -> datetime.date | None:
    valeur = request.query_params.get(nom)
    if not valeur:
        return None
    try:
        return datetime.date.fromisoformat(valeur)
    except ValueError:
        raise ValidationError({nom: "Date invalide (format attendu : AAAA-MM-JJ)."})


def _lire_options_pdf(request) -> dict:
    """Valide les paramètres de requête de l'export PDF (tous facultatifs)."""
    params = request.query_params

    contenu = params.get("contenu") or CONTENU_COMPLET
    if contenu not in CONTENUS:
        raise ValidationError({"contenu": f"Valeurs acceptées : {', '.join(CONTENUS)}."})

    date_debut = _lire_date(request, "date_debut")
    date_fin = _lire_date(request, "date_fin")
    if bool(date_debut) != bool(date_fin):
        raise ValidationError("date_debut et date_fin doivent être fournies ensemble.")
    if date_debut and date_debut > date_fin:
        raise ValidationError({"date_fin": "La date de fin précède la date de début."})
    if contenu == CONTENU_A_VENIR:
        if not date_debut:
            raise ValidationError("date_debut et date_fin sont requises pour ce contenu.")
        if date_fin < timezone.localdate():
            raise ValidationError({"date_fin": "La période doit se terminer aujourd'hui ou plus tard."})

    medecin_id = params.get("medecin") or None
    if medecin_id:
        try:
            medecin_id = uuid.UUID(medecin_id)
        except ValueError:
            raise ValidationError({"medecin": "Identifiant de médecin invalide."})

    return {
        "contenu": contenu,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "medecin_id": medecin_id,
        "inclure_inactives": params.get("inclure_inactives", "").lower() in ("1", "true"),
    }


PREFIXES_FICHIER_PDF = {
    CONTENU_COMPLET: "rapport",
    CONTENU_PRESCRIPTIONS: "prescriptions",
    CONTENU_PRISES: "prises",
    CONTENU_STOCK: "stock",
    CONTENU_A_VENIR: "prises-a-venir",
}


class ExportPdfPatientView(APIView):
    """
    GET /api/v1/patients/<id>/export-pdf/ — PDF du patient.

    Paramètres de requête, tous facultatifs :
    - contenu : "complet" (défaut), "prescriptions" (regroupées par
      médecin prescripteur), "prises" (prises effectuées + total par
      médicament), "stock" (boîtes actives) ou "a_venir" (prises prévues
      sur une période à venir et stock correspondant) ;
    - date_debut, date_fin (AAAA-MM-JJ, bornes incluses, à fournir
      ensemble) : période des prises ; sans elles, les 30 derniers jours.
      Obligatoires pour "a_venir", dont la période ne peut pas être
      entièrement passée ;
    - medecin : restreint le contenu "prescriptions" à ce prescripteur ;
    - inclure_inactives=true : ajoute au contenu "prescriptions" les
      prescriptions arrêtées et terminées.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = _recuperer_patient_autorise(request, patient_id)
        options = _lire_options_pdf(request)
        contenu_pdf = generer_pdf_patient(patient, **options)

        reponse = HttpResponse(contenu_pdf, content_type="application/pdf")
        nom_fichier = f"{PREFIXES_FICHIER_PDF[options['contenu']]}-{patient.numero_dossier}.pdf"
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


class ExportOptionsPatientView(APIView):
    """
    GET /api/v1/patients/<id>/export-options/ — choix proposés par le menu
    d'export : les médecins ayant rédigé au moins une prescription pour ce
    patient (un médecin ou un patient ne peut pas parcourir /utilisateurs/).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = _recuperer_patient_autorise(request, patient_id)
        medecins = {
            p.medecin_prescripteur
            for p in Prescription.objects.filter(patient=patient).select_related(
                "medecin_prescripteur"
            )
        }
        return Response(
            {
                "medecins": sorted(
                    ({"id": str(m.id), "nom": nom_affiche(m)} for m in medecins),
                    key=lambda m: m["nom"].lower(),
                )
            }
        )
