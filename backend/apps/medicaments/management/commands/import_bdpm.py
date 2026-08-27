"""
Commande d'import du référentiel médicaments depuis la BDPM.

Usage :
    python manage.py import_bdpm --fichier CIS_bdpm.txt

Source officielle des fichiers :
    https://base-donnees-publique.medicaments.gouv.fr/telechargement.php

STATUT : squelette fonctionnel du palier 1. Le format exact du fichier
CIS_bdpm.txt (colonnes séparées par tabulations, encodage latin-1) est
documenté sur le site officiel et sera implémenté et testé contre un
fichier réel avant la clôture du palier 1 — volontairement non deviné
ici pour respecter la contrainte "aucune approximation".
"""

from django.core.management.base import BaseCommand, CommandError

from apps.medicaments.models import Medicament


class Command(BaseCommand):
    help = "Importe ou met à jour le référentiel des médicaments depuis un extrait officiel de la BDPM."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fichier",
            required=True,
            help="Chemin vers le fichier CIS_bdpm.txt téléchargé depuis "
            "base-donnees-publique.medicaments.gouv.fr",
        )

    def handle(self, *args, **options):
        chemin = options["fichier"]

        try:
            with open(chemin, encoding="latin-1") as f:
                lignes = f.readlines()
        except OSError as exc:
            raise CommandError(f"Impossible de lire le fichier {chemin} : {exc}")

        crees, mis_a_jour = 0, 0
        for ligne in lignes:
            champs = ligne.rstrip("\n").split("\t")
            # Colonnes BDPM (fichier CIS_bdpm.txt) dans l'ordre officiel :
            # 0: code CIS, 1: dénomination, 2: forme pharmaceutique, ...
            # La correspondance complète colonne -> champ sera finalisée et
            # testée avec un fichier réel avant la fin du palier 1.
            if len(champs) < 3:
                continue

            code_cis, denomination, forme = champs[0], champs[1], champs[2]
            _, cree = Medicament.objects.update_or_create(
                code_cis=code_cis,
                defaults={
                    "denomination": denomination,
                    "forme_pharmaceutique": forme,
                },
            )
            crees += int(cree)
            mis_a_jour += int(not cree)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {crees} médicaments créés, {mis_a_jour} mis à jour."
            )
        )
