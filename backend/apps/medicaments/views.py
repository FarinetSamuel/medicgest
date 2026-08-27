from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Medicament
from .serializers import MedicamentSerializer


class MedicamentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Référentiel médicaments, consultable par tous les rôles authentifiés.
    ReadOnlyModelViewSet : aucune route de création/modification/suppression
    n'existe même dans l'URLconf — le référentiel ne peut être modifié que
    par la commande import_bdpm, jamais via l'API.
    """

    queryset = Medicament.objects.all()
    serializer_class = MedicamentSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["denomination", "code_cis"]
