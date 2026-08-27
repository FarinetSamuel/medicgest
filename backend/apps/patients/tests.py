import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.patients.models import NoteMedicale, Patient, PatientMedecin
from apps.utilisateurs.models import Utilisateur


def creer_utilisateur(email, **kwargs):
    return Utilisateur.objects.create_user(
        username=email.split("@")[0], email=email, password="x", **kwargs
    )


class PatientModelTest(TestCase):
    def test_patient_necessite_un_compte_utilisateur(self):
        """
        Décision validée avec le porteur du projet : tout patient a un
        compte (relation OneToOne obligatoire, pas nullable).
        """
        champ = Patient._meta.get_field("utilisateur")
        self.assertFalse(champ.null)

    def test_creation_patient_complete(self):
        user = creer_utilisateur("patient1@example.com", first_name="Marie")
        patient = Patient.objects.create(
            utilisateur=user,
            numero_dossier="DOS-0001",
            date_naissance=datetime.date(1980, 5, 12),
            sexe=Patient.Sexe.FEMININ,
        )
        self.assertEqual(patient.numero_dossier, "DOS-0001")
        # Contact d'urgence facultatif : doit pouvoir rester vide.
        self.assertEqual(patient.contact_urgence_nom, "")

    def test_contact_urgence_est_facultatif(self):
        """Le contact d'urgence doit pouvoir être rempli sans erreur (facultatif, pas absent)."""
        user = creer_utilisateur("patient2@example.com")
        patient = Patient.objects.create(
            utilisateur=user,
            numero_dossier="DOS-0002",
            date_naissance=datetime.date(1990, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
            contact_urgence_nom="Paul Martin",
            contact_urgence_telephone="0600000000",
            contact_urgence_lien="Conjoint",
        )
        self.assertEqual(patient.contact_urgence_nom, "Paul Martin")

    def test_numero_dossier_unique(self):
        user1 = creer_utilisateur("p3@example.com")
        user2 = creer_utilisateur("p4@example.com")
        Patient.objects.create(
            utilisateur=user1,
            numero_dossier="DOS-DUP",
            date_naissance=datetime.date(1970, 1, 1),
            sexe=Patient.Sexe.AUTRE,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Patient.objects.create(
                    utilisateur=user2,
                    numero_dossier="DOS-DUP",
                    date_naissance=datetime.date(1970, 1, 1),
                    sexe=Patient.Sexe.AUTRE,
                )


class NoteMedicaleModelTest(TestCase):
    def setUp(self):
        self.user = creer_utilisateur("patient5@example.com")
        self.patient = Patient.objects.create(
            utilisateur=self.user,
            numero_dossier="DOS-0005",
            date_naissance=datetime.date(1985, 3, 3),
            sexe=Patient.Sexe.FEMININ,
        )

    def test_note_structuree_par_categorie(self):
        """
        Décision validée : les notes médicales sont structurées par
        catégorie (allergie / antécédent / observation), pas en texte libre.
        """
        note = NoteMedicale.objects.create(
            patient=self.patient,
            categorie=NoteMedicale.Categorie.ALLERGIE,
            contenu="Allergie à la pénicilline",
        )
        self.assertEqual(note.categorie, "allergie")

    def test_filtrage_par_categorie(self):
        NoteMedicale.objects.create(
            patient=self.patient,
            categorie=NoteMedicale.Categorie.ALLERGIE,
            contenu="Allergie aux arachides",
        )
        NoteMedicale.objects.create(
            patient=self.patient,
            categorie=NoteMedicale.Categorie.ANTECEDENT,
            contenu="Appendicectomie en 2010",
        )
        allergies = self.patient.notes_medicales.filter(
            categorie=NoteMedicale.Categorie.ALLERGIE
        )
        self.assertEqual(allergies.count(), 1)


class PatientMedecinModelTest(TestCase):
    def setUp(self):
        self.patient_user = creer_utilisateur("patient6@example.com")
        self.patient = Patient.objects.create(
            utilisateur=self.patient_user,
            numero_dossier="DOS-0006",
            date_naissance=datetime.date(1995, 6, 6),
            sexe=Patient.Sexe.MASCULIN,
        )
        self.medecin = creer_utilisateur("medecin@example.com")

    def test_un_seul_suivi_actif_par_couple(self):
        """
        Contrainte métier : un médecin ne peut avoir qu'un seul suivi actif
        pour un même patient (empêche les doublons de relation active).
        """
        PatientMedecin.objects.create(
            patient=self.patient, medecin=self.medecin, actif=True
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatientMedecin.objects.create(
                    patient=self.patient, medecin=self.medecin, actif=True
                )

    def test_reactivation_apres_suivi_termine_autorisee(self):
        """
        Un nouveau suivi actif doit redevenir possible une fois l'ancien
        marqué comme terminé (actif=False) — la contrainte ne porte que
        sur les suivis actifs.
        """
        suivi = PatientMedecin.objects.create(
            patient=self.patient, medecin=self.medecin, actif=True
        )
        suivi.actif = False
        suivi.save()

        nouveau_suivi = PatientMedecin.objects.create(
            patient=self.patient, medecin=self.medecin, actif=True
        )
        self.assertTrue(nouveau_suivi.actif)
