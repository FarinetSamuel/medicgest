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


def valider_specialite(attrs, instance=None):
    """
    Partagée entre création et mise à jour : si specialite="autre",
    specialite_autre doit être renseigné — sinon on se retrouve avec un
    compte médecin affiché comme "Autre" sans aucune précision.
    """
    specialite = attrs.get("specialite", getattr(instance, "specialite", ""))
    specialite_autre = attrs.get("specialite_autre", getattr(instance, "specialite_autre", ""))
    if specialite == Utilisateur.Specialite.AUTRE and not specialite_autre.strip():
        raise serializers.ValidationError(
            {"specialite_autre": "Précisez la spécialité lorsque « Autre » est sélectionné."}
        )
    return attrs


class UtilisateurSerializer(serializers.ModelSerializer):
    """
    Lecture (et mise à jour des champs simples) d'un utilisateur.

    `password` est facultatif et write-only : absent, le mot de passe
    existant n'est pas touché. Fourni, il réinitialise le mot de passe du
    compte — réservé aux administrateurs (voir UtilisateurViewSet.get_permissions).
    """

    role = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "specialite",
            "specialite_autre",
            "actif",
            "date_creation",
            "password",
        ]
        read_only_fields = ["id", "date_creation"]

    def validate(self, attrs):
        return valider_specialite(attrs, instance=self.instance)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance


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
            "specialite",
            "specialite_autre",
            "actif",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        return valider_specialite(attrs)

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
