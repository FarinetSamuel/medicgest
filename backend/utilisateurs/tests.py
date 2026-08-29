from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur


class UtilisateurModelTest(TestCase):
    def test_creation_utilisateur_basique(self):
        """Un utilisateur se crée avec un email et un mot de passe hashé."""
        user = Utilisateur.objects.create_user(
            username="jdupont",
            email="jean.dupont@example.com",
            password="mot-de-passe-solide-123",
            first_name="Jean",
            last_name="Dupont",
        )
        self.assertNotEqual(user.password, "mot-de-passe-solide-123")
        self.assertTrue(user.check_password("mot-de-passe-solide-123"))

    def test_email_est_le_champ_de_connexion(self):
        """USERNAME_FIELD doit être 'email', conformément à la conception."""
        self.assertEqual(Utilisateur.USERNAME_FIELD, "email")

    def test_email_unique(self):
        """Deux comptes ne peuvent pas partager le même email."""
        Utilisateur.objects.create_user(
            username="u1", email="dup@example.com", password="x"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Utilisateur.objects.create_user(
                    username="u2", email="dup@example.com", password="x"
                )

    def test_role_reflete_le_groupe_django(self):
        """La propriété `role` doit refléter le Group auquel appartient l'utilisateur."""
        groupe_medecin, _ = Group.objects.get_or_create(name=ROLE_MEDECIN)
        user = Utilisateur.objects.create_user(
            username="medecin1", email="medecin1@example.com", password="x"
        )
        self.assertEqual(user.role, "sans_role")

        user.groups.add(groupe_medecin)
        self.assertEqual(user.role, ROLE_MEDECIN)

    def test_utilisateur_inactif_par_defaut_actif(self):
        """Le champ `actif` doit valoir True par défaut à la création."""
        user = Utilisateur.objects.create_user(
            username="u3", email="u3@example.com", password="x"
        )
        self.assertTrue(user.actif)


class GroupesRolesMigrationTest(TestCase):
    def test_les_trois_groupes_metier_existent(self):
        """
        La migration de données 0002_creer_groupes_roles doit avoir créé
        les trois groupes attendus dès l'installation, sans action manuelle.
        """
        noms = set(Group.objects.values_list("name", flat=True))
        self.assertIn(ROLE_ADMIN, noms)
        self.assertIn(ROLE_MEDECIN, noms)
        self.assertIn(ROLE_PATIENT, noms)


class AuthentificationJWTTest(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="jwtuser", email="jwtuser@example.com", password="mot-de-passe-solide-123"
        )
        groupe, _ = Group.objects.get_or_create(name=ROLE_MEDECIN)
        self.user.groups.add(groupe)

    def test_obtention_token_avec_email(self):
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.post(
            "/api/v1/auth/token/",
            {"email": "jwtuser@example.com", "password": "mot-de-passe-solide-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_endpoint_me_retourne_le_role(self):
        from rest_framework.test import APIClient

        client = APIClient()
        reponse_token = client.post(
            "/api/v1/auth/token/",
            {"email": "jwtuser@example.com", "password": "mot-de-passe-solide-123"},
        )
        access = reponse_token.data["access"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "jwtuser@example.com")
        self.assertEqual(response.data["role"], ROLE_MEDECIN)

    def test_mauvais_mot_de_passe_refuse(self):
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.post(
            "/api/v1/auth/token/",
            {"email": "jwtuser@example.com", "password": "mauvais-mot-de-passe"},
        )
        self.assertEqual(response.status_code, 401)
