from rest_framework import serializers

from .logique import jours_restants_estimes
from .models import Boite, MouvementStock


class MouvementStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MouvementStock
        fields = ["id", "boite", "prise", "quantite", "motif", "date_creation"]
        read_only_fields = fields


class BoiteSerializer(serializers.ModelSerializer):
    medicament_nom = serializers.CharField(source="medicament.denomination", read_only=True)
    en_alerte_quantite = serializers.BooleanField(read_only=True)
    en_alerte_jours = serializers.BooleanField(read_only=True)
    en_alerte = serializers.BooleanField(read_only=True)
    jours_restants_estimes = serializers.SerializerMethodField()

    class Meta:
        model = Boite
        fields = [
            "id",
            "patient",
            "medicament",
            "medicament_nom",
            "quantite_initiale",
            "quantite_restante",
            "date_ouverture",
            "date_peremption",
            "delai_reappro_jours",
            "seuil_alerte_quantite",
            "seuil_alerte_jours",
            "statut",
            "en_alerte_quantite",
            "en_alerte_jours",
            "en_alerte",
            "jours_restants_estimes",
            "date_creation",
        ]
        read_only_fields = ["id", "statut", "date_creation"]
        extra_kwargs = {
            "quantite_restante": {"required": False},
        }

    def create(self, validated_data):
        # Par défaut, une boîte neuve est pleine : quantite_restante =
        # quantite_initiale si non précisée explicitement (ex. import
        # d'une boîte déjà entamée).
        validated_data.setdefault("quantite_restante", validated_data["quantite_initiale"])
        return super().create(validated_data)

    def get_jours_restants_estimes(self, obj):
        """
        Estimation toutes boîtes actives confondues (patient+médicament),
        pas seulement cette boîte — voir logique.jours_restants_estimes.
        Retourné en float pour le JSON ; None si non calculable.
        """
        jours = jours_restants_estimes(obj.patient, obj.medicament)
        return round(float(jours), 1) if jours is not None else None
