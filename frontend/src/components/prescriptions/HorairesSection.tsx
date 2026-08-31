import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import type { HoraireProgramme } from "../../types";

export function HorairesSection({
  prescriptionId,
  horaires,
  peutModifier,
  onHoraireAjoute,
  onHoraireModifie,
}: {
  prescriptionId: string;
  horaires: HoraireProgramme[];
  peutModifier: boolean;
  onHoraireAjoute: (horaire: HoraireProgramme) => void;
  onHoraireModifie: (horaire: HoraireProgramme) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [heure, setHeure] = useState("08:00");
  const [quantite, setQuantite] = useState("1");
  const [enCours, setEnCours] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setEnCours(true);
    try {
      const { data } = await api.post<HoraireProgramme>("/horaires-programmes/", {
        prescription: prescriptionId,
        heure,
        quantite,
        actif: true,
      });
      onHoraireAjoute(data);
      setOuvert(false);
      toast.success("Horaire ajouté");
    } catch {
      toast.error("Impossible d'ajouter cet horaire");
    } finally {
      setEnCours(false);
    }
  }

  async function basculerActif(horaire: HoraireProgramme) {
    try {
      const { data } = await api.patch<HoraireProgramme>(`/horaires-programmes/${horaire.id}/`, {
        actif: !horaire.actif,
      });
      onHoraireModifie(data);
    } catch {
      toast.error("Impossible de modifier cet horaire");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Horaires
        </h4>
        {peutModifier && !ouvert && (
          <button
            onClick={() => setOuvert(true)}
            className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
          >
            <Plus size={14} /> Ajouter
          </button>
        )}
      </div>

      {ouvert && (
        <form onSubmit={handleSubmit} className="flex items-end gap-2 mb-2">
          <div>
            <label className="block text-xs mb-1">Heure</label>
            <input
              required
              type="time"
              value={heure}
              onChange={(e) => setHeure(e.target.value)}
              className={`${champClasse} py-1.5`}
            />
          </div>
          <div>
            <label className="block text-xs mb-1">Quantité</label>
            <input
              required
              type="number"
              step="0.01"
              min="0"
              value={quantite}
              onChange={(e) => setQuantite(e.target.value)}
              className={`${champClasse} py-1.5 w-24`}
            />
          </div>
          <button
            type="submit"
            disabled={enCours}
            className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-brand-500)] text-white hover:bg-[var(--color-brand-600)] disabled:opacity-60"
          >
            Ajouter
          </button>
          <button
            type="button"
            onClick={() => setOuvert(false)}
            className="text-xs px-2 py-1.5 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]"
          >
            Annuler
          </button>
        </form>
      )}

      {horaires.length === 0 ? (
        <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Aucun horaire défini.
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {horaires.map((h) => (
            <button
              key={h.id}
              onClick={() => peutModifier && basculerActif(h)}
              disabled={!peutModifier}
              title={peutModifier ? "Cliquer pour activer/désactiver" : undefined}
              className={`text-xs px-2.5 py-1 rounded-full border ${
                h.actif
                  ? "border-[var(--color-brand-500)] text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)]"
                  : "border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] line-through"
              }`}
            >
              {h.heure.slice(0, 5)} · {h.quantite}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
