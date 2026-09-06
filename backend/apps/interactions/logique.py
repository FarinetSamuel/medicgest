"""
Vérification des interactions entre les médicaments actuellement
prescrits à un patient.

Limitation documentée et assumée : la correspondance se fait par nom de
substance active exact (normalisé). Les protagonistes de type "classe
thérapeutique" (ex. "INDUCTEURS ENZYMATIQUES PUISSANTS") ne sont PAS
résolus vers leurs substances membres dans cette version — une
interaction définie au niveau d'une classe ne sera donc détectée que si
le protagoniste est écrit tel quel comme substance (ce qui n'est pas le
cas général). Ce point doit être clairement affiché à l'utilisateur.
"""

from dataclasses import dataclass

from apps.patients.models import Patient
from apps.prescriptions.models import Prescription

from .models import InteractionMedicamenteuse, DATE_PUBLICATION_THESAURUS_ANSM


@dataclass
class InteractionDetectee:
    substance_a: str
    substance_b: str
    medicament_a: str
    medicament_b: str
    niveau: str
    libelle: str


def substances_actives_prescrites(patient: Patient) -> dict[str, list[str]]:
    """
    {nom_substance: [noms_medicaments_concernes]} pour toutes les
    prescriptions actives du patient. Un même nom de substance peut
    provenir de plusieurs médicaments (ex. génériques).
    """
    prescriptions = Prescription.objects.filter(
        patient=patient, statut=Prescription.Statut.ACTIVE
    ).select_related("medicament").prefetch_related("medicament__substances_actives")

    resultat: dict[str, list[str]] = {}
    for prescription in prescriptions:
        medicament = prescription.medicament
        for substance in medicament.substances_actives.all():
            resultat.setdefault(substance.nom, []).append(medicament.denomination)
    return resultat


def medicaments_non_verifiables(patient: Patient) -> list[str]:
    """
    Noms des médicaments actuellement prescrits à ce patient dont les
    substances actives n'ont pas été rapprochées de façon fiable du
    Thésaurus (Medicament.verification_interactions_fiable=False — voir
    apps.medicaments.management.commands.import_swissmedic). Une absence
    d'interaction détectée pour ces médicaments ne veut pas dire
    "vérifié, rien trouvé" mais "non vérifiable" : à afficher séparément,
    jamais fondu dans le silence du cas "aucune interaction".
    """
    prescriptions = Prescription.objects.filter(
        patient=patient, statut=Prescription.Statut.ACTIVE
    ).select_related("medicament")
    noms = {
        prescription.medicament.denomination
        for prescription in prescriptions
        if not prescription.medicament.verification_interactions_fiable
    }
    return sorted(noms)


def verifier_interactions(patient: Patient) -> list[InteractionDetectee]:
    """
    Croise toutes les paires de substances actuellement prescrites à ce
    patient avec la table InteractionMedicamenteuse (correspondance
    exacte, dans les deux sens puisque le Thésaurus liste chaque paire
    une seule fois sous un ordre arbitraire A/B).
    """
    substances = substances_actives_prescrites(patient)
    noms_substances = list(substances.keys())

    detectees: list[InteractionDetectee] = []
    for i, substance_a in enumerate(noms_substances):
        for substance_b in noms_substances[i + 1:]:
            interaction = InteractionMedicamenteuse.objects.filter(
                protagoniste_a=substance_a, protagoniste_b=substance_b
            ).first() or InteractionMedicamenteuse.objects.filter(
                protagoniste_a=substance_b, protagoniste_b=substance_a
            ).first()

            if interaction:
                detectees.append(
                    InteractionDetectee(
                        substance_a=substance_a,
                        substance_b=substance_b,
                        medicament_a=", ".join(substances[substance_a]),
                        medicament_b=", ".join(substances[substance_b]),
                        niveau=interaction.niveau,
                        libelle=interaction.libelle,
                    )
                )
    return detectees
