import datetime
import io

from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from apps.medicaments.models import Medicament
from apps.patients.models import Patient, PatientMedecin
from apps.prescriptions.models import HoraireProgramme, Prescription, Prise
from apps.stock.models import Boite
from apps.utilisateurs.models import ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .donnees import (
    CONTENU_A_VENIR,
    CONTENUS,
    rassembler_besoins_a_venir,
    rassembler_donnees_patient,
)
from .excel import generer_excel_patient
from .pdf import generer_pdf_patient


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(username=email.split("@")[0], email=email, password="x")
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class DonneesExportTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medexp1@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patexp1@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-EXP-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="EXP1", denomination="EXPOL")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
            statut=Prescription.Statut.ACTIVE,
        )

    def test_rassemble_les_prescriptions_actives(self):
        donnees = rassembler_donnees_patient(self.patient)
        self.assertEqual(len(donnees["prescriptions_actives"]), 1)

    def test_prescription_arretee_absente(self):
        self.prescription.statut = Prescription.Statut.ARRETEE
        self.prescription.save()
        donnees = rassembler_donnees_patient(self.patient)
        self.assertEqual(len(donnees["prescriptions_actives"]), 0)

    def _creer_prise(self, jour, quantite=1):
        return Prise.objects.create(
            prescription=self.prescription,
            statut=Prise.Statut.PRISE,
            date_heure_reelle=timezone.make_aware(
                datetime.datetime.combine(jour, datetime.time(12, 0))
            ),
            quantite_prise=quantite,
        )

    def test_periode_choisie_borne_l_historique_des_prises(self):
        """Bornes incluses ; la période remplace la fenêtre par défaut de 30 jours."""
        self._creer_prise(datetime.date(2026, 3, 1))
        debut = self._creer_prise(datetime.date(2026, 3, 2))
        fin = self._creer_prise(datetime.date(2026, 3, 5), quantite=2)
        self._creer_prise(datetime.date(2026, 3, 6))

        donnees = rassembler_donnees_patient(
            self.patient, date_debut=datetime.date(2026, 3, 2), date_fin=datetime.date(2026, 3, 5)
        )

        self.assertEqual({p.pk for p in donnees["historique_prises"]}, {debut.pk, fin.pk})
        self.assertEqual(len(donnees["resume_prises"]), 1)
        self.assertEqual(donnees["resume_prises"][0]["medicament"], "EXPOL")
        self.assertEqual(donnees["resume_prises"][0]["nombre"], 2)
        self.assertEqual(donnees["resume_prises"][0]["quantite"], 3)

    def test_prescriptions_regroupees_par_medecin(self):
        autre_medecin = creer_utilisateur_avec_role("medexp1b@example.com", ROLE_MEDECIN)
        autre_medicament = Medicament.objects.create(code_cis="EXP1B", denomination="EXPOLB")
        autre = Prescription.objects.create(
            patient=self.patient,
            medicament=autre_medicament,
            medecin_prescripteur=autre_medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )

        groupes = rassembler_donnees_patient(self.patient)["prescriptions_par_medecin"]
        self.assertEqual(
            sorted([p.pk for p in g["prescriptions"]] for g in groupes),
            sorted([[self.prescription.pk], [autre.pk]]),
        )

        groupes = rassembler_donnees_patient(self.patient, medecin_id=autre_medecin.id)[
            "prescriptions_par_medecin"
        ]
        self.assertEqual(len(groupes), 1)
        self.assertEqual(groupes[0]["medecin"], "medexp1b@example.com")
        self.assertEqual(groupes[0]["prescriptions"], [autre])

    def test_prescriptions_par_medecin_n_inclut_les_inactives_que_sur_demande(self):
        self.prescription.statut = Prescription.Statut.ARRETEE
        self.prescription.save()

        self.assertEqual(rassembler_donnees_patient(self.patient)["prescriptions_par_medecin"], [])
        groupes = rassembler_donnees_patient(self.patient, inclure_inactives=True)[
            "prescriptions_par_medecin"
        ]
        self.assertEqual(groupes[0]["prescriptions"], [self.prescription])


class GenerationPdfTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medexp2@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patexp2@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-EXP-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )

    def test_genere_un_vrai_pdf_valide(self):
        """Vérifie la signature binaire réelle d'un PDF (%PDF-), pas juste l'absence d'exception."""
        contenu = generer_pdf_patient(self.patient)
        self.assertTrue(contenu.startswith(b"%PDF-"))
        self.assertGreater(len(contenu), 500)

    def test_pdf_genere_meme_sans_aucune_donnee(self):
        """Un patient sans prescription/prise/stock ne doit pas faire planter la génération."""
        contenu = generer_pdf_patient(self.patient)
        self.assertTrue(contenu.startswith(b"%PDF-"))

    def test_pdf_genere_pour_chaque_contenu(self):
        medicament = Medicament.objects.create(code_cis="EXP2", denomination="EXPOL2")
        prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        HoraireProgramme.objects.create(
            prescription=prescription, heure="08:00", quantite=1, intervalle_jours=2
        )
        Prise.objects.create(
            prescription=prescription,
            statut=Prise.Statut.PRISE,
            date_heure_reelle=timezone.now(),
            quantite_prise=1,
        )
        Boite.objects.create(
            patient=self.patient,
            medicament=medicament,
            quantite_initiale=10,
            quantite_restante=2,
            date_peremption=timezone.localdate(),
        )
        aujourdhui = timezone.localdate()
        for contenu in CONTENUS:
            with self.subTest(contenu=contenu):
                filtres = {}
                if contenu == CONTENU_A_VENIR:
                    filtres = {
                        "date_debut": aujourdhui,
                        "date_fin": aujourdhui + datetime.timedelta(days=10),
                    }
                pdf = generer_pdf_patient(self.patient, contenu=contenu, **filtres)
                self.assertTrue(pdf.startswith(b"%PDF-"))


class BesoinsAVenirTest(TestCase):
    """Liste de vacances : prises prévues sur une période à venir et stock correspondant."""

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medexp4@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patexp4@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-EXP-4",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="EXP4", denomination="EXPOL4")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        # 2 comprimés par jour.
        HoraireProgramme.objects.create(prescription=self.prescription, heure="08:00", quantite=1)
        HoraireProgramme.objects.create(prescription=self.prescription, heure="20:00", quantite=1)
        self.aujourdhui = timezone.localdate()
        # Minuit passé d'une minute : toutes les prises du jour sont encore à venir.
        self.maintenant = timezone.make_aware(
            datetime.datetime.combine(self.aujourdhui, datetime.time(0, 1))
        )

    def _besoins(self, debut_dans, fin_dans):
        return rassembler_besoins_a_venir(
            self.patient,
            self.aujourdhui + datetime.timedelta(days=debut_dans),
            self.aujourdhui + datetime.timedelta(days=fin_dans),
            maintenant=self.maintenant,
        )

    def _creer_boite(self, quantite, **champs):
        return Boite.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            quantite_initiale=quantite,
            quantite_restante=quantite,
            **champs,
        )

    def test_stock_suffisant(self):
        self._creer_boite(30)
        # Départ dans 3 jours (6 comprimés d'ici là), 5 jours sur place (10 comprimés).
        besoin = self._besoins(3, 7)["besoins"][0]
        self.assertEqual(besoin["nombre"], 10)
        self.assertEqual(besoin["quantite"], 10)
        self.assertEqual(besoin["quantite_avant"], 6)
        self.assertEqual(besoin["stock"], 30)
        self.assertEqual(besoin["stock_au_debut"], 24)
        self.assertEqual(besoin["reste"], 14)
        self.assertEqual(besoin["manque"], 0)

    def test_stock_insuffisant(self):
        self._creer_boite(10)
        besoin = self._besoins(3, 7)["besoins"][0]
        self.assertEqual(besoin["stock_au_debut"], 4)
        self.assertEqual(besoin["reste"], 0)
        self.assertEqual(besoin["manque"], 6)

    def test_prises_du_jour_deja_passees_non_comptees(self):
        apres_le_matin = timezone.make_aware(
            datetime.datetime.combine(self.aujourdhui, datetime.time(12, 0))
        )
        besoin = rassembler_besoins_a_venir(
            self.patient, self.aujourdhui, self.aujourdhui, maintenant=apres_le_matin
        )["besoins"][0]
        self.assertEqual(besoin["nombre"], 1)

    def test_respecte_le_rythme_et_la_date_de_fin(self):
        self.prescription.horaires.all().delete()
        HoraireProgramme.objects.create(
            prescription=self.prescription,
            heure="08:00",
            quantite=2,
            intervalle_jours=2,
            date_reference=self.aujourdhui,
        )
        self.prescription.date_fin = self.aujourdhui + datetime.timedelta(days=4)
        self.prescription.save()
        # Jours 0, 2 et 4 seulement (jour 6 après la date de fin).
        besoin = self._besoins(0, 7)["besoins"][0]
        self.assertEqual(besoin["nombre"], 3)
        self.assertEqual(besoin["quantite"], 6)

    def test_au_dela_de_la_fenetre_de_generation(self):
        """Calculé depuis les horaires : aucune Prise générée n'est nécessaire."""
        besoin = self._besoins(40, 49)["besoins"][0]
        self.assertEqual(besoin["nombre"], 20)
        self.assertEqual(besoin["quantite_avant"], 80)

    def test_reserve_listee_a_part_sans_estimation(self):
        medicament = Medicament.objects.create(code_cis="EXP4R", denomination="EXPOL4R")
        reserve = Prescription.objects.create(
            patient=self.patient,
            medicament=medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        Boite.objects.create(
            patient=self.patient, medicament=medicament, quantite_initiale=8, quantite_restante=8
        )
        donnees = self._besoins(0, 7)
        self.assertEqual([b["medicament"] for b in donnees["besoins"]], ["EXPOL4"])
        self.assertEqual(len(donnees["reserves"]), 1)
        self.assertEqual(donnees["reserves"][0]["prescription"], reserve)
        self.assertEqual(donnees["reserves"][0]["stock"], 8)

    def test_signale_les_boites_qui_periment_avant_la_fin(self):
        perimee = self._creer_boite(
            10, date_peremption=self.aujourdhui + datetime.timedelta(days=5)
        )
        self._creer_boite(10, date_peremption=self.aujourdhui + datetime.timedelta(days=30))
        donnees = self._besoins(0, 7)
        self.assertEqual(donnees["boites_perimees_avant_la_fin"], [perimee])


class GenerationExcelTest(TestCase):
    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medexp3@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patexp3@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-EXP-3",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="EXP3", denomination="EXPOL3")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
            statut=Prescription.Statut.ACTIVE,
        )

    def test_genere_un_vrai_classeur_avec_les_bonnes_feuilles(self):
        """Réouvre le fichier généré avec openpyxl pour valider son contenu réel, pas juste sa génération."""
        contenu = generer_excel_patient(self.patient)
        classeur = load_workbook(io.BytesIO(contenu))

        self.assertEqual(
            set(classeur.sheetnames),
            {"Prescriptions actives", "Interactions", "Historique des prises", "Stock"},
        )

    def test_feuille_prescriptions_contient_la_bonne_ligne(self):
        contenu = generer_excel_patient(self.patient)
        classeur = load_workbook(io.BytesIO(contenu))
        feuille = classeur["Prescriptions actives"]

        self.assertEqual(feuille.cell(row=1, column=1).value, "Médicament")
        self.assertEqual(feuille.cell(row=2, column=1).value, "EXPOL3")


class ExportAPITest(APITestCase):
    def setUp(self):
        self.medecin_suiveur = creer_utilisateur_avec_role("medexpapi1@example.com", ROLE_MEDECIN)
        self.medecin_autre = creer_utilisateur_avec_role("medexpapi2@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patexpapi1@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-EXP-API-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin_suiveur, actif=True)

    def test_medecin_suiveur_peut_telecharger_le_pdf(self):
        self.client.force_authenticate(self.medecin_suiveur)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_medecin_suiveur_peut_telecharger_l_excel(self):
        self.client.force_authenticate(self.medecin_suiveur)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-excel/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

    def test_medecin_non_suiveur_ne_peut_pas_exporter(self):
        self.client.force_authenticate(self.medecin_autre)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-pdf/")
        self.assertEqual(response.status_code, 404)

    def test_patient_peut_exporter_ses_propres_donnees(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-excel/")
        self.assertEqual(response.status_code, 200)

    def test_anonyme_refuse(self):
        # 401, pas 403 : voir le commentaire détaillé dans
        # apps/patients/test_api.py::test_acces_anonyme_refuse.
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-pdf/")
        self.assertEqual(response.status_code, 401)

    def test_pdf_avec_contenu_et_periode_choisis(self):
        self.client.force_authenticate(self.medecin_suiveur)
        response = self.client.get(
            f"/api/v1/patients/{self.patient.id}/export-pdf/",
            {"contenu": "prises", "date_debut": "2026-03-01", "date_fin": "2026-03-31"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("prises-DOS-EXP-API-1.pdf", response["Content-Disposition"])

    def test_pdf_refuse_des_parametres_invalides(self):
        self.client.force_authenticate(self.medecin_suiveur)
        for parametres in (
            {"contenu": "inconnu"},
            {"date_debut": "2026-03-01"},
            {"date_debut": "01/03/2026", "date_fin": "2026-03-31"},
            {"date_debut": "2026-03-31", "date_fin": "2026-03-01"},
            {"contenu": "prescriptions", "medecin": "pas-un-uuid"},
            {"contenu": "a_venir"},
            {"contenu": "a_venir", "date_debut": "2026-03-01", "date_fin": "2026-03-31"},
        ):
            with self.subTest(parametres=parametres):
                response = self.client.get(
                    f"/api/v1/patients/{self.patient.id}/export-pdf/", parametres
                )
                self.assertEqual(response.status_code, 400)

    def test_options_d_export_listent_les_medecins_prescripteurs(self):
        medicament = Medicament.objects.create(code_cis="EXPAPI1", denomination="EXPOLAPI")
        Prescription.objects.create(
            patient=self.patient,
            medicament=medicament,
            medecin_prescripteur=self.medecin_suiveur,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )
        self.client.force_authenticate(self.user_patient)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-options/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["medecins"],
            [{"id": str(self.medecin_suiveur.id), "nom": "medexpapi1@example.com"}],
        )

    def test_medecin_non_suiveur_ne_voit_pas_les_options_d_export(self):
        self.client.force_authenticate(self.medecin_autre)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/export-options/")
        self.assertEqual(response.status_code, 404)
