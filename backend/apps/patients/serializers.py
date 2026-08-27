from rest_framework import serializers

from .models import NoteMedicale, Patient, PatientMedecin


class NoteMedicaleSerializer(serializers.ModelSerializer):
    saisi_par_email = serializers.EmailField(source="saisi_par.email", read_only=True)

    class Meta:
        model = NoteMedicale
        fields = [
            "id",
            "patient",
            "categorie",
            "contenu",
            "saisi_par_email",
            "date_creation",
        ]
        read_only_fields = ["id", "date_creation"]


class PatientMedecinSerializer(serializers.ModelSerializer):
    medecin_email = serializers.EmailField(source="medecin.email", read_only=True)

    class Meta:
        model = PatientMedecin
        fields = ["id", "patient", "medecin", "medecin_email", "actif", "date_debut", "date_fin"]
        read_only_fields = ["id", "date_debut"]


class PatientSerializer(serializers.ModelSerializer):
    utilisateur_email = serializers.EmailField(source="utilisateur.email", read_only=True)
    notes_medicales = NoteMedicaleSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "utilisateur",
            "utilisateur_email",
            "numero_dossier",
            "date_naissance",
            "sexe",
            "contact_urgence_nom",
            "contact_urgence_telephone",
            "contact_urgence_lien",
            "notes_medicales",
            "date_creation",
            "date_modification",
        ]
        read_only_fields = ["id", "date_creation", "date_modification"]
