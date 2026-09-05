import datetime

from django.contrib.auth.models import Group, Permission
from rest_framework.test import APITestCase
from django.utils import timezone

from apps.medicaments.models import Medicament
from apps.patients.models import Patient, PatientMedecin
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .models import HoraireProgramme, Prescription, Prise


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(
        username=email.split("@")[0], email=email, password="x"
    )
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class PrescriptionAPITest(APITestCase):
    def setUp(self):
        self.admin = creer_utilisateur_avec_role("adminapi@example.com", ROLE_ADMIN)
        self.medecin_suiveur = creer_utilisateur_avec_role("medapi1@example.com", ROLE_MEDECIN)
        self.medecin_autre = creer_utilisateur_avec_role("medapi2@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patapi1@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-API-PRESC-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin_suiveur, actif=True)
        self.medicament = Medicament.objects.create(code_cis="API1", denomination="TESTOL")

    def test_medecin_suiveur_peut_prescrire(self):
        self.client.force_authenticate(self.medecin_suiveur)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "type_prise": Prescription.TypePrise.REGULIERE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["medecin_prescripteur"]), str(self.medecin_suiveur.id))

    def test_medecin_non_suiveur_ne_peut_pas_prescrire(self):
        self.client.force_authenticate(self.medecin_autre)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "type_prise": Prescription.TypePrise.REGULIERE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_peut_prescrire_en_precisant_le_medecin(self):
        """
        Reproduit le bug réel observé en production : avant correction,
        medecin_prescripteur était en read_only côté serializer, donc
        silencieusement ignoré même envoyé par le client — IntegrityError
        500 (colonne NOT NULL) au lieu d'un enregistrement correct.
        """
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "medecin_prescripteur": str(self.medecin_suiveur.id),
                "type_prise": Prescription.TypePrise.RESERVE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["medecin_prescripteur"]), str(self.medecin_suiveur.id))

    def test_admin_sans_medecin_prescripteur_recoit_une_erreur_propre(self):
        """
        Le cas qui provoquait le crash 500 : doit maintenant renvoyer un
        400 exploitable par le frontend, jamais une IntegrityError brute.
        """
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "type_prise": Prescription.TypePrise.RESERVE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("medecin_prescripteur", response.data)

    def test_medecin_ne_peut_pas_usurper_un_autre_prescripteur(self):
        """
        medecin_prescripteur n'est plus read_only (nécessaire pour
        l'admin) : vérifie qu'un médecin qui tente de passer l'id d'un
        autre médecin dans le payload est quand même enregistré comme
        LUI-MÊME le prescripteur (la vue écrase toujours la valeur).
        """
        self.client.force_authenticate(self.medecin_suiveur)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "medecin_prescripteur": str(self.medecin_autre.id),
                "type_prise": Prescription.TypePrise.REGULIERE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["medecin_prescripteur"]), str(self.medecin_suiveur.id))

    def test_patient_sans_permission_django_ne_peut_pas_prescrire(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "type_prise": Prescription.TypePrise.REGULIERE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_patient_avec_permission_django_peut_prescrire_en_designant_son_medecin_suiveur(self):
        """
        Même principe que HoraireProgrammeViewSet : un patient n'a par
        défaut qu'un accès en lecture, sauf s'il détient explicitement la
        permission Django add_prescription (accordée via un Group dans
        l'admin) — dans ce cas il peut créer une prescription pour
        lui-même, à condition de désigner l'un de ses médecins suiveurs
        actifs (medecin_prescripteur n'est pas nullable en base).
        """
        self.user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="add_prescription")
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "medecin_prescripteur": str(self.medecin_suiveur.id),
                "type_prise": Prescription.TypePrise.RESERVE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["medecin_prescripteur"]), str(self.medecin_suiveur.id))

    def test_patient_avec_permission_django_sans_medecin_prescripteur_recoit_une_erreur_propre(self):
        """
        Le cas qui provoquait le crash 500 observé en production :
        medecin_prescripteur n'est pas nullable en base, donc l'absence de
        ce champ doit renvoyer un 400 exploitable, jamais une
        IntegrityError brute.
        """
        self.user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="add_prescription")
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "type_prise": Prescription.TypePrise.RESERVE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("medecin_prescripteur", response.data)

    def test_patient_avec_permission_django_ne_peut_pas_prescrire_pour_un_autre_patient(self):
        autre_user_patient = creer_utilisateur_avec_role("patapi2@example.com", ROLE_PATIENT)
        Patient.objects.create(
            utilisateur=autre_user_patient,
            numero_dossier="DOS-API-PRESC-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        # autre_user_patient détient lui aussi la permission, pour isoler
        # le contrôle de propriété (perform_create) de la permission
        # Django (has_permission) : même autorisé, il ne peut prescrire
        # que pour lui-même, pas pour self.patient.
        autre_user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="add_prescription")
        )
        self.client.force_authenticate(autre_user_patient)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "medecin_prescripteur": str(self.medecin_suiveur.id),
                "type_prise": Prescription.TypePrise.RESERVE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_patient_avec_permission_django_ne_peut_pas_designer_un_medecin_qui_ne_le_suit_pas(self):
        self.user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="add_prescription")
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/prescriptions/",
            {
                "patient": str(self.patient.id),
                "medicament": str(self.medicament.id),
                "medecin_prescripteur": str(self.medecin_autre.id),
                "type_prise": Prescription.TypePrise.RESERVE,
                "dose_quantite": "1.00",
                "dose_unite": "comprimé",
                "date_debut": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("medecin_prescripteur", response.data)

    def test_patient_voit_ses_prescriptions_en_lecture_seule(self):
        prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin_suiveur,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.get("/api/v1/prescriptions/")
        self.assertEqual(len(response.data["results"]), 1)

        response_patch = self.client.patch(
            f"/api/v1/prescriptions/{prescription.id}/", {"dose_quantite": "5.00"}
        )
        self.assertEqual(response_patch.status_code, 403)


class PriseAPITest(APITestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medapi3@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patapi2@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-API-PRISE-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin, actif=True)
        self.medicament = Medicament.objects.create(code_cis="API2", denomination="TESTOL2")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            dose_max_par_jour=2,
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_patient_peut_enregistrer_une_prise_reserve(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/prises/",
            {
                "prescription": str(self.prescription.id),
                "date_heure_reelle": "2026-01-05T10:00:00Z",
                "quantite_prise": "1.00",
                "statut": "prise",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["alerte_depassement"])

    def test_alerte_declenchee_visible_via_l_api(self):
        self.client.force_authenticate(self.user_patient)
        self.client.post(
            "/api/v1/prises/",
            {
                "prescription": str(self.prescription.id),
                "date_heure_reelle": "2026-01-05T08:00:00Z",
                "quantite_prise": "2.00",
                "statut": "prise",
            },
        )
        response = self.client.post(
            "/api/v1/prises/",
            {
                "prescription": str(self.prescription.id),
                "date_heure_reelle": "2026-01-05T20:00:00Z",
                "quantite_prise": "1.00",
                "statut": "prise",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["alerte_depassement"])

    def test_patient_peut_modifier_sans_restriction_une_prise_deja_enregistree(self):
        """Décision validée : aucune restriction sur la modification par le patient lui-même."""
        prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=1,
            statut=Prise.Statut.PRISE,
            enregistre_par=self.user_patient,
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.patch(
            f"/api/v1/prises/{prise.id}/", {"quantite_prise": "0.50", "commentaire": "Correction"}
        )
        self.assertEqual(response.status_code, 200)

        response_delete = self.client.delete(f"/api/v1/prises/{prise.id}/")
        self.assertEqual(response_delete.status_code, 204)

    def test_autre_patient_ne_peut_pas_enregistrer_une_prise_sur_une_prescription_qui_nest_pas_la_sienne(self):
        autre_patient_user = creer_utilisateur_avec_role("patapi3@example.com", ROLE_PATIENT)
        Patient.objects.create(
            utilisateur=autre_patient_user,
            numero_dossier="DOS-API-PRISE-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.client.force_authenticate(autre_patient_user)
        response = self.client.post(
            "/api/v1/prises/",
            {
                "prescription": str(self.prescription.id),
                "date_heure_reelle": "2026-01-05T10:00:00Z",
                "quantite_prise": "1.00",
                "statut": "prise",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Prise.objects.count(), 0)

    def test_medecin_non_suiveur_ne_peut_pas_enregistrer_une_prise(self):
        autre_medecin = creer_utilisateur_avec_role("medapi5@example.com", ROLE_MEDECIN)
        self.client.force_authenticate(autre_medecin)
        response = self.client.post(
            "/api/v1/prises/",
            {
                "prescription": str(self.prescription.id),
                "date_heure_reelle": "2026-01-05T10:00:00Z",
                "quantite_prise": "1.00",
                "statut": "prise",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Prise.objects.count(), 0)

    def test_medecin_non_suiveur_ne_voit_pas_les_prises(self):
        autre_medecin = creer_utilisateur_avec_role("medapi4@example.com", ROLE_MEDECIN)
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=1,
            statut=Prise.Statut.PRISE,
        )
        self.client.force_authenticate(autre_medecin)
        response = self.client.get("/api/v1/prises/")
        self.assertEqual(response.data["results"], [])


class HoraireProgrammeAPITest(APITestCase):
    """
    Par défaut un patient n'a qu'un accès en lecture aux horaires
    programmés (décision clinique du médecin). Il peut y accéder en
    écriture uniquement si le compte détient explicitement les
    permissions Django add/change/delete_horaireprogramme — accordées via
    un Group dans l'admin — et seulement sur ses propres prescriptions.
    """

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medapi5@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patapi3@example.com", ROLE_PATIENT)
        self.autre_user_patient = creer_utilisateur_avec_role("patapi4@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-API-HORAIRE-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        self.autre_patient = Patient.objects.create(
            utilisateur=self.autre_user_patient,
            numero_dossier="DOS-API-HORAIRE-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin, actif=True)
        self.medicament = Medicament.objects.create(code_cis="API5", denomination="TESTOL5")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_patient_sans_permission_django_ne_peut_pas_ajouter_un_horaire(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/horaires-programmes/",
            {"prescription": str(self.prescription.id), "heure": "08:00", "quantite": "1"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(HoraireProgramme.objects.count(), 0)

    def test_patient_avec_permission_django_peut_ajouter_un_horaire_sur_sa_prescription(self):
        self.user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="add_horaireprogramme")
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/horaires-programmes/",
            {"prescription": str(self.prescription.id), "heure": "08:00", "quantite": "1"},
        )
        self.assertEqual(response.status_code, 201)

    def test_patient_avec_permission_django_ne_peut_pas_ajouter_un_horaire_pour_un_autre_patient(self):
        self.user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="add_horaireprogramme")
        )
        autre_prescription = Prescription.objects.create(
            patient=self.autre_patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.post(
            "/api/v1/horaires-programmes/",
            {"prescription": str(autre_prescription.id), "heure": "08:00", "quantite": "1"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(HoraireProgramme.objects.count(), 0)

    def test_patient_avec_permission_django_peut_modifier_son_propre_horaire(self):
        self.user_patient.user_permissions.add(
            Permission.objects.get(content_type__app_label="prescriptions", codename="change_horaireprogramme")
        )
        horaire = HoraireProgramme.objects.create(prescription=self.prescription, heure="08:00", quantite=1)
        self.client.force_authenticate(self.user_patient)
        response = self.client.patch(f"/api/v1/horaires-programmes/{horaire.id}/", {"actif": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["actif"])
