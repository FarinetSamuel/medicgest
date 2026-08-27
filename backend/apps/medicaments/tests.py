from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.medicaments.admin import MedicamentAdmin
from apps.medicaments.models import Medicament
from django.contrib.admin.sites import AdminSite


class MedicamentModelTest(TestCase):
    def test_creation_medicament(self):
        med = Medicament.objects.create(
            code_cis="60234567",
            denomination="DOLIPRANE 1000 mg",
            forme_pharmaceutique="comprimé",
            dosage="1000 mg",
            laboratoire="Sanofi",
        )
        self.assertEqual(med.source, "BDPM")

    def test_code_cis_unique(self):
        """Le code CIS (identifiant officiel BDPM) doit être unique."""
        Medicament.objects.create(code_cis="60234567", denomination="A")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Medicament.objects.create(code_cis="60234567", denomination="B")

    def test_str_lisible(self):
        med = Medicament.objects.create(
            code_cis="60234568", denomination="EFFERALGAN", dosage="500 mg"
        )
        self.assertEqual(str(med), "EFFERALGAN (500 mg)")


class MedicamentAdminReadOnlyTest(TestCase):
    """
    Règle non négociable : le référentiel médicaments ne doit jamais être
    modifiable à la main dans l'admin — seule la commande import_bdpm
    peut le faire.
    """

    def setUp(self):
        self.admin = MedicamentAdmin(Medicament, AdminSite())

    def test_ajout_interdit_dans_admin(self):
        self.assertFalse(self.admin.has_add_permission(request=None))

    def test_modification_interdite_dans_admin(self):
        self.assertFalse(self.admin.has_change_permission(request=None))
