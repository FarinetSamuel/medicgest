from rest_framework import serializers

from .models import DATE_PUBLICATION_THESAURUS_ANSM


class InteractionDetecteeSerializer(serializers.Serializer):
    substance_a = serializers.CharField()
    substance_b = serializers.CharField()
    medicament_a = serializers.CharField()
    medicament_b = serializers.CharField()
    niveau = serializers.CharField()
    libelle = serializers.CharField()


class VerificationInteractionsSerializer(serializers.Serializer):
    """
    Enveloppe la liste des interactions détectées avec l'avertissement de
    fraîcheur des données — présent dans CHAQUE réponse, pas seulement
    documenté à part, pour qu'un consommateur de l'API ne puisse pas
    l'ignorer facilement.
    """

    interactions = InteractionDetecteeSerializer(many=True)
    avertissement = serializers.SerializerMethodField()
    date_publication_source = serializers.SerializerMethodField()

    def get_avertissement(self, obj):
        return (
            "Le Thésaurus des interactions médicamenteuses de l'ANSM n'est plus mis à "
            "jour depuis le 15/09/2023. Cette vérification ne couvre que les substances "
            "correctement rattachées au référentiel BDPM et les entrées à niveau de "
            "gravité non ambigu. Elle ne remplace jamais l'avis d'un pharmacien ou d'un "
            "médecin."
        )

    def get_date_publication_source(self, obj):
        return DATE_PUBLICATION_THESAURUS_ANSM
