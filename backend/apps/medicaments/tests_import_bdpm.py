"""
Tests de la commande import_bdpm avec des lignes synthétiques respectant
EXACTEMENT l'ordre de colonnes documenté par l'ANSM (v3, 18/12/2024) :
https://base-donnees-publique.medicaments.gouv.fr/telechargement.php

Ces lignes ne sont pas de vraies données BDPM (impossible de télécharger
le fichier officiel depuis cet environnement, domaine non autorisé), mais
respectent fidèlement le format documenté pour valider le parsing.
"""

import tempfile

from django.core.management import call_command
from django.test import TestCase

from apps.medicaments.models import Medicament


class ImportBdpmCommandTest(TestCase):
    def _fichier_temporaire(self, lignes, encoding="latin-1"):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding=encoding)
        f.write("\n".join(lignes))
        f.close()
        return f.name

    def test_import_cis_bdpm_seul(self):
        # 12 colonnes exactement, dans l'ordre documenté (section 3.1) :
        # CIS / dénomination / forme / voies / statut AMM / procédure AMM /
        # état commercialisation / date AMM / statutBdm / n° autor. euro /
        # titulaire(s) / surveillance renforcée.
        ligne = "\t".join([
            "60234567", "DOLIPRANE 1000 mg, comprimé", "comprimé",
            "orale", "Autorisation active", "Procédure nationale",
            "Commercialisée", "01/01/2000", "", "",
            "SANOFI", "Non",
        ])
        chemin = self._fichier_temporaire([ligne])

        call_command("import_bdpm", fichier=chemin)

        med = Medicament.objects.get(code_cis="60234567")
        self.assertEqual(med.denomination, "DOLIPRANE 1000 mg, comprimé")
        self.assertEqual(med.forme_pharmaceutique, "comprimé")
        self.assertEqual(med.laboratoire, "SANOFI")
        self.assertEqual(med.dosage, "")  # pas de fichier composition fourni
        self.assertEqual(med.source, "BDPM")

    def test_import_avec_fichier_composition_renseigne_le_dosage(self):
        ligne_cis = "\t".join([
            "60234568", "EFFERALGAN 500 mg", "comprimé effervescent",
            "orale", "Autorisation active", "Procédure nationale",
            "Commercialisée", "01/01/2000", "", "",
            "UPSA", "Non",
        ])
        chemin_cis = self._fichier_temporaire([ligne_cis])

        # 8 colonnes exactement, dans l'ordre documenté (section 3.3) :
        # CIS / désignation élément / code substance / dénomination
        # substance / dosage / référence dosage / nature composant /
        # n° liaison SA/FT.
        ligne_compo = "\t".join([
            "60234568", "comprimé", "1234", "PARACETAMOL",
            "500 mg", "un comprimé", "SA", "",
        ])
        chemin_compo = self._fichier_temporaire([ligne_compo])

        call_command("import_bdpm", fichier=chemin_cis, fichier_composition=chemin_compo)

        med = Medicament.objects.get(code_cis="60234568")
        self.assertEqual(med.dosage, "PARACETAMOL 500 mg")

    def test_plusieurs_substances_actives_sont_concatenees(self):
        ligne_cis = "\t".join([
            "60234569", "MEDICAMENT COMBINE", "comprimé",
            "orale", "Autorisation active", "Procédure nationale",
            "Commercialisée", "01/01/2000", "", "",
            "LABO TEST", "Non",
        ])
        chemin_cis = self._fichier_temporaire([ligne_cis])

        lignes_compo = [
            "\t".join(["60234569", "comprimé", "1", "SUBSTANCE A", "10 mg", "un comprimé", "SA", ""]),
            "\t".join(["60234569", "comprimé", "2", "SUBSTANCE B", "20 mg", "un comprimé", "SA", ""]),
        ]
        chemin_compo = self._fichier_temporaire(lignes_compo)

        call_command("import_bdpm", fichier=chemin_cis, fichier_composition=chemin_compo)

        med = Medicament.objects.get(code_cis="60234569")
        self.assertEqual(med.dosage, "SUBSTANCE A 10 mg + SUBSTANCE B 20 mg")

    def test_fraction_therapeutique_st_est_ignoree(self):
        """Seules les substances actives (SA) comptent, pas les fractions thérapeutiques (ST)."""
        ligne_cis = "\t".join([
            "60234570", "MEDICAMENT AVEC SEL", "comprimé",
            "orale", "Autorisation active", "Procédure nationale",
            "Commercialisée", "01/01/2000", "", "",
            "LABO TEST", "Non",
        ])
        chemin_cis = self._fichier_temporaire([ligne_cis])

        lignes_compo = [
            "\t".join(["60234570", "comprimé", "1", "SUBSTANCE PRINCIPALE", "10 mg", "un comprimé", "SA", ""]),
            "\t".join(["60234570", "comprimé", "2", "SEL ASSOCIE", "5 mg", "un comprimé", "ST", "1"]),
        ]
        chemin_compo = self._fichier_temporaire(lignes_compo)

        call_command("import_bdpm", fichier=chemin_cis, fichier_composition=chemin_compo)

        med = Medicament.objects.get(code_cis="60234570")
        self.assertEqual(med.dosage, "SUBSTANCE PRINCIPALE 10 mg")

    def test_reimport_met_a_jour_sans_dupliquer(self):
        ligne_v1 = "\t".join([
            "60234571", "NOM INITIAL", "comprimé", "orale",
            "Autorisation active", "Procédure nationale", "Commercialisée",
            "01/01/2000", "", "", "LABO TEST", "Non",
        ])
        chemin_v1 = self._fichier_temporaire([ligne_v1])
        call_command("import_bdpm", fichier=chemin_v1)

        ligne_v2 = "\t".join([
            "60234571", "NOM CORRIGE", "comprimé", "orale",
            "Autorisation active", "Procédure nationale", "Commercialisée",
            "01/01/2000", "", "", "LABO TEST", "Non",
        ])
        chemin_v2 = self._fichier_temporaire([ligne_v2])
        call_command("import_bdpm", fichier=chemin_v2)

        self.assertEqual(Medicament.objects.filter(code_cis="60234571").count(), 1)
        self.assertEqual(Medicament.objects.get(code_cis="60234571").denomination, "NOM CORRIGE")

    def test_champs_longs_ne_font_pas_planter_l_import(self):
        """
        Reproduit le bug réel rencontré en production : un médicament
        combiné avec de nombreuses substances actives génère un dosage
        concaténé très long, qui dépassait l'ancien max_length=150.
        """
        ligne_cis = "\t".join([
            "60234573", "MEDICAMENT MULTI-SUBSTANCES", "comprimé",
            "orale", "Autorisation active", "Procédure nationale",
            "Commercialisée", "01/01/2000", "", "",
            "LABO TEST", "Non",
        ])
        chemin_cis = self._fichier_temporaire([ligne_cis])

        lignes_compo = [
            "\t".join(["60234573", "comprimé", str(i), f"SUBSTANCE NUMERO {i} AVEC UN NOM ASSEZ LONG",
                       f"{i}0 mg", "un comprimé", "SA", ""])
            for i in range(1, 11)
        ]
        chemin_compo = self._fichier_temporaire(lignes_compo)

        call_command("import_bdpm", fichier=chemin_cis, fichier_composition=chemin_compo)

        med = Medicament.objects.get(code_cis="60234573")
        self.assertLessEqual(len(med.dosage), 500)

    def test_erreur_sur_une_ligne_n_interrompt_pas_les_autres(self):
        lignes = [
            "\t".join(["60234574", "MEDICAMENT VALIDE 1", "comprimé", "orale",
                       "Autorisation active", "Procédure nationale", "Commercialisée",
                       "01/01/2000", "", "", "LABO", "Non"]),
            "ligne mal formée sans assez de colonnes",
            "\t".join(["60234575", "MEDICAMENT VALIDE 2", "comprimé", "orale",
                       "Autorisation active", "Procédure nationale", "Commercialisée",
                       "01/01/2000", "", "", "LABO", "Non"]),
        ]
        chemin = self._fichier_temporaire(lignes)

        call_command("import_bdpm", fichier=chemin)

        self.assertTrue(Medicament.objects.filter(code_cis="60234574").exists())
        self.assertTrue(Medicament.objects.filter(code_cis="60234575").exists())

        """
        Limitation documentée et assumée : le code ATC n'est pas dans les
        fichiers gratuits pour l'ensemble du référentiel (uniquement pour
        le sous-ensemble MITM, non importé par cette commande).
        """
        ligne = "\t".join([
            "60234572", "TEST ATC", "comprimé", "orale",
            "Autorisation active", "Procédure nationale", "Commercialisée",
            "01/01/2000", "", "", "LABO TEST", "Non",
        ])
        chemin = self._fichier_temporaire([ligne])
        call_command("import_bdpm", fichier=chemin)

        med = Medicament.objects.get(code_cis="60234572")
        self.assertEqual(med.code_atc, "")
