from rest_framework import serializers

from .models import Medicament


class MedicamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicament
        fields = [
            "id",
            "code_cis",
            "denomination",
            "forme_pharmaceutique",
            "dosage",
            "laboratoire",
            "code_atc",
            "source",
            "date_import",
        ]
