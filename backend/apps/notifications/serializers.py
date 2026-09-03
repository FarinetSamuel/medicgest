from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "canal", "categorie", "titre", "message",
            "prise", "boite", "prescription", "statut", "date_creation", "date_envoi",
        ]
        read_only_fields = [
            "id", "canal", "categorie", "titre", "message",
            "prise", "boite", "prescription", "date_creation", "date_envoi",
        ]

    def validate_statut(self, value):
        # Seule transition autorisée par le destinataire lui-même : passer
        # une notification in_app à "lue". Tout le reste (envoi, échec)
        # est géré par le backend, jamais par le client.
        if value != Notification.Statut.LUE:
            raise serializers.ValidationError(
                "Seul le passage au statut 'lue' est autorisé via l'API."
            )
        return value
