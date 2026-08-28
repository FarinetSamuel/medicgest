from rest_framework import serializers

from .models import HoraireProgramme, Prescription, Prise


class HoraireProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoraireProgramme
        fields = ["id", "prescription", "heure", "quantite", "actif"]
        read_only_fields = ["id"]


class PrescriptionSerializer(serializers.ModelSerializer):
    medicament_nom = serializers.CharField(source="medicament.denomination", read_only=True)
    horaires = HoraireProgrammeSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "patient",
            "medicament",
            "medicament_nom",
            "medecin_prescripteur",
            "type_prise",
            "dose_quantite",
            "dose_unite",
            "frequence_par_jour",
            "dose_max_par_jour",
            "date_debut",
            "date_fin",
            "instructions",
            "statut",
            "horaires",
            "date_creation",
        ]
        read_only_fields = ["id", "medecin_prescripteur", "date_creation"]

    def validate(self, attrs):
        type_prise = attrs.get("type_prise") or getattr(self.instance, "type_prise", None)
        if type_prise == Prescription.TypePrise.REGULIERE and attrs.get("dose_max_par_jour"):
            raise serializers.ValidationError(
                "dose_max_par_jour ne s'applique qu'aux prescriptions de type 'reserve'."
            )
        return attrs


class PriseSerializer(serializers.ModelSerializer):
    alerte_depassement = serializers.BooleanField(read_only=True)

    class Meta:
        model = Prise
        fields = [
            "id",
            "prescription",
            "horaire_programme",
            "date_heure_prevue",
            "date_heure_reelle",
            "quantite_prevue",
            "quantite_prise",
            "statut",
            "enregistre_par",
            "alerte_depassement",
            "commentaire",
            "date_creation",
            "date_modification",
        ]
        read_only_fields = ["id", "enregistre_par", "alerte_depassement", "date_creation", "date_modification"]
