"""
Tests des endpoints API DRF et de leurs permissions par rôle.

Ces tests utilisent APIClient pour effectuer de vraies requêtes HTTP
contre les vues, pas juste vérifier le code des permissions isolément.
"""

import datetime

from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .models import NoteMedicale, Patient, PatientMedecin


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(
        username=email.split("@")[0], email=email, password="motdepasse123"
    )
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class PatientAPIPermissionsTest(APITestCase):
    def setUp(self):
        self.admin = creer_utilisateur_avec_role("admin@example.com", ROLE_ADMIN)
        self.medecin_a = creer_utilisateur_avec_role("medecin.a@example.com", ROLE_MEDECIN)
        self.medecin_b = creer_utilisateur_avec_role("medecin.b@example.com", ROLE_MEDECIN)

        self.user_patient_1 = creer_utilisateur_avec_role("patient1@example.com", ROLE_PATIENT)
        self.user_patient_1.first_name = "Camille"
        self.user_patient_1.last_name = "Martin"
        self.user_patient_1.save()
        self.patient_1 = Patient.objects.create(
            utilisateur=self.user_patient_1,
            numero_dossier="DOS-API-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.user_patient_2 = creer_utilisateur_avec_role("patient2@example.com", ROLE_PATIENT)
        self.patient_2 = Patient.objects.create(
            utilisateur=self.user_patient_2,
            numero_dossier="DOS-API-2",
            date_naissance=datetime.date(1990, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        # Seul medecin_a suit patient_1 ; medecin_b ne suit personne.
        PatientMedecin.objects.create(patient=self.patient_1, medecin=self.medecin_a, actif=True)

    # --- Accès non authentifié ---

    def test_acces_anonyme_refuse(self):
        """
        403, pas 401 : comportement standard de DRF quand
        SessionAuthentication est en tête des authenticators — elle ne
        fournit pas de challenge WWW-Authenticate, donc DRF « rétrograde »
        NotAuthenticated (401) en PermissionDenied (403). Voir
        rest_framework.views.APIView.handle_exception.
        """
        response = self.client.get("/api/v1/patients/")
        self.assertEqual(response.status_code, 403)

    # --- Périmètre de visibilité par rôle (get_queryset) ---

    def test_admin_voit_tous_les_patients(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/patients/")
        dossiers = {p["numero_dossier"] for p in response.data["results"]}
        self.assertEqual(dossiers, {"DOS-API-1", "DOS-API-2"})

    def test_serialisation_expose_prenom_nom_patient(self):
        """
        Le frontend a besoin du prénom/nom du patient (pas seulement de son
        email) pour l'afficher dans la liste et la fiche détail.
        """
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/v1/patients/{self.patient_1.id}/")
        self.assertEqual(response.data["utilisateur_prenom"], "Camille")
        self.assertEqual(response.data["utilisateur_nom"], "Martin")

    def test_medecin_voit_seulement_ses_patients_suivis(self):
        self.client.force_authenticate(self.medecin_a)
        response = self.client.get("/api/v1/patients/")
        dossiers = {p["numero_dossier"] for p in response.data["results"]}
        self.assertEqual(dossiers, {"DOS-API-1"})

    def test_medecin_sans_patient_suivi_ne_voit_rien(self):
        self.client.force_authenticate(self.medecin_b)
        response = self.client.get("/api/v1/patients/")
        self.assertEqual(response.data["results"], [])

    def test_patient_voit_seulement_sa_propre_fiche(self):
        self.client.force_authenticate(self.user_patient_1)
        response = self.client.get("/api/v1/patients/")
        dossiers = {p["numero_dossier"] for p in response.data["results"]}
        self.assertEqual(dossiers, {"DOS-API-1"})

    # --- Création : réservée à l'admin ---

    def test_admin_peut_creer_un_patient(self):
        user3 = creer_utilisateur_avec_role("patient3@example.com", ROLE_PATIENT)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/patients/",
            {
                "utilisateur": str(user3.id),
                "numero_dossier": "DOS-API-3",
                "date_naissance": "2000-01-01",
                "sexe": "M",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_medecin_peut_creer_un_patient_et_devient_suiveur_automatiquement(self):
        """
        Décision validée avec le porteur du projet : un médecin peut créer
        directement une fiche patient (en référençant un compte
        Utilisateur déjà existant, créé par un admin) et devient
        automatiquement son médecin suiveur actif.
        """
        user4 = creer_utilisateur_avec_role("patient4@example.com", ROLE_PATIENT)
        self.client.force_authenticate(self.medecin_a)
        response = self.client.post(
            "/api/v1/patients/",
            {
                "utilisateur": str(user4.id),
                "numero_dossier": "DOS-API-4",
                "date_naissance": "2000-01-01",
                "sexe": "M",
            },
        )
        self.assertEqual(response.status_code, 201)
        patient_cree = Patient.objects.get(numero_dossier="DOS-API-4")
        self.assertTrue(
            PatientMedecin.objects.filter(
                patient=patient_cree, medecin=self.medecin_a, actif=True
            ).exists()
        )

    def test_medecin_qui_cree_voit_ensuite_le_patient_dans_son_perimetre(self):
        user5 = creer_utilisateur_avec_role("patient5@example.com", ROLE_PATIENT)
        self.client.force_authenticate(self.medecin_b)
        self.client.post(
            "/api/v1/patients/",
            {
                "utilisateur": str(user5.id),
                "numero_dossier": "DOS-API-5",
                "date_naissance": "2000-01-01",
                "sexe": "F",
            },
        )
        response = self.client.get("/api/v1/patients/")
        dossiers = {p["numero_dossier"] for p in response.data["results"]}
        self.assertIn("DOS-API-5", dossiers)

    def test_patient_ne_peut_toujours_pas_creer_de_patient(self):
        user6 = creer_utilisateur_avec_role("patient6@example.com", ROLE_PATIENT)
        self.client.force_authenticate(self.user_patient_1)
        response = self.client.post(
            "/api/v1/patients/",
            {
                "utilisateur": str(user6.id),
                "numero_dossier": "DOS-API-6",
                "date_naissance": "2000-01-01",
                "sexe": "M",
            },
        )
        self.assertEqual(response.status_code, 403)    # --- Accès objet direct (retrieve) hors périmètre : 404, pas 403 ---
    # (get_queryset filtre déjà l'objet hors du set visible, donc DRF
    # renvoie naturellement 404 plutôt que de révéler son existence.)

    def test_medecin_ne_peut_pas_voir_un_patient_non_suivi(self):
        self.client.force_authenticate(self.medecin_b)
        response = self.client.get(f"/api/v1/patients/{self.patient_1.id}/")
        self.assertEqual(response.status_code, 404)

    def test_patient_ne_peut_pas_voir_la_fiche_d_un_autre_patient(self):
        self.client.force_authenticate(self.user_patient_1)
        response = self.client.get(f"/api/v1/patients/{self.patient_2.id}/")
        self.assertEqual(response.status_code, 404)

    # --- Modification : patient en lecture seule ---

    def test_patient_ne_peut_pas_modifier_sa_propre_fiche(self):
        self.client.force_authenticate(self.user_patient_1)
        response = self.client.patch(
            f"/api/v1/patients/{self.patient_1.id}/", {"numero_dossier": "TRICHE"}
        )
        self.assertEqual(response.status_code, 403)

    def test_medecin_peut_modifier_un_patient_suivi(self):
        self.client.force_authenticate(self.medecin_a)
        response = self.client.patch(
            f"/api/v1/patients/{self.patient_1.id}/",
            {"contact_urgence_nom": "Contact ajouté par le médecin"},
        )
        self.assertEqual(response.status_code, 200)


class NoteMedicaleAPIPermissionsTest(APITestCase):
    def setUp(self):
        self.medecin_a = creer_utilisateur_avec_role("medecinnote.a@example.com", ROLE_MEDECIN)
        self.medecin_b = creer_utilisateur_avec_role("medecinnote.b@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patientnote@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-NOTE-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.AUTRE,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin_a, actif=True)

    def test_medecin_suiveur_peut_ajouter_une_note(self):
        self.client.force_authenticate(self.medecin_a)
        response = self.client.post(
            "/api/v1/notes-medicales/",
            {
                "patient": str(self.patient.id),
                "categorie": NoteMedicale.Categorie.OBSERVATION,
                "contenu": "Tension artérielle normale",
            },
        )
        self.assertEqual(response.status_code, 201)
        note = NoteMedicale.objects.get(id=response.data["id"])
        self.assertEqual(note.saisi_par, self.medecin_a)

    def test_medecin_non_suiveur_ne_peut_pas_ajouter_une_note(self):
        self.client.force_authenticate(self.medecin_b)
        response = self.client.post(
            "/api/v1/notes-medicales/",
            {
                "patient": str(self.patient.id),
                "categorie": NoteMedicale.Categorie.OBSERVATION,
                "contenu": "Ne devrait pas passer",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_patient_ne_peut_pas_ecrire_de_note(self):
        user_patient = self.patient.utilisateur
        self.client.force_authenticate(user_patient)
        response = self.client.post(
            "/api/v1/notes-medicales/",
            {
                "patient": str(self.patient.id),
                "categorie": NoteMedicale.Categorie.OBSERVATION,
                "contenu": "Auto-diagnostic",
            },
        )
        self.assertEqual(response.status_code, 403)


class MedicamentAPITest(APITestCase):
    def setUp(self):
        from apps.medicaments.models import Medicament

        self.medicament = Medicament.objects.create(
            code_cis="60234999", denomination="TEST MEDICAMENT"
        )
        self.patient_user = creer_utilisateur_avec_role("patientmed@example.com", ROLE_PATIENT)

    def test_tout_role_authentifie_peut_lire_le_referentiel(self):
        self.client.force_authenticate(self.patient_user)
        response = self.client.get("/api/v1/medicaments/")
        self.assertEqual(response.status_code, 200)

    def test_ecriture_impossible_meme_pour_un_admin(self):
        """Le référentiel n'est modifiable que par import_bdpm, jamais par l'API."""
        admin = creer_utilisateur_avec_role("adminmed@example.com", ROLE_ADMIN)
        self.client.force_authenticate(admin)
        response = self.client.post(
            "/api/v1/medicaments/", {"code_cis": "99999999", "denomination": "INTRUS"}
        )
        # 405 : la route POST n'existe même pas (ReadOnlyModelViewSet).
        self.assertEqual(response.status_code, 405)
