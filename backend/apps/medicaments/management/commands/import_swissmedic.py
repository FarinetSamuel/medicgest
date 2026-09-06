"""
Commande d'import du référentiel médicaments suisse depuis les données
Open Government Data (OGD) officielles de Swissmedic.

Source confirmée : https://opendata.swiss/fr/dataset/daten-von-human-und-tierarzneimitteln
(organisme Swissmedic, périodicité mensuelle, publication le 1er jour
ouvré du mois). Le fichier à télécharger est l'archive ZIP unique
"OGD.zip" (ressource au format ZIP listée sur la page du jeu de
données) — pas de flux XML séparé à assembler soi-même :

    curl -o OGD.zip https://ogd.swissmedic.cloud/ogd-arzneimittel/Daten/OGD.zip

Cette archive contient (structure confirmée en inspectant un export réel,
pas supposée) :
    - OGD-Praeparate.XML     : une ligne par numéro d'autorisation
                                (ZULASSUNGSNUMMER), avec ATC, forme
                                galénique (code), titulaire, usage
                                (HAM = humain, TAM = vétérinaire).
    - OGD-Sequenzen.XML      : les déclinaisons (séquences) d'un numéro
                                d'autorisation — c'est l'unité importée
                                comme un Medicament, car c'est à ce
                                niveau que la composition est rattachée.
    - OGD-Deklarationen.XML  : composition, par séquence, référençant
                                chaque substance par un STOFF_ID opaque.
    - OGD-Stoff-Synonyme.XML : résout STOFF_ID vers un nom de substance —
                                en LATIN (nomenclature pharmacopée), pas
                                en français.
    - OGD-Adressen.XML       : résout le titulaire d'autorisation
                                (ZULASSUNGSINHABERIN) vers une raison
                                sociale.

Usage :
    python manage.py import_swissmedic --fichier-zip ./OGD.zip

Périmètre volontairement restreint (pas une approximation silencieuse) :
    - Seul l'usage humain est importé (VERWENDUNG == "HAM") : les
      médicaments vétérinaires (TAM), également présents dans ce jeu de
      données, sont ignorés.
    - Seules les séquences au statut "Z" (Zugelassen = autorisé) sont
      importées : les autorisations révoquées ne sont pas proposées à la
      prescription.
    - `forme_pharmaceutique` reçoit le code brut Swissmedic (ex. "TROF"),
      pas un libellé — la table de correspondance code → libellé
      (OGD-User-Defined-Codes.XML) n'est pas exploitée dans cette
      version.

Limitation assumée et non contournable automatiquement — sujet santé,
« précision exigée, aucune approximation » : les noms de substances de
ce jeu de données sont en latin (nomenclature de la Pharmacopée, ex.
"atorvastatinum"), alors que apps.interactions rapproche les
prescriptions du Thésaurus ANSM par nom de substance EXACT en français
(ex. "ATORVASTATINE"). Un rapprochement heuristique (ex. retirer le
suffixe latin "-um") donnerait un résultat correct pour certains noms
(ex. "valsartanum" → "VALSARTAN") mais un résultat FAUX pour beaucoup
d'autres (ex. "atorvastatinum" → "ATORVASTATIN", qui ne correspond pas à
"ATORVASTATINE" en base) — un taux d'erreur silencieux inacceptable pour
une vérification d'interactions. Cette commande ne tente donc AUCUN
rapprochement automatique : chaque substance suisse est créée comme une
SubstanceActive distincte (nom latin), et tout médicament importé par
cette commande a `verification_interactions_fiable=False` de façon
inconditionnelle. apps.interactions doit avertir l'utilisateur en
conséquence plutôt que d'afficher silencieusement « aucune interaction
détectée ». Une table de correspondance latin → français validée
manuellement pourrait lever cette limitation dans une version
ultérieure — ce n'est pas fait ici pour ne pas deviner.
"""

import xml.etree.ElementTree as ET
import zipfile

from django.core.management.base import BaseCommand, CommandError

from apps.medicaments.models import Medicament, SubstanceActive

VERWENDUNG_HUMAIN = "HAM"
STATUT_AUTORISE = "Z"
CATEGORIE_SUBSTANCE_ACTIVE = "WIRKS"


class Command(BaseCommand):
    help = "Importe ou met à jour le référentiel des médicaments humains depuis l'archive OGD de Swissmedic."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fichier-zip",
            required=True,
            help="Chemin vers l'archive OGD.zip téléchargée depuis opendata.swiss.",
        )

    def handle(self, *args, **options):
        chemin_zip = options["fichier_zip"]
        try:
            archive = zipfile.ZipFile(chemin_zip)
        except OSError as exc:
            raise CommandError(f"Impossible de lire {chemin_zip} : {exc}")
        except zipfile.BadZipFile as exc:
            raise CommandError(f"{chemin_zip} n'est pas une archive ZIP valide : {exc}")

        noms_fichiers = archive.namelist()

        def trouver(suffixe):
            for nom in noms_fichiers:
                if nom.endswith(suffixe):
                    return nom
            raise CommandError(
                f"Fichier '{suffixe}' introuvable dans {chemin_zip} — archive OGD inattendue."
            )

        self.stdout.write("Lecture des titulaires d'autorisation...")
        adresses = self._lire_adresses(archive, trouver("OGD-Adressen.XML"))

        self.stdout.write("Lecture des noms de substances (latin)...")
        noms_substances = self._lire_synonymes(archive, trouver("OGD-Stoff-Synonyme.XML"))

        self.stdout.write("Lecture de la composition...")
        composition = self._lire_declarations(
            archive, trouver("OGD-Deklarationen.XML"), noms_substances
        )

        self.stdout.write("Lecture des préparations (usage humain)...")
        preparations = self._lire_preparations(archive, trouver("OGD-Praeparate.XML"), adresses)

        self.stdout.write("Import des séquences...")
        crees, mis_a_jour, ignorees = self._importer_sequences(
            archive, trouver("OGD-Sequenzen.XML"), preparations, composition
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {crees} créé(s), {mis_a_jour} mis à jour, "
                f"{ignorees} ignoré(e)s (usage vétérinaire, statut révoqué, ou "
                "numéro d'autorisation inconnu)."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Tous les médicaments importés ont verification_interactions_fiable=False : "
                "aucun rapprochement automatique n'est tenté entre les noms de substances "
                "latins (Swissmedic) et français (BDPM/Thésaurus ANSM). Voir la docstring de "
                "cette commande pour le détail."
            )
        )

    def _iterer(self, archive, nom_fichier, balise):
        with archive.open(nom_fichier) as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag == balise:
                    yield {enfant.tag: (enfant.text or "").strip() for enfant in elem}
                    elem.clear()

    def _lire_adresses(self, archive, nom_fichier):
        """{PARTNER_NR: raison_sociale}"""
        return {
            e["PARTNER_NR"]: e.get("FIRMENNAME", "")
            for e in self._iterer(archive, nom_fichier, "ADRESSEN")
            if e.get("PARTNER_NR")
        }

    def _lire_synonymes(self, archive, nom_fichier):
        """
        {STOFF_ID: nom_latin}. Un STOFF_ID peut avoir plusieurs synonymes
        (LAUFENDE_NR) — on garde le premier rencontré, sans en privilégier
        un arbitrairement au-delà de l'ordre du fichier.
        """
        noms = {}
        for e in self._iterer(archive, nom_fichier, "SYNONYME"):
            stoff_id = e.get("STOFF_ID")
            if stoff_id and stoff_id not in noms and e.get("STOFFSYNONYM"):
                noms[stoff_id] = e["STOFFSYNONYM"]
        return noms

    def _lire_declarations(self, archive, nom_fichier, noms_substances):
        """
        {(ZULASSUNGSNUMMER, SEQUENZNUMMER): [(nom_substance, menge, unite), ...]}

        Ne garde que les composants de catégorie WIRKS (substance active,
        équivalent du filtre "SA" de import_bdpm) et seulement ceux dont
        le STOFF_ID est résolu vers un nom (sinon substance non
        identifiable — exclue plutôt que devinée).
        """
        composition = {}
        for e in self._iterer(archive, nom_fichier, "DEKLARATION"):
            if e.get("STOFFKATEGORIE") != CATEGORIE_SUBSTANCE_ACTIVE:
                continue
            nom = noms_substances.get(e.get("STOFF_ID"))
            if not nom:
                continue
            cle = (e.get("ZULASSUNGSNUMMER"), e.get("SEQUENZNUMMER"))
            composition.setdefault(cle, []).append(
                (nom, e.get("MENGE", ""), e.get("MENGEN_EINHEIT", ""))
            )
        return composition

    def _lire_preparations(self, archive, nom_fichier, adresses):
        """{ZULASSUNGSNUMMER: {denomination, arzneiform, atc_code, laboratoire}} — humain uniquement."""
        preparations = {}
        for e in self._iterer(archive, nom_fichier, "PRAEPARAT"):
            if e.get("VERWENDUNG") != VERWENDUNG_HUMAIN:
                continue
            preparations[e.get("ZULASSUNGSNUMMER")] = {
                "denomination": e.get("PRAEPARATENAME", ""),
                "arzneiform": e.get("ARZNEIFORM", ""),
                "atc_code": e.get("ATC_CODE", ""),
                "laboratoire": adresses.get(e.get("ZULASSUNGSINHABERIN"), ""),
            }
        return preparations

    def _importer_sequences(self, archive, nom_fichier, preparations, composition):
        crees, mis_a_jour, ignorees = 0, 0, 0
        for e in self._iterer(archive, nom_fichier, "SEQUENZ"):
            zulassungsnummer = e.get("ZULASSUNGSNUMMER")
            sequenznummer = e.get("SEQUENZNUMMER")
            preparation = preparations.get(zulassungsnummer)
            if preparation is None or e.get("ZULASSUNGSSTATUS") != STATUT_AUTORISE:
                ignorees += 1
                continue

            composants = composition.get((zulassungsnummer, sequenznummer), [])
            dosage = " + ".join(
                f"{nom} {menge}{unite}".strip() for nom, menge, unite in composants
            )

            medicament, cree = Medicament.objects.update_or_create(
                code_cis=f"CH-{zulassungsnummer}-{sequenznummer}",
                defaults={
                    "denomination": (e.get("SEQUENZNAME") or preparation["denomination"])[:255],
                    "forme_pharmaceutique": preparation["arzneiform"][:255],
                    "laboratoire": preparation["laboratoire"][:255],
                    "code_atc": preparation["atc_code"][:10],
                    "dosage": dosage[:500],
                    "source": Medicament.Source.SWISSMEDIC,
                    "verification_interactions_fiable": False,
                },
            )
            if composants:
                objets_substances = [
                    SubstanceActive.objects.get_or_create(nom=nom.upper())[0]
                    for nom, _menge, _unite in composants
                ]
                medicament.substances_actives.set(objets_substances)

            crees += int(cree)
            mis_a_jour += int(not cree)

        return crees, mis_a_jour, ignorees
