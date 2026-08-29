from django.template.loader import render_to_string
from weasyprint import HTML

from .donnees import rassembler_donnees_patient


def generer_pdf_patient(patient) -> bytes:
    contexte = rassembler_donnees_patient(patient)
    html = render_to_string("exports/rapport_patient.html", contexte)
    return HTML(string=html).write_pdf()
