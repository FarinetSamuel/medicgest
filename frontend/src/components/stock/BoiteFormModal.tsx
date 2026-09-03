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

export function BoiteFormModal({
  patientId,
  boite,
  onFermer,
  onSauvegarde,
}: {
  patientId: string;
  /** null = création */
  boite: Boite | null;
  onFermer: () => void;
  onSauvegarde: (boite: Boite) => void;
}) {
  const modeCreation = boite === null;
  const [medicament, setMedicament] = useState<Medicament | null>(null);
  const [champs, setChamps] = useState<ChampsFormulaire>(
    boite
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

  function champ(nom: keyof ChampsFormulaire) {
    return {
      value: champs[nom],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => setChamps((c) => ({ ...c, [nom]: e.target.value })),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreurs({});
    if (modeCreation && !medicament) {
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
        payload.medicament = medicament!.id;
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
    <Modal titre={modeCreation ? "Nouvelle boîte" : "Modifier la boîte"} onFermer={onFermer}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {modeCreation ? (
          <div>
            <label className="block text-sm font-medium mb-1.5">Médicament</label>
            <MedicamentSelect valeur={medicament} onChoisir={setMedicament} />
            {erreurs.medicament && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.medicament}</p>}
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium mb-1.5">Médicament</label>
            <p className={`${champClasse} text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]`}>
              {boite!.medicament_nom}
            </p>
          </div>
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
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Date de péremption</label>
            <input type="date" {...champ("date_peremption")} className={champClasse} />
          </div>
        </div>

        <fieldset className="border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-lg p-3 space-y-3">
          <legend className="text-xs font-medium px-1 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
            Seuils d'alerte (facultatifs)
          </legend>
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
                <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
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
            className="text-sm px-4 py-2 rounded-lg text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={enCours}
            className="text-sm px-4 py-2 rounded-lg bg-[var(--color-brand-500)] text-white hover:bg-[var(--color-brand-600)] disabled:opacity-60"
          >
            {enCours ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
