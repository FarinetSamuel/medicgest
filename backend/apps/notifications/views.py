from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.utilisateurs.models import ROLE_ADMIN

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Consultation de ses propres notifications, et marquage comme lue.
    Pas de création/suppression via l'API : une notification est toujours
    générée par le backend (rappels, alertes), jamais par le client.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = Notification.objects.select_related("destinataire")
        if user.role == ROLE_ADMIN:
            return base
        return base.filter(destinataire=user)
