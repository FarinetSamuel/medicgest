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
        read_only_fields = ["id", "date_creation"]
        extra_kwargs = {
            # Pas read_only : un admin doit pouvoir le renseigner à la
            # création (voir PrescriptionViewSet.perform_create). Pas
            # required=True non plus : un médecin ne l'envoie jamais dans
            # le payload, la vue l'assigne elle-même à request.user via
            # serializer.save(medecin_prescripteur=user), qui l'écrase de
            # toute façon — donc aucun risque qu'un médecin usurpe un
            # autre prescripteur en le passant dans le payload.
            "medecin_prescripteur": {"required": False},
        }

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
