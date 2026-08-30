from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

ROLES_VALIDES = (ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT)


class ConnexionSerializer(TokenObtainPairSerializer):
    """
    Émission de jetons JWT (access + refresh) à la connexion.

    TokenObtainPairSerializer construit déjà son champ d'identifiant à
    partir de Utilisateur.USERNAME_FIELD ("email"), donc {"email": ...,
    "password": ...} est accepté tel quel sans configuration supplémentaire.

    Ajout nécessaire : le champ `actif` du modèle est un champ métier
    distinct du `is_active` natif de Django (jamais mis à False ailleurs
    dans le code) — sans cette vérification explicite, un compte désactivé
    pourrait quand même se connecter.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.actif:
            raise serializers.ValidationError(
                "Ce compte est désactivé.", code="compte_desactive"
            )
        return data


class ProfilSerializer(serializers.ModelSerializer):
    """Profil de l'utilisateur connecté, renvoyé par GET /auth/me/."""

    prenom = serializers.CharField(source="first_name", read_only=True)
    nom = serializers.CharField(source="last_name", read_only=True)
    role = serializers.CharField(read_only=True)
    patient_id = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = ["id", "email", "prenom", "nom", "role", "patient_id"]

    def get_patient_id(self, obj):
        fiche = getattr(obj, "fiche_patient", None)
        return str(fiche.id) if fiche else None


class UtilisateurSerializer(serializers.ModelSerializer):
    """Lecture (et mise à jour des champs simples) d'un utilisateur."""

    role = serializers.CharField(read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "actif",
            "date_creation",
        ]
        read_only_fields = ["id", "date_creation"]


class UtilisateurCreationSerializer(serializers.ModelSerializer):
    """
    Création d'un utilisateur par un administrateur : nécessite un mot de
    passe et un rôle, qui ne sont pas des champs directs du modèle
    (le rôle est un Group, le mot de passe doit être hashé).
    """

    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=ROLES_VALIDES, write_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "role",
            "actif",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        role = validated_data.pop("role")
        password = validated_data.pop("password")
        # username est requis par AbstractUser : on le dérive de l'email
        # pour ne pas exposer un champ redondant côté API.
        validated_data.setdefault("username", validated_data["email"])

        utilisateur = Utilisateur(**validated_data)
        utilisateur.set_password(password)
        utilisateur.save()

        groupe, _ = Group.objects.get_or_create(name=role)
        utilisateur.groups.add(groupe)
        return utilisateur
