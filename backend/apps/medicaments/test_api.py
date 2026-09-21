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


class MedicamentFiltreParPatientAPITest(APITestCase):
    """
    ?patient=<uuid> : le référentiel est celui du patient
    (Patient.referentiel_medicaments), décidé côté backend.
    """

    def setUp(self):
        import datetime

        from apps.patients.models import Patient
        from apps.utilisateurs.models import ROLE_PATIENT

        self.admin = Utilisateur.objects.create_user(
            username="admin3", email="admin3@example.com", password="motdepasse123"
        )
        self.admin.groups.add(Group.objects.get_or_create(name=ROLE_ADMIN)[0])
        self.user_patient = Utilisateur.objects.create_user(
            username="pat3", email="pat3@example.com", password="motdepasse123"
        )
        self.user_patient.groups.add(Group.objects.get_or_create(name=ROLE_PATIENT)[0])
        self.autre_user = Utilisateur.objects.create_user(
            username="pat4", email="pat4@example.com", password="motdepasse123"
        )
        self.autre_user.groups.add(Group.objects.get_or_create(name=ROLE_PATIENT)[0])
        self.patient_ch = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-REF-CH",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
            referentiel_medicaments=Medicament.Source.SWISSMEDIC,
        )
        self.patient_fr = Patient.objects.create(
            utilisateur=self.autre_user,
            numero_dossier="DOS-REF-FR",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        Medicament.objects.create(code_cis="FR-9", denomination="DOLIPRANE")
        Medicament.objects.create(code_cis="CH-9", denomination="DAFALGAN", source=Medicament.Source.SWISSMEDIC)

    def test_admin_voit_le_referentiel_du_patient(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/v1/medicaments/?patient={self.patient_ch.id}")
        self.assertEqual([m["denomination"] for m in response.data["results"]], ["DAFALGAN"])
        response = self.client.get(f"/api/v1/medicaments/?patient={self.patient_fr.id}")
        self.assertEqual([m["denomination"] for m in response.data["results"]], ["DOLIPRANE"])

    def test_patient_voit_le_referentiel_de_sa_fiche(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.get(f"/api/v1/medicaments/?patient={self.patient_ch.id}")
        self.assertEqual(response.data["count"], 1)

    def test_patient_inaccessible_donne_liste_vide(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.get(f"/api/v1/medicaments/?patient={self.patient_fr.id}")
        self.assertEqual(response.data["count"], 0)

    def test_identifiant_invalide_donne_liste_vide(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/medicaments/?patient=pas-un-uuid")
        self.assertEqual(response.data["count"], 0)
