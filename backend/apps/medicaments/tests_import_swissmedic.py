"""
Tests de la commande import_swissmedic avec une archive ZIP synthétique
respectant EXACTEMENT la structure XML confirmée en inspectant un export
réel de https://ogd.swissmedic.cloud/ogd-arzneimittel/Daten/OGD.zip
(nommage des balises, absence de préfixe de namespace sur les enfants).
"""

import tempfile
import zipfile

from django.core.management import call_command
from django.test import TestCase

from apps.medicaments.models import Medicament, SubstanceActive

NS = 'xmlns:n0="http://ccsap.bit.admin.ch/SWISSMEDIC/LIMS_HMIT_KHZ"'


def _adressen(entrees):
    lignes = "".join(
        f"<ADRESSEN><PARTNER_NR>{p}</PARTNER_NR><FIRMENNAME>{n}</FIRMENNAME></ADRESSEN>"
        for p, n in entrees
    )
    return f'<?xml version="1.0" encoding="utf-8"?><n0:SMC_Adressen {NS}>{lignes}</n0:SMC_Adressen>'


def _synonymes(entrees):
    lignes = "".join(
        f"<SYNONYME><STOFF_ID>{sid}</STOFF_ID><SYNONYM_CODE>LN</SYNONYM_CODE>"
        f"<LAUFENDE_NR>001</LAUFENDE_NR><STOFFSYNONYM>{nom}</STOFFSYNONYM><QUELLE>DCI</QUELLE></SYNONYME>"
        for sid, nom in entrees
    )
    return f'<?xml version="1.0" encoding="utf-8"?><n0:SMC_Synonyme {NS}>{lignes}</n0:SMC_Synonyme>'


def _declarations(entrees):
    lignes = "".join(
        f"<DEKLARATION><ZULASSUNGSNUMMER>{zn}</ZULASSUNGSNUMMER><SEQUENZNUMMER>{sn}</SEQUENZNUMMER>"
        f"<STOFF_ID>{sid}</STOFF_ID><STOFFKATEGORIE>{cat}</STOFFKATEGORIE>"
        f"<MENGE>{menge}</MENGE><MENGEN_EINHEIT>{unite}</MENGEN_EINHEIT></DEKLARATION>"
        for zn, sn, sid, cat, menge, unite in entrees
    )
    return f'<?xml version="1.0" encoding="utf-8"?><n0:SMC_Deklaration {NS}>{lignes}</n0:SMC_Deklaration>'


def _praeparate(entrees):
    lignes = "".join(
        f"<PRAEPARAT><VERWENDUNG>{verwendung}</VERWENDUNG><ZULASSUNGSNUMMER>{zn}</ZULASSUNGSNUMMER>"
        f"<PRAEPARATENAME>{nom}</PRAEPARATENAME><ARZNEIFORM>{form}</ARZNEIFORM>"
        f"<ATC_CODE>{atc}</ATC_CODE><ZULASSUNGSINHABERIN>{titulaire}</ZULASSUNGSINHABERIN></PRAEPARAT>"
        for verwendung, zn, nom, form, atc, titulaire in entrees
    )
    return f'<?xml version="1.0" encoding="utf-8"?><n0:SMC_Praeparat {NS}>{lignes}</n0:SMC_Praeparat>'


def _sequenzen(entrees):
    lignes = "".join(
        f"<SEQUENZ><ZULASSUNGSNUMMER>{zn}</ZULASSUNGSNUMMER><SEQUENZNUMMER>{sn}</SEQUENZNUMMER>"
        f"<ZULASSUNGSSTATUS>{statut}</ZULASSUNGSSTATUS><SEQUENZNAME>{nom}</SEQUENZNAME></SEQUENZ>"
        for zn, sn, statut, nom in entrees
    )
    return f'<?xml version="1.0" encoding="utf-8"?><n0:SMC_Sequenz {NS}>{lignes}</n0:SMC_Sequenz>'


class ImportSwissmedicCommandTest(TestCase):
    def _archive(
        self,
        praeparate,
        sequenzen,
        declarations=(),
        synonymes=(),
        adressen=(),
    ):
        chemin = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
        with zipfile.ZipFile(chemin, "w") as z:
            z.writestr("OGD-Praeparate.XML", _praeparate(praeparate))
            z.writestr("OGD-Sequenzen.XML", _sequenzen(sequenzen))
            z.writestr("OGD-Deklarationen.XML", _declarations(declarations))
            z.writestr("OGD-Stoff-Synonyme.XML", _synonymes(synonymes))
            z.writestr("OGD-Adressen.XML", _adressen(adressen))
        return chemin

    def test_import_medicament_humain_autorise_avec_composition(self):
        chemin = self._archive(
            praeparate=[("HAM", "10029", "Nom Praeparat", "TROF", "C01EX", "1000324")],
            sequenzen=[("10029", "2", "Z", "Zeller Herz und Nerven Classic")],
            declarations=[("10029", "2", "SID1", "WIRKS", "31", "MG")],
            synonymes=[("SID1", "crataegi fructus")],
            adressen=[("1000324", "Max Zeller Söhne AG")],
        )

        call_command("import_swissmedic", fichier_zip=chemin)

        med = Medicament.objects.get(code_cis="CH-10029-2")
        self.assertEqual(med.denomination, "Zeller Herz und Nerven Classic")
        self.assertEqual(med.forme_pharmaceutique, "TROF")
        self.assertEqual(med.code_atc, "C01EX")
        self.assertEqual(med.laboratoire, "Max Zeller Söhne AG")
        self.assertEqual(med.dosage, "crataegi fructus 31MG")
        self.assertEqual(med.source, Medicament.Source.SWISSMEDIC)
        self.assertFalse(med.verification_interactions_fiable)
        self.assertEqual(
            list(med.substances_actives.values_list("nom", flat=True)), ["CRATAEGI FRUCTUS"]
        )

    def test_medicament_veterinaire_est_ignore(self):
        chemin = self._archive(
            praeparate=[("TAM", "20000", "Med Veto", "COMP", "QJ01", "1")],
            sequenzen=[("20000", "1", "Z", "Med Veto")],
        )

        call_command("import_swissmedic", fichier_zip=chemin)

        self.assertFalse(Medicament.objects.filter(code_cis="CH-20000-1").exists())

    def test_sequence_non_autorisee_est_ignoree(self):
        chemin = self._archive(
            praeparate=[("HAM", "30000", "Med Revoque", "COMP", "N02BE", "1")],
            sequenzen=[("30000", "1", "W", "Med Revoque")],  # W = widerrufen, pas "Z"
        )

        call_command("import_swissmedic", fichier_zip=chemin)

        self.assertFalse(Medicament.objects.filter(code_cis="CH-30000-1").exists())

    def test_substance_non_resolue_est_exclue_sans_deviner(self):
        chemin = self._archive(
            praeparate=[("HAM", "40000", "Med Inconnu", "COMP", "A01AA", "1")],
            sequenzen=[("40000", "1", "Z", "Med Inconnu")],
            declarations=[("40000", "1", "SID_INTROUVABLE", "WIRKS", "10", "MG")],
            synonymes=[],  # STOFF_ID non résolu
        )

        call_command("import_swissmedic", fichier_zip=chemin)

        med = Medicament.objects.get(code_cis="CH-40000-1")
        self.assertEqual(med.dosage, "")
        self.assertEqual(med.substances_actives.count(), 0)

    def test_composant_non_actif_est_ignore(self):
        """Seuls les composants STOFFKATEGORIE=WIRKS comptent (équivalent du filtre SA de import_bdpm)."""
        chemin = self._archive(
            praeparate=[("HAM", "50000", "Med Excipient", "COMP", "A01AA", "1")],
            sequenzen=[("50000", "1", "Z", "Med Excipient")],
            declarations=[
                ("50000", "1", "SID_ACTIF", "WIRKS", "10", "MG"),
                ("50000", "1", "SID_EXCIPIENT", "HILFS", "5", "MG"),
            ],
            synonymes=[("SID_ACTIF", "paracetamolum"), ("SID_EXCIPIENT", "lactosum")],
        )

        call_command("import_swissmedic", fichier_zip=chemin)

        med = Medicament.objects.get(code_cis="CH-50000-1")
        self.assertEqual(med.dosage, "paracetamolum 10MG")

    def test_reimport_met_a_jour_sans_dupliquer(self):
        chemin_v1 = self._archive(
            praeparate=[("HAM", "60000", "Nom Initial", "COMP", "A01AA", "1")],
            sequenzen=[("60000", "1", "Z", "Nom Initial")],
        )
        call_command("import_swissmedic", fichier_zip=chemin_v1)

        chemin_v2 = self._archive(
            praeparate=[("HAM", "60000", "Nom Corrige", "COMP", "A01AA", "1")],
            sequenzen=[("60000", "1", "Z", "Nom Corrige")],
        )
        call_command("import_swissmedic", fichier_zip=chemin_v2)

        self.assertEqual(Medicament.objects.filter(code_cis="CH-60000-1").count(), 1)
        self.assertEqual(Medicament.objects.get(code_cis="CH-60000-1").denomination, "Nom Corrige")

    def test_bdpm_et_swissmedic_ne_partagent_pas_de_substance_par_erreur(self):
        """
        Aucun rapprochement n'est tenté entre les noms latins suisses et
        les noms français existants : un import BDPM préalable de
        PARACETAMOL ne doit pas être réutilisé pour "paracetamolum".
        """
        SubstanceActive.objects.create(nom="PARACETAMOL")

        chemin = self._archive(
            praeparate=[("HAM", "70000", "Med Paracetamol CH", "COMP", "N02BE", "1")],
            sequenzen=[("70000", "1", "Z", "Med Paracetamol CH")],
            declarations=[("70000", "1", "SID1", "WIRKS", "500", "MG")],
            synonymes=[("SID1", "paracetamolum")],
        )
        call_command("import_swissmedic", fichier_zip=chemin)

        self.assertEqual(SubstanceActive.objects.count(), 2)
        med = Medicament.objects.get(code_cis="CH-70000-1")
        self.assertEqual(
            list(med.substances_actives.values_list("nom", flat=True)), ["PARACETAMOLUM"]
        )
