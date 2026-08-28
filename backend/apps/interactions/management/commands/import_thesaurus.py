"""
Importe le Thésaurus des interactions médicamenteuses de l'ANSM (dernière
version, non actualisée depuis le 15/09/2023).

Le PDF officiel doit d'abord être converti en texte avec pdftotext
(-layout conserve la mise en page, importante pour le parseur) :

    pdftotext -layout thesaurus.pdf thesaurus.txt
    python manage.py import_thesaurus --fichier thesaurus.txt

Seules les entrées à niveau de gravité NON ambigu sont importées dans
InteractionMedicamenteuse. Les entrées à niveau conditionnel (codes
composés type "CI - ASDEC - APEC") sont enregistrées séparément dans
InteractionNonImportee, pour revue manuelle — jamais importées avec un
niveau deviné.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.interactions.models import InteractionMedicamenteuse, InteractionNonImportee
from apps.interactions.parseur import parser_thesaurus


class Command(BaseCommand):
    help = "Importe le Thésaurus des interactions médicamenteuses ANSM (texte extrait du PDF officiel)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fichier",
            required=True,
            help="Chemin vers le texte extrait du PDF officiel (pdftotext -layout).",
        )

    def handle(self, *args, **options):
        try:
            with open(options["fichier"], encoding="utf-8") as f:
                texte = f.read()
        except OSError as exc:
            raise CommandError(f"Impossible de lire le fichier : {exc}")

        entrees = parser_thesaurus(texte)

        importees, doublons, exclues = 0, 0, 0
        for entree in entrees:
            if entree.ambigue:
                InteractionNonImportee.objects.get_or_create(
                    protagoniste_a=entree.protagoniste_a[:255],
                    protagoniste_b=entree.protagoniste_b[:255],
                    defaults={
                        "texte_brut": entree.texte_brut,
                        "raison_exclusion": entree.raison_exclusion[:255],
                    },
                )
                exclues += 1
                continue

            _, cree = InteractionMedicamenteuse.objects.get_or_create(
                protagoniste_a=entree.protagoniste_a[:255],
                protagoniste_b=entree.protagoniste_b[:255],
                defaults={"niveau": entree.niveau, "libelle": entree.texte_brut},
            )
            if cree:
                importees += 1
            else:
                doublons += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {importees} interaction(s) importée(s), "
                f"{doublons} déjà existante(s), "
                f"{exclues} exclue(s) pour revue manuelle (niveau conditionnel)."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Rappel : le Thésaurus ANSM n'est plus mis à jour depuis le 15/09/2023. "
                "Cette donnée est figée — voir le README."
            )
        )
