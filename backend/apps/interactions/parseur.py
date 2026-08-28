"""
Parseur du Thésaurus des interactions médicamenteuses de l'ANSM, converti
en texte brut via `pdftotext -layout` (voir commande import_thesaurus).

Principe directeur : en cas d'ambiguïté sur le niveau de gravité d'une
entrée (codes composés comme "CI - ASDEC - APEC", ou plusieurs niveaux
distincts détectés dans le même bloc), l'entrée n'est PAS importée
automatiquement — elle est journalisée à part pour revue manuelle. On ne
devine jamais un niveau de gravité.

Structure réelle observée dans le document officiel (confirmée sur un
extrait authentique récupéré du PDF, pas supposée) :

    NOM_DU_PROTAGONISTE_A
    Voir aussi : ...                     (optionnel, ignoré)
    + NOM_DU_PROTAGONISTE_B
    [texte explicatif]                   (une ou plusieurs lignes)
    [NIVEAU]                             (peut être sur la même ligne que
                                           le texte, ou seul sur sa ligne)
    [texte de conduite à tenir]          (optionnel)

Un protagoniste A est une ligne en MAJUSCULES qui n'est ni une ligne
"+ ...", ni une ligne "Voir aussi", ni une ligne purement entre
parenthèses (liste des membres d'une classe, ignorée dans cette version).
"""

import re
from dataclasses import dataclass, field

NIVEAUX_SIMPLES = {
    "CONTRE-INDICATION": "contre_indication",
    "CONTRE INDICATION": "contre_indication",
    "ASSOCIATION DECONSEILLEE": "association_deconseillee",
    "ASSOCIATION DÉCONSEILLÉE": "association_deconseillee",
    "PRÉCAUTION D'EMPLOI": "precaution_emploi",
    "PRECAUTION D'EMPLOI": "precaution_emploi",
    "A PRENDRE EN COMPTE": "a_prendre_en_compte",
    "À PRENDRE EN COMPTE": "a_prendre_en_compte",
}

# Codes composés indiquant un niveau conditionnel (dose/contexte) — toute
# entrée dont le bloc contient un de ces codes est exclue de l'import
# automatique, quel que soit le niveau détecté par ailleurs.
MOTIF_CODE_COMPOSE = re.compile(r"\b(CI|ASDEC|APEC|PE)\s*-\s*(CI|ASDEC|APEC|PE)")

MOTIF_LIGNE_PROTAGONISTE_B = re.compile(r"^\+\s*(.+)$")
MOTIF_VOIR_AUSSI = re.compile(r"^Voir aussi\s*:", re.IGNORECASE)
MOTIF_LIGNE_PARENTHESES = re.compile(r"^\(.+\)$")
MOTIF_NUMERO_PAGE = re.compile(r"^\d+$")


@dataclass
class EntreeParsee:
    protagoniste_a: str
    protagoniste_b: str
    niveau: str | None
    texte_brut: str
    ambigue: bool = False
    raison_exclusion: str = ""


def _est_ligne_protagoniste_a(ligne: str) -> bool:
    """
    Une ligne protagoniste A est en MAJUSCULES (lettres accentuées
    incluses), ne commence pas par '+', n'est pas 'Voir aussi', n'est pas
    une liste entre parenthèses, et n'est pas un simple numéro de page.

    Exclut aussi explicitement les lignes qui sont elles-mêmes des
    marqueurs de niveau de gravité (ex. "CONTRE-INDICATION" seul sur sa
    ligne, ou un code composé "CI - ASDEC - APEC") : ces lignes sont en
    MAJUSCULES comme un vrai protagoniste A, et les confondre ferait
    disparaître silencieusement l'entrée en cours — bug réel détecté et
    corrigé lors des tests contre un extrait authentique du PDF.
    """
    ligne = ligne.strip()
    if not ligne:
        return False
    if ligne.startswith("+"):
        return False
    if MOTIF_VOIR_AUSSI.match(ligne):
        return False
    if MOTIF_LIGNE_PARENTHESES.match(ligne):
        return False
    if MOTIF_NUMERO_PAGE.match(ligne):
        return False
    if MOTIF_CODE_COMPOSE.search(ligne):
        return False
    if ligne.upper() in NIVEAUX_SIMPLES:
        return False
    # Doit être essentiellement en majuscules (autorise chiffres, espaces,
    # ponctuation courante) pour écarter les lignes de texte explicatif.
    lettres = [c for c in ligne if c.isalpha()]
    if not lettres:
        return False
    return all(c.isupper() for c in lettres)


def _detecter_niveau(bloc_texte: str) -> tuple[str | None, bool, str]:
    """Retourne (niveau_ou_None, ambigue, raison) pour un bloc de texte d'entrée."""
    if MOTIF_CODE_COMPOSE.search(bloc_texte):
        return None, True, "Code composé détecté (niveau conditionnel selon dose/contexte)."

    niveaux_trouves = {
        niveau
        for cle, niveau in NIVEAUX_SIMPLES.items()
        if cle in bloc_texte.upper()
    }
    if len(niveaux_trouves) == 0:
        return None, True, "Aucun niveau de gravité reconnu dans le bloc."
    if len(niveaux_trouves) > 1:
        return None, True, f"Plusieurs niveaux distincts détectés : {niveaux_trouves}."

    return niveaux_trouves.pop(), False, ""


def parser_thesaurus(texte: str) -> list[EntreeParsee]:
    """Parse le texte intégral (déjà extrait du PDF) et retourne toutes les entrées détectées."""
    lignes = [l.rstrip() for l in texte.split("\n")]

    entrees: list[EntreeParsee] = []
    protagoniste_a_courant: str | None = None
    protagoniste_b_courant: str | None = None
    bloc_lignes: list[str] = []

    def cloturer_entree_en_cours():
        if protagoniste_a_courant and protagoniste_b_courant and bloc_lignes:
            bloc_texte = "\n".join(bloc_lignes).strip()
            niveau, ambigue, raison = _detecter_niveau(bloc_texte)
            entrees.append(
                EntreeParsee(
                    protagoniste_a=protagoniste_a_courant,
                    protagoniste_b=protagoniste_b_courant,
                    niveau=niveau,
                    texte_brut=bloc_texte,
                    ambigue=ambigue,
                    raison_exclusion=raison,
                )
            )

    for ligne in lignes:
        ligne_nettoyee = ligne.strip()
        if not ligne_nettoyee:
            continue

        if _est_ligne_protagoniste_a(ligne_nettoyee):
            cloturer_entree_en_cours()
            protagoniste_a_courant = ligne_nettoyee
            protagoniste_b_courant = None
            bloc_lignes = []
            continue

        if MOTIF_VOIR_AUSSI.match(ligne_nettoyee) or MOTIF_LIGNE_PARENTHESES.match(ligne_nettoyee):
            continue  # ignorées dans cette version (voir docstring)

        correspondance_b = MOTIF_LIGNE_PROTAGONISTE_B.match(ligne_nettoyee)
        if correspondance_b:
            cloturer_entree_en_cours()
            protagoniste_b_courant = correspondance_b.group(1).strip()
            bloc_lignes = []
            continue

        if protagoniste_a_courant and protagoniste_b_courant:
            bloc_lignes.append(ligne_nettoyee)

    cloturer_entree_en_cours()
    return entrees
