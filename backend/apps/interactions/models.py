import uuid

from django.db import models

# Date de publication de la dernière (et dernière) version du Thésaurus.
# L'ANSM a officiellement arrêté sa mise à jour à cette date — voir
# https://ansm.sante.fr/documents/reference/thesaurus-des-interactions-medicamenteuses-1
DATE_PUBLICATION_THESAURUS_ANSM = "2023-09-15"


class InteractionMedicamenteuse(models.Model):
    """
    Une interaction entre deux protagonistes (substance active ou classe
    thérapeutique telle que nommée dans le Thésaurus), importée depuis le
    Thésaurus des interactions médicamenteuses de l'ANSM.

    ⚠️ Le Thésaurus n'est plus mis à jour par l'ANSM depuis le 15/09/2023
    (dernière version). Toute donnée ici doit être présentée à
    l'utilisateur avec cette date bien visible — voir
    apps.interactions.logique et le README.

    protagoniste_a / protagoniste_b sont stockés en texte brut (tel
    qu'écrit dans le Thésaurus, normalisé en MAJUSCULES), plutôt que liés
    à SubstanceActive : le Thésaurus mélange substances individuelles et
    classes thérapeutiques (ex. "INDUCTEURS ENZYMATIQUES PUISSANTS"), qui
    ne correspondent pas à une substance unique. Le rapprochement avec les
    substances réellement prescrites à un patient se fait par
    correspondance de texte (voir logique.py), avec ses limites
    documentées (une classe n'est pas résolue à ses substances membres
    dans cette première version).
    """

    class Niveau(models.TextChoices):
        CONTRE_INDICATION = "contre_indication", "Contre-indication"
        ASSOCIATION_DECONSEILLEE = "association_deconseillee", "Association déconseillée"
        PRECAUTION_EMPLOI = "precaution_emploi", "Précaution d'emploi"
        A_PRENDRE_EN_COMPTE = "a_prendre_en_compte", "À prendre en compte"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    protagoniste_a = models.CharField(max_length=255, db_index=True)
    protagoniste_b = models.CharField(max_length=255, db_index=True)
    niveau = models.CharField(max_length=30, choices=Niveau.choices)
    libelle = models.TextField(help_text="Texte explicatif complet tel qu'issu du Thésaurus.")

    source = models.CharField(max_length=100, default="Thésaurus ANSM", editable=False)
    date_publication_source = models.DateField(default=DATE_PUBLICATION_THESAURUS_ANSM)
    date_import = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Interaction médicamenteuse"
        verbose_name_plural = "Interactions médicamenteuses"
        constraints = [
            models.UniqueConstraint(
                fields=["protagoniste_a", "protagoniste_b"],
                name="paire_protagonistes_unique",
            )
        ]

    def __str__(self):
        return f"{self.protagoniste_a} + {self.protagoniste_b} ({self.get_niveau_display()})"


class InteractionNonImportee(models.Model):
    """
    Entrée du Thésaurus volontairement NON importée dans
    InteractionMedicamenteuse car son niveau de gravité est conditionnel
    (dose, contexte clinique, plusieurs niveaux combinés — ex. "CI - ASDEC
    - APEC"). Conservée pour permettre une revue manuelle plutôt que
    d'attribuer arbitrairement un seul niveau à une règle qui en a
    plusieurs selon le contexte.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    protagoniste_a = models.CharField(max_length=255)
    protagoniste_b = models.CharField(max_length=255)
    texte_brut = models.TextField()
    raison_exclusion = models.CharField(max_length=255)
    date_import = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Interaction non importée (à revoir manuellement)"
        verbose_name_plural = "Interactions non importées (à revoir manuellement)"

    def __str__(self):
        return f"{self.protagoniste_a} + {self.protagoniste_b} — {self.raison_exclusion}"
