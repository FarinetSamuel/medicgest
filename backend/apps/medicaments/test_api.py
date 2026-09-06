"""
Tests de l'endpoint /api/v1/medicaments/, en particulier la recherche
(?search=...) — search_fields était déclaré sur le ViewSet mais sans
filter_backends, donc totalement inopérant (vérifié : renvoyait la liste
complète non filtrée). Indispensable avec 15 857 médicaments réels pour
que le futur formulaire de prescription reste utilisable.
"""

from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from apps.utilisateurs.models import ROLE_ADMIN, Utilisateur

from .models import Medicament


class MedicamentRechercheAPITest(APITestCase):
    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user(
            username="admin", email="admin@example.com", password="motdepasse123"
        )
        groupe, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        self.utilisateur.groups.add(groupe)
        self.client.force_authenticate(self.utilisateur)

        Medicament.objects.create(code_cis="11111111", denomination="DOLIPRANE 1000 mg")
        Medicament.objects.create(code_cis="22222222", denomination="AMOXICILLINE 500 mg")
        Medicament.objects.create(code_cis="33333333", denomination="IBUPROFENE 400 mg")
        Medicament.objects.create(
            code_cis="CH-1111-1", denomination="DAFALGAN", source=Medicament.Source.SWISSMEDIC
        )

    def test_sans_recherche_renvoie_tout(self):
        response = self.client.get("/api/v1/medicaments/")
        self.assertEqual(response.data["count"], 4)

    def test_recherche_par_denomination_filtre_reellement(self):
        response = self.client.get("/api/v1/medicaments/?search=DOLIPRANE")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["denomination"], "DOLIPRANE 1000 mg")

    def test_recherche_par_denomination_insensible_a_la_casse(self):
        response = self.client.get("/api/v1/medicaments/?search=doliprane")
        self.assertEqual(response.data["count"], 1)

    def test_recherche_par_code_cis(self):
        response = self.client.get("/api/v1/medicaments/?search=222222")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["denomination"], "AMOXICILLINE 500 mg")

    def test_recherche_sans_resultat(self):
        response = self.client.get("/api/v1/medicaments/?search=INEXISTANT")
        self.assertEqual(response.data["count"], 0)


class MedicamentFiltreParPaysAPITest(APITestCase):
    """
    ?source=BDPM|SWISSMEDIC : le frontend choisit un pays et ne doit
    présenter que le référentiel correspondant (les deux catalogues ne
    sont jamais mélangés — noms de substances non rapprochables entre
    la BDPM en français et Swissmedic en latin).
    """

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user(
            username="admin2", email="admin2@example.com", password="motdepasse123"
        )
        groupe, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        self.utilisateur.groups.add(groupe)
        self.client.force_authenticate(self.utilisateur)

        Medicament.objects.create(code_cis="FR-1", denomination="DOLIPRANE")
        Medicament.objects.create(code_cis="FR-2", denomination="EFFERALGAN")
        Medicament.objects.create(
            code_cis="CH-1", denomination="DAFALGAN", source=Medicament.Source.SWISSMEDIC
        )

    def test_filtre_bdpm(self):
        response = self.client.get("/api/v1/medicaments/?source=BDPM")
        self.assertEqual(response.data["count"], 2)

    def test_filtre_swissmedic(self):
        response = self.client.get("/api/v1/medicaments/?source=SWISSMEDIC")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["denomination"], "DAFALGAN")

    def test_source_inconnue_ignoree(self):
        response = self.client.get("/api/v1/medicaments/?source=AUTRE")
        self.assertEqual(response.data["count"], 3)

    def test_combine_avec_la_recherche(self):
        response = self.client.get("/api/v1/medicaments/?source=BDPM&search=DOLIPRANE")
        self.assertEqual(response.data["count"], 1)
