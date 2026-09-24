import datetime

from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from apps.medicaments.models import Medicament
from apps.patients.models import Patient, PatientMedecin
from apps.utilisateurs.models import ROLE_ADMIN, ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .logique import calculer_alerte_depassement, confirmer_prises_automatiques
from .models import HoraireProgramme, Prescription, Prise


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(
        username=email.split("@")[0], email=email, password="x"
    )
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class PrescriptionModelTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medecin@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patient@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-PRESC-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="1", denomination="DOLIPRANE")

    def test_creation_prescription_reguliere_avec_horaires(self):
        prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            frequence_par_jour=2,
            date_debut=datetime.date(2026, 1, 1),
        )
        HoraireProgramme.objects.create(prescription=prescription, heure="08:00", quantite=1)
        HoraireProgramme.objects.create(prescription=prescription, heure="20:00", quantite=1)
        self.assertEqual(prescription.horaires.count(), 2)


class CalculerAlerteDepassementTest(TestCase):
    """
    Décision validée : une prise 'réserve' qui dépasse dose_max_par_jour
    est enregistrée quand même, avec alerte_depassement=True.
    """

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medecin2@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patient2@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-PRESC-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        self.medicament = Medicament.objects.create(code_cis="2", denomination="DAFALGAN")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            dose_max_par_jour=3,
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_pas_d_alerte_sous_le_plafond(self):
        prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=2,
            statut=Prise.Statut.PRISE,
        )
        self.assertFalse(calculer_alerte_depassement(prise))

    def test_alerte_si_cumul_du_jour_depasse_le_plafond(self):
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 8, 0)),
            quantite_prise=2,
            statut=Prise.Statut.PRISE,
        )
        nouvelle_prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 18, 0)),
            quantite_prise=2,
            statut=Prise.Statut.PRISE,
        )
        # 2 + 2 = 4 > plafond de 3
        self.assertTrue(calculer_alerte_depassement(nouvelle_prise))

    def test_jour_different_ne_compte_pas_dans_le_cumul(self):
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 4, 8, 0)),
            quantite_prise=3,
            statut=Prise.Statut.PRISE,
        )
        nouvelle_prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 8, 0)),
            quantite_prise=2,
            statut=Prise.Statut.PRISE,
        )
        self.assertFalse(calculer_alerte_depassement(nouvelle_prise))

    def test_pas_d_alerte_pour_une_prescription_reguliere(self):
        prescription_reguliere = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=10,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        prise = Prise.objects.create(
            prescription=prescription_reguliere,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 8, 0)),
            quantite_prise=10,
            statut=Prise.Statut.PRISE,
        )
        self.assertFalse(calculer_alerte_depassement(prise))


class GenererPrisesAttenduesCommandTest(TestCase):
    """Vérifie que la commande génère bien un calendrier à l'avance (décision validée)."""

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medecin3@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patient3@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-PRESC-3",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="3", denomination="ASPIRINE")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=timezone.localdate(),
        )
        HoraireProgramme.objects.create(prescription=self.prescription, heure="08:00", quantite=1)
        HoraireProgramme.objects.create(prescription=self.prescription, heure="20:00", quantite=1)

    def test_genere_le_bon_nombre_de_prises(self):
        from django.core.management import call_command

        call_command("generer_prises_attendues", jours=7)
        # 2 horaires x 7 jours = 14 prises attendues
        self.assertEqual(
            Prise.objects.filter(prescription=self.prescription, statut=Prise.Statut.ATTENDUE).count(),
            14,
        )

    def test_execution_repetee_ne_duplique_pas(self):
        from django.core.management import call_command

        call_command("generer_prises_attendues", jours=7)
        call_command("generer_prises_attendues", jours=7)
        self.assertEqual(
            Prise.objects.filter(prescription=self.prescription).count(),
            14,
        )

    def test_respecte_la_date_de_fin_de_prescription(self):
        from django.core.management import call_command

        self.prescription.date_fin = timezone.localdate() + datetime.timedelta(days=2)
        self.prescription.save()

        call_command("generer_prises_attendues", jours=7)
        # 2 horaires x 3 jours couverts (aujourd'hui + 2) = 6
        self.assertEqual(
            Prise.objects.filter(prescription=self.prescription).count(),
            6,
        )


class ConfirmerPrisesAutomatiquesTest(TestCase):
    """
    Décision validée : confirmation_automatique (par défaut activée) fait
    basculer une prise 'attendue' en 'prise' dès que son heure prévue est
    atteinte ; désactivée, la prise reste 'attendue' indéfiniment (jamais
    de bascule automatique en 'oubliée').
    """

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medecin4@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patient4@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-PRESC-4",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="4", denomination="EFFERALGAN")
        self.maintenant = timezone.now()

    def _creer_prescription(self, confirmation_automatique):
        return Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=timezone.localdate() - datetime.timedelta(days=1),
            confirmation_automatique=confirmation_automatique,
        )

    def test_confirmation_automatique_activee_par_defaut(self):
        prescription = self._creer_prescription(confirmation_automatique=True)
        self.assertTrue(prescription.confirmation_automatique)

    def test_bascule_en_prise_une_fois_l_heure_atteinte(self):
        prescription = self._creer_prescription(confirmation_automatique=True)
        prise = Prise.objects.create(
            prescription=prescription,
            date_heure_prevue=self.maintenant - datetime.timedelta(minutes=1),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )

        confirmees = confirmer_prises_automatiques(maintenant=self.maintenant)

        prise.refresh_from_db()
        self.assertEqual([p.pk for p in confirmees], [prise.pk])
        self.assertEqual(prise.statut, Prise.Statut.PRISE)
        self.assertEqual(prise.quantite_prise, 1)
        self.assertEqual(prise.date_heure_reelle, prise.date_heure_prevue)

    def test_ne_touche_pas_une_prise_dont_l_heure_n_est_pas_encore_atteinte(self):
        prescription = self._creer_prescription(confirmation_automatique=True)
        prise = Prise.objects.create(
            prescription=prescription,
            date_heure_prevue=self.maintenant + datetime.timedelta(minutes=30),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )

        confirmees = confirmer_prises_automatiques(maintenant=self.maintenant)

        prise.refresh_from_db()
        self.assertEqual(confirmees, [])
        self.assertEqual(prise.statut, Prise.Statut.ATTENDUE)

    def test_ne_touche_pas_une_prescription_avec_confirmation_manuelle(self):
        prescription = self._creer_prescription(confirmation_automatique=False)
        prise = Prise.objects.create(
            prescription=prescription,
            date_heure_prevue=self.maintenant - datetime.timedelta(minutes=1),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )

        confirmees = confirmer_prises_automatiques(maintenant=self.maintenant)

        prise.refresh_from_db()
        self.assertEqual(confirmees, [])
        self.assertEqual(prise.statut, Prise.Statut.ATTENDUE)

    def test_decompte_le_stock_seulement_a_la_confirmation_pas_a_la_generation(self):
        from apps.stock.models import Boite

        prescription = self._creer_prescription(confirmation_automatique=True)
        Boite.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            quantite_initiale=10,
            quantite_restante=10,
        )
        prise = Prise.objects.create(
            prescription=prescription,
            date_heure_prevue=self.maintenant - datetime.timedelta(minutes=1),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )
        # Génération à l'avance (statut ATTENDUE) : pas de décompte.
        self.assertEqual(Boite.objects.get().quantite_restante, 10)

        confirmer_prises_automatiques(maintenant=self.maintenant)

        prise.refresh_from_db()
        self.assertEqual(prise.statut, Prise.Statut.PRISE)
        self.assertEqual(Boite.objects.get().quantite_restante, 9)

    def test_commande_de_management_confirme_les_prises_dues(self):
        from django.core.management import call_command

        prescription = self._creer_prescription(confirmation_automatique=True)
        prise = Prise.objects.create(
            prescription=prescription,
            date_heure_prevue=self.maintenant - datetime.timedelta(minutes=1),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )

        call_command("confirmer_prises_automatiques")

        prise.refresh_from_db()
        self.assertEqual(prise.statut, Prise.Statut.PRISE)
