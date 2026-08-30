"""
Tests des endpoints API DRF de l'app utilisateurs et de leurs permissions
par rôle — en particulier la restriction de lecture ouverte au médecin
(get_queryset filtré aux comptes "patient" actifs uniquement).
"""

from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from .models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur


def creer_utilisateur_avec_role(email, role, actif=True):
    user = Utilisateur.objects.create_user(
        username=email.split("@")[0], email=email, password="motdepasse123", actif=actif
    )
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class UtilisateurAPIPermissionsTest(APITestCase):
    def setUp(self):
        self.admin = creer_utilisateur_avec_role("admin@example.com", ROLE_ADMIN)
        self.medecin = creer_utilisateur_avec_role("medecin@example.com", ROLE_MEDECIN)
        self.patient_actif = creer_utilisateur_avec_role("patient.actif@example.com", ROLE_PATIENT)
        self.patient_inactif = creer_utilisateur_avec_role(
            "patient.inactif@example.com", ROLE_PATIENT, actif=False
        )

    # --- Accès anonyme ---

    def test_liste_anonyme_refusee(self):
        response = self.client.get("/api/v1/utilisateurs/")
        self.assertEqual(response.status_code, 403)

    # --- Lecture (list) ---

    def test_admin_voit_tous_les_comptes(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/utilisateurs/")
        self.assertEqual(response.status_code, 200)
        emails = {u["email"] for u in response.data["results"]}
        self.assertEqual(
            emails,
            {
                "admin@example.com",
                "medecin@example.com",
                "patient.actif@example.com",
                "patient.inactif@example.com",
            },
        )

    def test_medecin_ne_voit_que_les_comptes_patient_actifs(self):
        """
        Un médecin doit pouvoir lister les comptes pour associer un compte
        existant à une nouvelle fiche Patient, mais jamais voir les autres
        comptes admin/médecin, ni les comptes patient désactivés.
        """
        self.client.force_authenticate(self.medecin)
        response = self.client.get("/api/v1/utilisateurs/")
        self.assertEqual(response.status_code, 200)
        emails = {u["email"] for u in response.data["results"]}
        self.assertEqual(emails, {"patient.actif@example.com"})

    def test_patient_ne_peut_pas_lister_les_comptes(self):
        self.client.force_authenticate(self.patient_actif)
        response = self.client.get("/api/v1/utilisateurs/")
        self.assertEqual(response.status_code, 403)

    def test_medecin_peut_consulter_un_compte_patient(self):
        self.client.force_authenticate(self.medecin)
        response = self.client.get(f"/api/v1/utilisateurs/{self.patient_actif.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "patient.actif@example.com")

    def test_medecin_ne_peut_pas_consulter_un_compte_admin(self):
        """
        404, pas 403 : le compte admin est hors du queryset filtré pour un
        médecin, donc invisible plutôt qu'explicitement refusé — évite de
        confirmer l'existence d'un compte que le médecin ne doit pas voir.
        """
        self.client.force_authenticate(self.medecin)
        response = self.client.get(f"/api/v1/utilisateurs/{self.admin.id}/")
        self.assertEqual(response.status_code, 404)

    # --- Écriture (create/update/delete) : réservée à l'admin ---

    def test_medecin_ne_peut_pas_creer_de_compte(self):
        self.client.force_authenticate(self.medecin)
        response = self.client.post(
            "/api/v1/utilisateurs/",
            {
                "email": "nouveau@example.com",
                "first_name": "Nouveau",
                "last_name": "Compte",
                "password": "motdepasse123",
                "role": ROLE_PATIENT,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_peut_creer_un_compte_patient(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/utilisateurs/",
            {
                "email": "nouveau@example.com",
                "first_name": "Nouveau",
                "last_name": "Compte",
                "password": "motdepasse123",
                "role": ROLE_PATIENT,
            },
        )
        self.assertEqual(response.status_code, 201)
        cree = Utilisateur.objects.get(email="nouveau@example.com")
        self.assertEqual(cree.role, ROLE_PATIENT)

    def test_medecin_ne_peut_pas_modifier_un_compte(self):
        self.client.force_authenticate(self.medecin)
        response = self.client.patch(
            f"/api/v1/utilisateurs/{self.patient_actif.id}/", {"first_name": "Modifié"}
        )
        self.assertEqual(response.status_code, 403)

    def test_medecin_ne_peut_pas_supprimer_un_compte(self):
        self.client.force_authenticate(self.medecin)
        response = self.client.delete(f"/api/v1/utilisateurs/{self.patient_actif.id}/")
        self.assertEqual(response.status_code, 403)
