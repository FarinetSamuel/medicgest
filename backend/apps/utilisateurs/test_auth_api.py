"""
Tests du flux d'authentification JWT : /auth/token/, /auth/token/refresh/,
/auth/me/. Ces endpoints n'existaient pas avant — ajoutés après avoir
constaté que le frontend les appelait sans qu'ils soient jamais câblés
côté backend (le "auth JWT fonctionnel" du résumé de projet ne
correspondait pas à l'état réel du code).
"""

import datetime

from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from apps.patients.models import Patient

from .models import ROLE_ADMIN, ROLE_PATIENT, Utilisateur


def creer_utilisateur_avec_role(email, role, actif=True, **extra):
    user = Utilisateur.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="motdepasse123",
        actif=actif,
        **extra,
    )
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class AuthentificationAPITest(APITestCase):
    def setUp(self):
        self.admin = creer_utilisateur_avec_role(
            "admin@example.com", ROLE_ADMIN, first_name="Test", last_name="Admin"
        )
        self.desactive = creer_utilisateur_avec_role("desactive@example.com", ROLE_PATIENT, actif=False)
        self.patient_user = creer_utilisateur_avec_role(
            "patient1@example.com", ROLE_PATIENT, first_name="Camille", last_name="Martin"
        )
        self.patient_fiche = Patient.objects.create(
            utilisateur=self.patient_user,
            numero_dossier="DOS-AUTH-1",
            date_naissance=datetime.date(1990, 1, 1),
            sexe="F",
        )

    def test_connexion_identifiants_valides_renvoie_les_jetons(self):
        response = self.client.post(
            "/api/v1/auth/token/", {"email": "admin@example.com", "password": "motdepasse123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_connexion_mauvais_mot_de_passe_renvoie_401(self):
        response = self.client.post(
            "/api/v1/auth/token/", {"email": "admin@example.com", "password": "mauvais"}
        )
        self.assertEqual(response.status_code, 401)

    def test_connexion_email_inconnu_renvoie_401(self):
        response = self.client.post(
            "/api/v1/auth/token/", {"email": "inconnu@example.com", "password": "motdepasse123"}
        )
        self.assertEqual(response.status_code, 401)

    def test_connexion_compte_desactive_refusee(self):
        """
        Le champ `actif` (métier) n'est pas le `is_active` natif de Django :
        sans la vérification explicite dans ConnexionSerializer, ce test
        échouerait silencieusement (connexion acceptée à tort).
        """
        response = self.client.post(
            "/api/v1/auth/token/", {"email": "desactive@example.com", "password": "motdepasse123"}
        )
        self.assertEqual(response.status_code, 400)

    def test_refresh_token_renvoie_un_nouvel_access(self):
        connexion = self.client.post(
            "/api/v1/auth/token/", {"email": "admin@example.com", "password": "motdepasse123"}
        )
        response = self.client.post("/api/v1/auth/token/refresh/", {"refresh": connexion.data["refresh"]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_profil_sans_authentification_refuse(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_profil_admin_ne_renvoie_pas_de_patient_id(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "admin")
        self.assertIsNone(response.data["patient_id"])

    def test_profil_patient_renvoie_son_patient_id_et_son_nom(self):
        self.client.force_authenticate(self.patient_user)
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["prenom"], "Camille")
        self.assertEqual(response.data["nom"], "Martin")
        self.assertEqual(response.data["patient_id"], str(self.patient_fiche.id))
