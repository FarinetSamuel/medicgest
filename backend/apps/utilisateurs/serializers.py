from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

ROLES_VALIDES = (ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT)


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
