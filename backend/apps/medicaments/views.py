from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Medicament
from .serializers import MedicamentSerializer


class MedicamentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Référentiel médicaments, consultable par tous les rôles authentifiés.
    ReadOnlyModelViewSet : aucune route de création/modification/suppression
    n'existe même dans l'URLconf — le référentiel ne peut être modifié que
    par la commande import_bdpm, jamais via l'API.

    filter_backends + SearchFilter : sans eux, `search_fields` ne fait
    STRICTEMENT RIEN (vérifié : ?search=... renvoyait la liste complète,
    non filtrée, avant cet ajout) — indispensable avec 15 857 médicaments
    réels pour permettre un vrai champ de recherche côté frontend plutôt
    que de parcourir des centaines de pages.
    """

    queryset = Medicament.objects.all()
    serializer_class = MedicamentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["denomination", "code_cis"]
