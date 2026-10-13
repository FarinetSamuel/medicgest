from django.template.loader import render_to_string
from weasyprint import HTML

from .donnees import (
    CONTENU_A_VENIR,
    CONTENU_COMPLET,
    rassembler_besoins_a_venir,
    rassembler_donnees_patient,
)


def generer_pdf_patient(patient, contenu: str = CONTENU_COMPLET, **filtres) -> bytes:
    """
    contenu choisit les sections du PDF (voir donnees.CONTENUS) ; filtres
    est transmis tel quel à rassembler_donnees_patient. Pour le contenu
    "a_venir", date_debut et date_fin sont obligatoires et délimitent la
    période à venir (voir rassembler_besoins_a_venir).
    """
    if contenu == CONTENU_A_VENIR:
        contexte = rassembler_donnees_patient(patient)
        contexte.update(
            rassembler_besoins_a_venir(patient, filtres["date_debut"], filtres["date_fin"])
        )
    else:
        contexte = rassembler_donnees_patient(patient, **filtres)
    contexte["contenu"] = contenu
    html = render_to_string("exports/rapport_patient.html", contexte)
    return HTML(string=html).write_pdf()
