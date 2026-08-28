"""
Commande d'import du référentiel médicaments depuis la BDPM officielle.

Sources et format confirmés par la documentation officielle ANSM :
"Contenu et format des fichiers téléchargeables de la BDPM" (v3, 18/12/2024)
https://base-donnees-publique.medicaments.gouv.fr/telechargement.php

Format commun à tous les fichiers BDPM : texte, séparateur tabulation,
encodage latin-1, PAS de ligne d'en-tête, PAS de délimiteur de champ.

Usage :
    # Import minimal (dénomination, forme, laboratoire) :
    python manage.py import_bdpm --fichier CIS_bdpm.txt

    # Avec dosage (croise avec le fichier des compositions) :
    python manage.py import_bdpm --fichier CIS_bdpm.txt \
        --fichier-composition CIS_COMPO_bdpm.txt

Limitation assumée et documentée (pas une approximation silencieuse) :
le code ATC n'est disponible, dans les fichiers en téléchargement libre,
que pour le sous-ensemble des médicaments d'intérêt thérapeutique majeur
(fichier CIS_MITM.txt) — il n'est donc PAS renseigné par cette commande
pour l'ensemble du référentiel. Le champ Medicament.code_atc reste vide
tant qu'un import dédié MITM n'est pas ajouté.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from apps.medicaments.models import Medicament

# Index des colonnes dans CIS_bdpm.txt (0-indexé), confirmés par la
# documentation officielle ANSM v3 (18/12/2024), section 3.1.
COL_CIS_CODE_CIS = 0
COL_CIS_DENOMINATION = 1
COL_CIS_FORME_PHARMA = 2
COL_CIS_TITULAIRES = 10

# Index des colonnes dans CIS_COMPO_bdpm.txt, section 3.3.
COL_COMPO_CODE_CIS = 0
COL_COMPO_DENOMINATION_SUBSTANCE = 3
COL_COMPO_DOSAGE = 4
COL_COMPO_NATURE_COMPOSANT = 6
NATURE_PRINCIPE_ACTIF = "SA"


class Command(BaseCommand):
    help = "Importe ou met à jour le référentiel des médicaments depuis les fichiers officiels de la BDPM."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fichier",
            required=True,
            help="Chemin vers CIS_bdpm.txt (fichier des spécialités).",
        )
        parser.add_argument(
            "--fichier-composition",
            required=False,
            help="Chemin vers CIS_COMPO_bdpm.txt (optionnel, pour renseigner le dosage).",
        )

    def handle(self, *args, **options):
        dosages_par_cis = {}
        if options.get("fichier_composition"):
            dosages_par_cis = self._lire_dosages(options["fichier_composition"])

        lignes = self._lire_fichier(options["fichier"])

        crees, mis_a_jour, ignorees = 0, 0, 0
        for ligne in lignes:
            champs = ligne.rstrip("\n").split("\t")
            if len(champs) <= COL_CIS_TITULAIRES:
                ignorees += 1
                continue

            code_cis = champs[COL_CIS_CODE_CIS].strip()
            _, cree = Medicament.objects.update_or_create(
                code_cis=code_cis,
                defaults={
                    "denomination": champs[COL_CIS_DENOMINATION].strip(),
                    "forme_pharmaceutique": champs[COL_CIS_FORME_PHARMA].strip(),
                    "laboratoire": champs[COL_CIS_TITULAIRES].strip(),
                    "dosage": dosages_par_cis.get(code_cis, ""),
                },
            )
            crees += int(cree)
            mis_a_jour += int(not cree)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {crees} créé(s), {mis_a_jour} mis à jour, "
                f"{ignorees} ligne(s) ignorée(s) (format inattendu)."
            )
        )
        if not options.get("fichier_composition"):
            self.stdout.write(
                self.style.WARNING(
                    "Dosage non renseigné (--fichier-composition non fourni). "
                    "code_atc non renseigné dans tous les cas (limitation documentée, voir docstring)."
                )
            )

    def _lire_fichier(self, chemin):
        try:
            with open(chemin, encoding="latin-1") as f:
                return f.readlines()
        except OSError as exc:
            raise CommandError(f"Impossible de lire le fichier {chemin} : {exc}")

    def _lire_dosages(self, chemin):
        """
        Construit {code_cis: dosage_lisible} à partir de CIS_COMPO_bdpm.txt.
        Un médicament peut avoir plusieurs substances actives (SA) : leurs
        dosages sont concaténés avec ' + ', jamais moyennés ou choisis
        arbitrairement — l'information complète est conservée.
        """
        substances_par_cis = defaultdict(list)
        for ligne in self._lire_fichier(chemin):
            champs = ligne.rstrip("\n").split("\t")
            if len(champs) <= COL_COMPO_NATURE_COMPOSANT:
                continue
            if champs[COL_COMPO_NATURE_COMPOSANT].strip() != NATURE_PRINCIPE_ACTIF:
                continue  # on ne garde que les principes actifs, pas les fractions thérapeutiques

            code_cis = champs[COL_COMPO_CODE_CIS].strip()
            substance = champs[COL_COMPO_DENOMINATION_SUBSTANCE].strip()
            dosage = champs[COL_COMPO_DOSAGE].strip()
            substances_par_cis[code_cis].append(f"{substance} {dosage}".strip())

        return {
            code_cis: " + ".join(substances)
            for code_cis, substances in substances_par_cis.items()
        }
