import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Modal } from "../Modal";
import { champClasse } from "../../lib/ui";
import { api } from "../../lib/api";
import { MedicamentSelect } from "../prescriptions/MedicamentSelect";
import type { Boite, Medicament } from "../../types";

interface ChampsFormulaire {
  quantite_initiale: string;
  quantite_restante: string;
  date_ouverture: string;
  date_peremption: string;
  delai_reappro_jours: string;
  seuil_alerte_quantite: string;
  seuil_alerte_jours: string;
}

const VIDE: ChampsFormulaire = {
  quantite_initiale: "",
  quantite_restante: "",
  date_ouverture: "",
  date_peremption: "",
  delai_reappro_jours: "",
  seuil_alerte_quantite: "",
  seuil_alerte_jours: "",
};

/**
 * Nouvelle boîte pré-remplie d'après une boîte existante du même
 * médicament : quantité initiale, délai de réapprovisionnement et seuils
 * d'alerte. Les seuils ne comptant que sur la dernière boîte à consommer
 * (voir Boite.est_derniere_boite côté backend), une nouvelle boîte sans
 * seuils ferait disparaître l'alerte de ce médicament. Les dates et la
 * quantité restante ne sont jamais recopiées : propres à chaque boîte.
 */
function champsDepuisModele(modele: Boite): ChampsFormulaire {
  return {
    ...VIDE,
    quantite_initiale: modele.quantite_initiale,
    delai_reappro_jours: modele.delai_reappro_jours?.toString() ?? "",
    seuil_alerte_quantite: modele.seuil_alerte_quantite ?? "",
    seuil_alerte_jours: modele.seuil_alerte_jours?.toString() ?? "",
  };
}

function derniereBoiteDuMedicament(boites: Boite[], medicamentId: string): Boite | null {
  const memeMedicament = boites.filter((b) => b.medicament === medicamentId);
  if (memeMedicament.length === 0) return null;
  return memeMedicament.reduce((a, b) => (a.date_creation > b.date_creation ? a : b));
}

export function BoiteFormModal({
  patientId,
  boite,
  modele = null,
  boitesExistantes = [],
  onFermer,
  onSauvegarde,
}: {
  patientId: string;
  /** null = création */
  boite: Boite | null;
  /** Création uniquement : boîte à réapprovisionner (médicament imposé, champs recopiés). */
  modele?: Boite | null;
  /** Création uniquement : boîtes du patient, pour pré-remplir d'après la dernière du médicament choisi. */
  boitesExistantes?: Boite[];
  onFermer: () => void;
  onSauvegarde: (boite: Boite) => void;
}) {
  const modeCreation = boite === null;
  const [medicament, setMedicament] = useState<Medicament | null>(null);
  const [preRempliDepuis, setPreRempliDepuis] = useState<Boite | null>(modele);
  const [champs, setChamps] = useState<ChampsFormulaire>(
    modele
      ? champsDepuisModele(modele)
      : boite
      ? {
          quantite_initiale: boite.quantite_initiale,
          quantite_restante: boite.quantite_restante,
          date_ouverture: boite.date_ouverture ?? "",
          date_peremption: boite.date_peremption ?? "",
          delai_reappro_jours: boite.delai_reappro_jours?.toString() ?? "",
          seuil_alerte_quantite: boite.seuil_alerte_quantite ?? "",
          seuil_alerte_jours: boite.seuil_alerte_jours?.toString() ?? "",
        }
      : VIDE
  );
  const [enCours, setEnCours] = useState(false);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});

  function choisirMedicament(choix: Medicament) {
    setMedicament(choix);
    const derniere = derniereBoiteDuMedicament(boitesExistantes, choix.id);
    setPreRempliDepuis(derniere);
    setChamps(derniere ? champsDepuisModele(derniere) : VIDE);
  }

  function champ(nom: keyof ChampsFormulaire) {
    return {
      value: champs[nom],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => setChamps((c) => ({ ...c, [nom]: e.target.value })),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreurs({});
    if (modeCreation && !modele && !medicament) {
      setErreurs({ medicament: "Choisissez un médicament." });
      return;
    }
    setEnCours(true);
    try {
      const payload: Record<string, unknown> = {
        quantite_initiale: champs.quantite_initiale,
        date_ouverture: champs.date_ouverture || null,
        date_peremption: champs.date_peremption || null,
        delai_reappro_jours: champs.delai_reappro_jours ? Number(champs.delai_reappro_jours) : null,
        seuil_alerte_quantite: champs.seuil_alerte_quantite || null,
        seuil_alerte_jours: champs.seuil_alerte_jours ? Number(champs.seuil_alerte_jours) : null,
      };
      if (modeCreation) {
        payload.patient = patientId;
        payload.medicament = modele ? modele.medicament : medicament!.id;
        if (champs.quantite_restante) payload.quantite_restante = champs.quantite_restante;
        const { data } = await api.post<Boite>("/boites/", payload);
        toast.success("Boîte ajoutée");
        onSauvegarde(data);
      } else {
        payload.quantite_restante = champs.quantite_restante;
        const { data } = await api.patch<Boite>(`/boites/${boite!.id}/`, payload);
        toast.success("Boîte mise à jour");
        onSauvegarde(data);
      }
      onFermer();
    } catch (err) {
      const donnees = (err as { response?: { data?: unknown } })?.response?.data;
      if (donnees && typeof donnees === "object") {
        const messages: Record<string, string> = {};
        for (const [cle, val] of Object.entries(donnees as Record<string, unknown>)) {
          messages[cle] = Array.isArray(val) ? val.join(" ") : String(val);
        }
        setErreurs(messages);
      }
      toast.error("Impossible d'enregistrer la boîte");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <Modal
      titre={modele ? "Réapprovisionner" : modeCreation ? "Nouvelle boîte" : "Modifier la boîte"}
      onFermer={onFermer}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {modeCreation && !modele ? (
          <div>
            <label className="block text-sm font-medium mb-1.5">Médicament</label>
            <MedicamentSelect patientId={patientId} valeur={medicament} onChoisir={choisirMedicament} />
            {erreurs.medicament && <p className="text-xs text-[var(--statut-rupture)] mt-1">{erreurs.medicament}</p>}
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium mb-1.5">Médicament</label>
            <p className={`${champClasse} text-[var(--muted)]`}>
              {(modele ?? boite)!.medicament_nom}
            </p>
          </div>
        )}

        {modeCreation && preRempliDepuis && (
          <p className="text-xs text-[var(--muted)]">
            Quantité, délai et seuils repris de la boîte ajoutée le{" "}
            {new Date(preRempliDepuis.date_creation).toLocaleDateString("fr-FR")} — à vérifier.
          </p>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1.5">Quantité initiale</label>
            <input required type="number" step="1" min="0" {...champ("quantite_initiale")} className={champClasse} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              {modeCreation ? "Quantité restante (si déjà entamée)" : "Quantité restante"}
            </label>
            <input
              required={!modeCreation}
              type="number"
              step="1"
              min="0"
              {...champ("quantite_restante")}
              className={champClasse}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1.5">Date d'ouverture</label>
            <input type="date" {...champ("date_ouverture")} className={champClasse} />
            <p className="text-xs text-[var(--muted)] mt-1">
              Remplie automatiquement à la première prise décomptée.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Date de péremption</label>
            <input type="date" {...champ("date_peremption")} className={champClasse} />
          </div>
        </div>

        <fieldset className="border border-[var(--hairline)] rounded-[var(--radius-control)] p-3 space-y-3">
          <legend className="text-xs font-medium px-1 text-[var(--muted)]">
            Seuils d'alerte (facultatifs)
          </legend>
          <p className="text-xs text-[var(--muted)]">
            Avec plusieurs boîtes du même médicament, seuls les seuils de la dernière boîte à
            consommer sont pris en compte : renseignez-les sur chaque nouvelle boîte.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs mb-1">Quantité minimale ≤</label>
              <input
                type="number"
                step="1"
                min="0"
                {...champ("seuil_alerte_quantite")}
                className={champClasse}
              />
            </div>
            <div>
              <label className="block text-xs mb-1">Jours restants estimés ≤</label>
              <input type="number" min="0" {...champ("seuil_alerte_jours")} className={champClasse} />
              {!modeCreation && boite!.jours_restants_estimes !== null && (
                <p className="text-xs text-[var(--muted)] mt-1">
                  Actuellement estimé à ~{boite!.jours_restants_estimes} j, d'après la consommation récente.
                </p>
              )}
            </div>
          </div>
          <div>
            <label className="block text-xs mb-1">Délai habituel de réapprovisionnement (jours)</label>
            <input type="number" min="0" {...champ("delai_reappro_jours")} className={champClasse} />
          </div>
        </fieldset>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onFermer}
            className="text-sm px-4 py-2 rounded-[var(--radius-control)] text-[var(--muted)] hover:bg-black/5 dark:hover:bg-white/5"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={enCours}
            className="text-sm px-4 py-2 rounded-[var(--radius-control)] bg-[var(--cta)] text-[var(--cta-ink)] hover:brightness-95 disabled:opacity-60"
          >
            {enCours ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
