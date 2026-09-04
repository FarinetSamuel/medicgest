import datetime
from decimal import Decimal

from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from apps.medicaments.models import Medicament
from apps.patients.models import Patient, PatientMedecin
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .models import Boite


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(username=email.split("@")[0], email=email, password="x")
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class BoiteAPITest(APITestCase):
    def setUp(self):
        self.medecin_suiveur = creer_utilisateur_avec_role("medstockapi1@example.com", ROLE_MEDECIN)
        self.medecin_autre = creer_utilisateur_avec_role("medstockapi2@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patstockapi1@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-STOCK-API-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin_suiveur, actif=True)
        self.medicament = Medicament.objects.create(code_cis="STKAPI1", denomination="STOCKAPIOL")

    def test_patient_peut_creer_sa_propre_boite(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/boites/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "quantite_initiale": "30.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        # quantite_restante par défaut = quantite_initiale
        self.assertEqual(response.data["quantite_restante"], "30.00")

    def test_medecin_suiveur_voit_les_boites_du_patient(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=30, quantite_restante=30,
        )
        self.client.force_authenticate(self.medecin_suiveur)
        response = self.client.get("/api/v1/boites/")
        self.assertEqual(len(response.data["results"]), 1)

    def test_medecin_non_suiveur_ne_voit_rien(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=30, quantite_restante=30,
        )
        self.client.force_authenticate(self.medecin_autre)
        response = self.client.get("/api/v1/boites/")
        self.assertEqual(response.data["results"], [])

    def test_autre_patient_ne_voit_pas_cette_boite(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=30, quantite_restante=30,
        )
        autre_user_patient = creer_utilisateur_avec_role("patstockapi2@example.com", ROLE_PATIENT)
        self.client.force_authenticate(autre_user_patient)
        response = self.client.get("/api/v1/boites/")
        self.assertEqual(response.data["results"], [])

    def test_autre_patient_ne_peut_pas_creer_une_boite_pour_ce_patient(self):
        autre_user_patient = creer_utilisateur_avec_role("patstockapi3@example.com", ROLE_PATIENT)
        self.client.force_authenticate(autre_user_patient)
        response = self.client.post(
            "/api/v1/boites/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "quantite_initiale": "30.00",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Boite.objects.count(), 0)

    def test_medecin_non_suiveur_ne_peut_pas_creer_une_boite(self):
        self.client.force_authenticate(self.medecin_autre)
        response = self.client.post(
            "/api/v1/boites/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "quantite_initiale": "30.00",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Boite.objects.count(), 0)

    def test_champ_en_alerte_expose_dans_l_api(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=30, quantite_restante=2, seuil_alerte_quantite=5,
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.get("/api/v1/boites/")
        self.assertTrue(response.data["results"][0]["en_alerte"])
        self.assertTrue(response.data["results"][0]["en_alerte_quantite"])

    def test_mouvements_stock_en_lecture_seule(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=30, quantite_restante=30,
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/mouvements-stock/", {"boite": str(boite.id), "quantite": "-5"}
        )
        self.assertEqual(response.status_code, 405)
