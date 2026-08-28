import datetime
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from apps.medicaments.models import Medicament
from apps.patients.models import Patient
from apps.prescriptions.models import Prescription, Prise
from apps.utilisateurs.models import ROLE_MEDECIN, ROLE_PATIENT, Utilisateur

from .logique import consommation_moyenne_par_jour, jours_restants_estimes
from .models import Boite, MouvementStock


def creer_utilisateur_avec_role(email, role):
    user = Utilisateur.objects.create_user(username=email.split("@")[0], email=email, password="x")
    groupe, _ = Group.objects.get_or_create(name=role)
    user.groups.add(groupe)
    return user


class DecompteAutomatiqueStockTest(TestCase):
    """
    Décision validée : le stock se décrémente automatiquement à chaque
    prise enregistrée, en FEFO (boîte qui périme le plus tôt d'abord).
    """

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medstock1@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patstock1@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-STOCK-1",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.FEMININ,
        )
        self.medicament = Medicament.objects.create(code_cis="STK1", denomination="STOCKOL")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_une_prise_decremente_la_boite_active(self):
        boite = Boite.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            quantite_initiale=10,
            quantite_restante=10,
        )
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=3,
            statut=Prise.Statut.PRISE,
        )
        boite.refresh_from_db()
        self.assertEqual(boite.quantite_restante, Decimal("7"))

    def test_fefo_consomme_la_boite_qui_perime_le_plus_tot_en_premier(self):
        boite_lointaine = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
            date_peremption=datetime.date(2027, 1, 1),
        )
        boite_proche = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
            date_peremption=datetime.date(2026, 6, 1),
        )
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=4,
            statut=Prise.Statut.PRISE,
        )
        boite_proche.refresh_from_db()
        boite_lointaine.refresh_from_db()
        self.assertEqual(boite_proche.quantite_restante, Decimal("6"))
        self.assertEqual(boite_lointaine.quantite_restante, Decimal("10"))

    def test_bascule_sur_la_boite_suivante_quand_la_premiere_est_epuisee(self):
        boite_1 = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=2, quantite_restante=2,
            date_peremption=datetime.date(2026, 6, 1),
        )
        boite_2 = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
            date_peremption=datetime.date(2027, 1, 1),
        )
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=5,
            statut=Prise.Statut.PRISE,
        )
        boite_1.refresh_from_db()
        boite_2.refresh_from_db()
        self.assertEqual(boite_1.quantite_restante, Decimal("0"))
        self.assertEqual(boite_1.statut, Boite.Statut.EPUISEE)
        self.assertEqual(boite_2.quantite_restante, Decimal("7"))

    def test_suppression_de_la_prise_annule_le_decompte(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
        )
        prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=3,
            statut=Prise.Statut.PRISE,
        )
        boite.refresh_from_db()
        self.assertEqual(boite.quantite_restante, Decimal("7"))

        prise.delete()
        boite.refresh_from_db()
        self.assertEqual(boite.quantite_restante, Decimal("10"))
        self.assertEqual(MouvementStock.objects.filter(boite=boite).count(), 0)

    def test_modification_de_la_quantite_reajuste_le_decompte(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
        )
        prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=3,
            statut=Prise.Statut.PRISE,
        )
        boite.refresh_from_db()
        self.assertEqual(boite.quantite_restante, Decimal("7"))

        prise.quantite_prise = 5
        prise.save()
        boite.refresh_from_db()
        self.assertEqual(boite.quantite_restante, Decimal("5"))
        # Un seul mouvement doit exister pour cette prise (l'ancien a été
        # remplacé, pas cumulé).
        self.assertEqual(MouvementStock.objects.filter(prise=prise).count(), 1)

    def test_boite_epuisee_redevient_active_si_le_decompte_est_annule(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=3, quantite_restante=3,
        )
        prise = Prise.objects.create(
            prescription=self.prescription,
            date_heure_reelle=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prise=3,
            statut=Prise.Statut.PRISE,
        )
        boite.refresh_from_db()
        self.assertEqual(boite.statut, Boite.Statut.EPUISEE)

        prise.delete()
        boite.refresh_from_db()
        self.assertEqual(boite.statut, Boite.Statut.ACTIVE)

    def test_prise_non_prise_ne_decremente_rien(self):
        """Une Prise au statut ATTENDUE (générée à l'avance) ne doit pas toucher le stock."""
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
        )
        Prise.objects.create(
            prescription=self.prescription,
            date_heure_prevue=timezone.make_aware(datetime.datetime(2026, 1, 5, 10, 0)),
            quantite_prevue=1,
            statut=Prise.Statut.ATTENDUE,
        )
        boite.refresh_from_db()
        self.assertEqual(boite.quantite_restante, Decimal("10"))


class AlerteStockTest(TestCase):
    """Décision validée : les deux types de seuil (quantité et jours) coexistent, indépendants."""

    def setUp(self):
        self.medecin = creer_utilisateur_avec_role("medstock2@example.com", ROLE_MEDECIN)
        user_patient = creer_utilisateur_avec_role("patstock2@example.com", ROLE_PATIENT)
        self.patient = Patient.objects.create(
            utilisateur=user_patient,
            numero_dossier="DOS-STOCK-2",
            date_naissance=datetime.date(1980, 1, 1),
            sexe=Patient.Sexe.MASCULIN,
        )
        self.medicament = Medicament.objects.create(code_cis="STK2", denomination="STOCKOL2")
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            medicament=self.medicament,
            medecin_prescripteur=self.medecin,
            type_prise=Prescription.TypePrise.RESERVE,
            dose_quantite=1,
            dose_unite="comprimé",
            date_debut=datetime.date(2026, 1, 1),
        )

    def test_alerte_quantite_se_declenche_sous_le_seuil(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=4, seuil_alerte_quantite=5,
        )
        self.assertTrue(boite.en_alerte_quantite)
        self.assertTrue(boite.en_alerte)

    def test_pas_d_alerte_quantite_au_dessus_du_seuil(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=8, seuil_alerte_quantite=5,
        )
        self.assertFalse(boite.en_alerte_quantite)

    def test_pas_d_alerte_sans_seuil_defini(self):
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=1,
        )
        self.assertFalse(boite.en_alerte)

    def test_consommation_moyenne_par_jour(self):
        maintenant = timezone.now()
        for i in range(4):
            Prise.objects.create(
                prescription=self.prescription,
                date_heure_reelle=maintenant - datetime.timedelta(days=i),
                quantite_prise=1,
                statut=Prise.Statut.PRISE,
            )
        # 4 prises de 1 sur une fenêtre de 14 jours -> 4/14
        conso = consommation_moyenne_par_jour(self.patient, self.medicament)
        self.assertAlmostEqual(float(conso), 4 / 14, places=4)

    def test_jours_restants_estimes_none_sans_historique(self):
        Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=10, quantite_restante=10,
        )
        self.assertIsNone(jours_restants_estimes(self.patient, self.medicament))

    def test_alerte_jours_se_declenche_selon_consommation_reelle(self):
        """
        Les Prise créées ci-dessous décrémentent aussi réellement le stock
        (signal), donc on part d'un stock large pour isoler l'effet du
        calcul de seuil de l'effet du décompte automatique lui-même.
        """
        boite = Boite.objects.create(
            patient=self.patient, medicament=self.medicament,
            quantite_initiale=1000, quantite_restante=1000, seuil_alerte_jours=990,
        )
        maintenant = timezone.now()
        for i in range(14):
            Prise.objects.create(
                prescription=self.prescription,
                date_heure_reelle=maintenant - datetime.timedelta(days=i),
                quantite_prise=1,
                statut=Prise.Statut.PRISE,
            )
        boite.refresh_from_db()
        # 14 prises de 1 -> stock réel décompté à 986, consommation
        # mesurée à 1/jour -> jours_restants = 986, sous le seuil de 990.
        self.assertEqual(boite.quantite_restante, Decimal("986"))
        self.assertTrue(boite.en_alerte_jours)
