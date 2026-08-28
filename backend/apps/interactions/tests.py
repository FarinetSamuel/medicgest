"""
Tests du module interactions.

IMPORTANT : `thesaurus_extrait_reel.txt` est un VRAI extrait du PDF
officiel du Thésaurus ANSM (août 2023), récupéré directement depuis
ansm.sante.fr — pas un texte de test inventé. Cela permet de tester le
parseur contre le format réel, avec ses irrégularités réelles (codes
composés, entrées multi-lignes).
"""

import datetime
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.medicaments.models import Medicament, SubstanceActive
from apps.patients.models import Patient, PatientMedecin
from apps.prescriptions.models import Prescription
from apps.utilisateurs.models import ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .logique import verifier_interactions
from .models import InteractionMedicamenteuse, InteractionNonImportee
from .parseur import parser_thesaurus

CHEMIN_EXTRAIT_REEL = Path(__file__).parent / "thesaurus_extrait_reel.txt"


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(username=email.split("@")[0], email=email, password="x")
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class ParseurThesaurusTest(TestCase):
    """Tests contre le VRAI extrait officiel (voir docstring du module)."""

    def setUp(self):
        self.texte = CHEMIN_EXTRAIT_REEL.read_text(encoding="utf-8")
        self.entrees = parser_thesaurus(self.texte)

    def test_toutes_les_paires_sont_detectees(self):
        # 15 paires réellement présentes dans l'extrait officiel.
        self.assertEqual(len(self.entrees), 15)

    def test_entree_simple_correctement_classee(self):
        entree = next(
            e for e in self.entrees
            if e.protagoniste_a == "ABATACEPT" and e.protagoniste_b == "ANTI-TNF ALPHA"
        )
        self.assertFalse(entree.ambigue)
        self.assertEqual(entree.niveau, "association_deconseillee")

    def test_contre_indication_simple_correctement_classee(self):
        entree = next(
            e for e in self.entrees
            if e.protagoniste_a == "ATORVASTATINE" and e.protagoniste_b == "ITRACONAZOLE"
        )
        self.assertFalse(entree.ambigue)
        self.assertEqual(entree.niveau, "contre_indication")

    def test_code_compose_ci_asdec_apec_exclu(self):
        entree = next(
            e for e in self.entrees
            if e.protagoniste_a == "ACIDE ACETYLSALICYLIQUE" and e.protagoniste_b == "ANTICOAGULANTS ORAUX"
        )
        self.assertTrue(entree.ambigue)
        self.assertIsNone(entree.niveau)

    def test_code_compose_ci_pe_exclu(self):
        entree = next(
            e for e in self.entrees
            if e.protagoniste_a == "ACIDE ACETYLSALICYLIQUE" and e.protagoniste_b == "METHOTREXATE"
        )
        self.assertTrue(entree.ambigue)

    def test_ligne_niveau_seule_sur_sa_ligne_ne_casse_pas_le_parsing(self):
        """
        Régression du bug détecté en développement : une ligne
        "CONTRE-INDICATION" seule (tout en majuscules) ne doit pas être
        prise pour un nouveau protagoniste A et faire disparaître l'entrée.
        """
        entree = next(
            e for e in self.entrees
            if e.protagoniste_a == "ACIDE FUSIDIQUE"
        )
        self.assertFalse(entree.ambigue)
        self.assertEqual(entree.niveau, "contre_indication")

    def test_protagoniste_avec_parentheses_conserve(self):
        entree = next(
            e for e in self.entrees
            if e.protagoniste_b == "PAMPLEMOUSSE (JUS ET FRUIT)"
        )
        self.assertFalse(entree.ambigue)


class ImportThesaurusCommandTest(TestCase):
    def test_import_cree_les_bonnes_lignes(self):
        call_command("import_thesaurus", fichier=str(CHEMIN_EXTRAIT_REEL))

        self.assertEqual(InteractionMedicamenteuse.objects.count(), 13)
        self.assertEqual(InteractionNonImportee.objects.count(), 2)

        interaction = InteractionMedicamenteuse.objects.get(
            protagoniste_a="ATORVASTATINE", protagoniste_b="ITRACONAZOLE"
        )
        self.assertEqual(interaction.niveau, "contre_indication")
        self.assertEqual(str(interaction.date_publication_source), "2023-09-15")

    def test_reimport_ne_duplique_pas(self):
        call_command("import_thesaurus", fichier=str(CHEMIN_EXTRAIT_REEL))
        call_command("import_thesaurus", fichier=str(CHEMIN_EXTRAIT_REEL))
        self.assertEqual(InteractionMedicamenteuse.objects.count(), 13)


class VerifierInteractionsPatientTest(TestCase):
    def setUp(self):
        call_command("import_thesaurus", fichier=str(CHEMIN_EXTRAIT_REEL))

        self.medecin = creer_utilisateur_avec_role("medint@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patint@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-INT-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )

        self.substance_atorvastatine = SubstanceActive.objects.create(nom="ATORVASTATINE")
        self.substance_itraconazole = SubstanceActive.objects.create(nom="ITRACONAZOLE")
        self.substance_sans_interaction = SubstanceActive.objects.create(nom="PARACETAMOL")

        self.medicament_a = Medicament.objects.create(code_cis="INT1", denomination="TAHOR")
        self.medicament_a.substances_actives.add(self.substance_atorvastatine)
        self.medicament_b = Medicament.objects.create(code_cis="INT2", denomination="SPORANOX")
        self.medicament_b.substances_actives.add(self.substance_itraconazole)
        self.medicament_c = Medicament.objects.create(code_cis="INT3", denomination="DOLIPRANE")
        self.medicament_c.substances_actives.add(self.substance_sans_interaction)

    def _prescrire(self, medicament):
        return Prescription.objects.create(
            patient=self.patient,
            medicament=medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.REGULIERE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
            statut=Prescription.Statut.ACTIVE,
        )

    def test_detecte_une_interaction_reelle_entre_deux_prescriptions_actives(self):
        self._prescrire(self.medicament_a)
        self._prescrire(self.medicament_b)

        resultats = verifier_interactions(self.patient)

        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].niveau, "contre_indication")

    def test_pas_d_interaction_sans_correspondance(self):
        self._prescrire(self.medicament_a)
        self._prescrire(self.medicament_c)

        resultats = verifier_interactions(self.patient)
        self.assertEqual(resultats, [])

    def test_prescription_arretee_non_prise_en_compte(self):
        self._prescrire(self.medicament_a)
        prescription_b = self._prescrire(self.medicament_b)
        prescription_b.statut = Prescription.Statut.ARRETEE
        prescription_b.save()

        resultats = verifier_interactions(self.patient)
        self.assertEqual(resultats, [])


class VerificationInteractionsAPITest(APITestCase):
    def setUp(self):
        call_command("import_thesaurus", fichier=str(CHEMIN_EXTRAIT_REEL))

        self.medecin = creer_utilisateur_avec_role("medintapi@example.com", ROLE_MEDECIN)
        self.autre_medecin = creer_utilisateur_avec_role("medintapi2@example.com", ROLE_MEDECIN)
        self.user_patient = creer_utilisateur_avec_role("patintapi@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=self.user_patient,
            numero_dossier="DOS-INT-API-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        PatientMedecin.objects.create(patient=self.patient, medecin=self.medecin, actif=True)

        substance_a = SubstanceActive.objects.create(nom="ATORVASTATINE")
        substance_b = SubstanceActive.objects.create(nom="ITRACONAZOLE")
        med_a = Medicament.objects.create(code_cis="INTAPI1", denomination="TAHOR")
        med_a.substances_actives.add(substance_a)
        med_b = Medicament.objects.create(code_cis="INTAPI2", denomination="SPORANOX")
        med_b.substances_actives.add(substance_b)

        for med in (med_a, med_b):
            Prescription.objects.create(
                patient=self.patient,
                medicament=med,
                medecin_prescripteur=self.medecin,
                type_prise=Prescription.TypePrise.REGULIERE,
                dose_quantite=1,
                dose_unite="comprimé",
                date_debut=datetime.date(2026, 1, 1),
                statut=Prescription.Statut.ACTIVE,
            )

    def test_medecin_suiveur_voit_l_interaction_avec_avertissement(self):
        self.client.force_authenticate(self.medecin)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/verifier-interactions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["interactions"]), 1)
        self.assertIn("15/09/2023", response.data["avertissement"])
        self.assertEqual(response.data["date_publication_source"], "2023-09-15")

    def test_medecin_non_suiveur_recoit_404(self):
        self.client.force_authenticate(self.autre_medecin)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/verifier-interactions/")
        self.assertEqual(response.status_code, 404)

    def test_patient_voit_ses_propres_interactions(self):
        self.client.force_authenticate(self.user_patient)
        response = self.client.get(f"/api/v1/patients/{self.patient.id}/verifier-interactions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["interactions"]), 1)
