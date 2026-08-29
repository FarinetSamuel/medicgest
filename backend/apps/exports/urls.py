from django.urls import path

from .views import ExportExcelPatientView, ExportPdfPatientView

urlpatterns = [
    path("patients/<uuid:patient_id>/export-pdf/", ExportPdfPatientView.as_view(), name="export-pdf-patient"),
    path("patients/<uuid:patient_id>/export-excel/", ExportExcelPatientView.as_view(), name="export-excel-patient"),
]
