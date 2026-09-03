import datetime

from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.medicaments.models import Medicament
from apps.patients.models import Patient
from apps.prescriptions.models import Prescription, Prise
from apps.stock.models import Boite
from apps.utilisateurs.models import ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from apps.patients.models import PatientMedecin

from .canaux import envoyer_notification
from .logique import generer_alertes_rupture_stock, generer_alertes_stock, generer_rappels_prises_a_venir
from .models import Notification


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(username=email.split("@")[0], email=email, password="x")
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class RappelsPrisesTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("mednotif1@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patnotif1@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-NOTIF-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="NOTIF1", denomination="NOTIFOL")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_rappel_genere_pour_une_prise_proche(self):
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_prevue=timezone.now() + datetime.timedelta(minutes=10),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )
        notifications = generer_rappels_prises_a_venir(fenetre_minutes=15)
        # 2 notifications : in_app + email
        self.assertEqual(len(notifications), 2)
        self.assertEqual(
            {n.canal for n in notifications}, {Notification.Canal.IN_APP, Notification.Canal.EMAIL}
        )

    def test_pas_de_rappel_hors_fenetre(self):
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_prevue=timezone.now() + datetime.timedelta(hours=5),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )
        notifications = generer_rappels_prises_a_venir(fenetre_minutes=15)
        self.assertEqual(len(notifications), 0)

    def test_pas_de_doublon_si_deja_notifie(self):
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_prevue=timezone.now() + datetime.timedelta(minutes=10),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )
        generer_rappels_prises_a_venir(fenetre_minutes=15)
        deuxieme_appel = generer_rappels_prises_a_venir(fenetre_minutes=15)
        self.assertEqual(len(deuxieme_appel), 0)

    def test_pas_de_rappel_pour_une_prise_deja_prise(self):
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_prevue=timezone.now() + datetime.timedelta(minutes=10),
            date_heure_reelle=timezone.now(),
            quantite_prise=1,
            statut=Prise.Statut.PRISE,
        )
        notifications = generer_rappels_prises_a_venir(fenetre_minutes=15)
        self.assertEqual(len(notifications), 0)


class AlertesStockNotificationTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("mednotif2@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patnotif2@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-NOTIF-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        self.medicament = Medicament.objects.create(code_cis="NOTIF2", denomination="NOTIFOL2")

    def test_alerte_generee_pour_boite_en_alerte(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=2, seuil_alerte_quantite=5,
        )
        notifications = generer_alertes_stock()
        self.assertEqual(len(notifications), 2)  # in_app + email

    def test_pas_d_alerte_pour_boite_hors_seuil(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=8, seuil_alerte_quantite=5,
        )
        notifications = generer_alertes_stock()
        self.assertEqual(len(notifications), 0)

    def test_pas_de_relance_avant_le_delai(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=2, seuil_alerte_quantite=5,
        )
        generer_alertes_stock(delai_relance_heures=24)
        deuxieme_appel = generer_alertes_stock(delai_relance_heures=24)
        self.assertEqual(len(deuxieme_appel), 0)

    def test_preference_medecin_envoie_uniquement_au_medecin_suiveur(self):
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin, actif=True)
        self.patient.preference_alerte_stock = "medecin"
        self.patient.save(update_fields=["preference_alerte_stock"])
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=2, seuil_alerte_quantite=5,
        )
        notifications = generer_alertes_stock()
        self.assertEqual(len(notifications), 2)  # in_app + email
        self.assertTrue(all(n.destinataire == self.medecin for n in notifications))

    def test_preference_les_deux_envoie_au_patient_et_au_medecin(self):
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin, actif=True)
        self.patient.preference_alerte_stock = "les_deux"
        self.patient.save(update_fields=["preference_alerte_stock"])
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=2, seuil_alerte_quantite=5,
        )
        notifications = generer_alertes_stock()
        self.assertEqual(len(notifications), 4)  # (in_app + email) x 2 destinataires
        destinataires = {n.destinataire for n in notifications}
        self.assertEqual(destinataires, {self.user_patient, self.medecin})


class AlertesRuptureStockNotificationTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("mednotif4@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patnotif4@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-NOTIF-4",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        self.medicament = Medicament.objects.create(code_cis="NOTIF4", denomination="NOTIFOL4")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_alerte_generee_quand_aucune_boite_pour_une_prescription_active(self):
        notifications = generer_alertes_rupture_stock()
        self.assertEqual(len(notifications), 2)  # in_app + email
        self.assertEqual(notifications[0].prescription, self.prescription)
        self.assertIsNone(notifications[0].boite)

    def test_pas_dalerte_si_une_boite_active_existe(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
        )
        notifications = generer_alertes_rupture_stock()
        self.assertEqual(len(notifications), 0)

    def test_pas_dalerte_pour_une_prescription_arretee(self):
        self.prescription.statut = Prescription.Statut.ARRETEE
        self.prescription.save(update_fields=["statut"])
        notifications = generer_alertes_rupture_stock()
        self.assertEqual(len(notifications), 0)

    def test_pas_de_relance_avant_le_delai(self):
        generer_alertes_rupture_stock(delai_relance_heures=24)
        deuxieme_appel = generer_alertes_rupture_stock(delai_relance_heures=24)
        self.assertEqual(len(deuxieme_appel), 0)


class EnvoyerNotificationTest(TestCase):
    def setUp(self):
        self.user_patient = creer_utilisateur_avec_role("patnotif3@example.com", ROLE_PATIENT)

    def test_email_envoye_via_backend_console_marque_envoyee(self):
        notification = Notification.objects.create(
            destinataire=self.user_patient,
            canal=Notification.Canal.EMAIL,
            categorie=Notification.Categorie.AUTRE,
            titre="Test",
            message="Contenu de test",
        )
        envoyer_notification(notification)
        notification.refresh_from_db()
        self.assertEqual(notification.statut, Notification.Statut.ENVOYEE)
        self.assertIsNotNone(notification.date_envoi)
        # Backend console : l'email est capturé par le test runner Django.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_patient.email])

    def test_in_app_marquee_envoyee_immediatement(self):
        notification = Notification.objects.create(
            destinataire=self.user_patient,
            canal=Notification.Canal.IN_APP,
            categorie=Notification.Categorie.AUTRE,
            titre="Test",
            message="Contenu de test",
        )
        envoyer_notification(notification)
        notification.refresh_from_db()
        self.assertEqual(notification.statut, Notification.Statut.ENVOYEE)

    def test_sms_echoue_explicitement_sans_fournisseur_configure(self):
        """
        Décision assumée : sans fournisseur SMS configuré, la notification
        est marquée en échec avec un message clair, jamais silencieusement
        ignorée ni faussement marquée "envoyée".
        """
        notification = Notification.objects.create(
            destinataire=self.user_patient,
            canal=Notification.Canal.SMS,
            categorie=Notification.Categorie.AUTRE,
            titre="Test",
            message="Contenu de test",
        )
        envoyer_notification(notification)
        notification.refresh_from_db()
        self.assertEqual(notification.statut, Notification.Statut.ECHEC)
        self.assertIn("Aucun fournisseur SMS configuré", notification.erreur)

    @override_settings(SMS_BACKEND_ACTIVE=True)
    def test_sms_active_sans_integration_leve_une_erreur_explicite(self):
        """Si SMS_BACKEND_ACTIVE=True sans intégration réelle codée, on veut une erreur claire, pas un faux succès."""
        notification = Notification.objects.create(
            destinataire=self.user_patient,
            canal=Notification.Canal.SMS,
            categorie=Notification.Categorie.AUTRE,
            titre="Test",
            message="Contenu de test",
        )
        with self.assertRaises(NotImplementedError):
            envoyer_notification(notification)
