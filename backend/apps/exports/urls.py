from django.urls import path

from .views import ExportExcelPatientView, ExportOptionsPatientView, ExportPdfPatientView

urlpatterns = [
    path("patients/<uuid:patient_id>/export-pdf/", ExportPdfPatientView.as_view(), name="export-pdf-patient"),
    path("patients/<uuid:patient_id>/export-excel/", ExportExcelPatientView.as_view(), name="export-excel-patient"),
    path("patients/<uuid:patient_id>/export-options/", ExportOptionsPatientView.as_view(), name="export-options-patient"),
]
