import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { AlertTriangle, Plus } from "lucide-react";
import { api, recupererToutesPages } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import { StatusBadge } from "../StatusBadge";
import type { Prise } from "../../types";

const STATUTS: Record<Prise["statut"], { label: string; ton: "danger" | "warning" | "success" | "muted" }> = {
  attendue: { label: "Attendue", ton: "warning" },
  prise: { label: "Prise", ton: "success" },
  oubliee: { label: "Oubliée", ton: "danger" },
  reportee: { label: "Reportée", ton: "muted" },
};

/**
 * Pas de filtre serveur par prescription (aucun filter_backend configuré
 * sur PriseViewSet) — on récupère toutes les prises accessibles à
 * l'utilisateur puis on filtre côté client, comme pour SuivisMedecin.
 */
export function PrisesSection({
  prescriptionId,
  typePrise,
  doseQuantiteDefaut,
  peutModifier,
}: {
  prescriptionId: string;
  typePrise: "reguliere" | "reserve";
  doseQuantiteDefaut: string;
  peutModifier: boolean;
}) {
  const [prises, setPrises] = useState<Prise[] | null>(null);
  const [ouvert, setOuvert] = useState(false);
  const [quantitePrise, setQuantitePrise] = useState(doseQuantiteDefaut);
  const [commentaire, setCommentaire] = useState("");
  const [enCours, setEnCours] = useState(false);

  async function charger() {
    const toutes = await recupererToutesPages<Prise>("/prises/");
    setPrises(toutes.filter((p) => p.prescription === prescriptionId));
  }

  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prescriptionId]);

  function remplacer(prise: Prise) {
    setPrises((liste) => (liste ? liste.map((p) => (p.id === prise.id ? prise : p)) : [prise]));
  }

  async function enregistrerPriseLibre(e: FormEvent) {
    e.preventDefault();
    setEnCours(true);
    try {
      const { data } = await api.post<Prise>("/prises/", {
        prescription: prescriptionId,
        statut: "prise",
        date_heure_reelle: new Date().toISOString(),
        quantite_prise: quantitePrise,
        commentaire,
      });
      setPrises((liste) => (liste ? [data, ...liste] : [data]));
      setOuvert(false);
      setCommentaire("");
      toast.success(
        data.alerte_depassement ? "Prise enregistrée — plafond journalier dépassé" : "Prise enregistrée"
      );
    } catch {
      toast.error("Impossible d'enregistrer cette prise");
    } finally {
      setEnCours(false);
    }
  }

  async function changerStatut(prise: Prise, statut: Prise["statut"]) {
    try {
      const payload: Record<string, unknown> = { statut };
      if (statut === "prise") {
        payload.date_heure_reelle = new Date().toISOString();
        payload.quantite_prise = prise.quantite_prevue;
      }
      const { data } = await api.patch<Prise>(`/prises/${prise.id}/`, payload);
      remplacer(data);
    } catch {
      toast.error("Impossible de mettre à jour cette prise");
    }
  }

  async function supprimer(prise: Prise) {
    try {
      await api.delete(`/prises/${prise.id}/`);
      setPrises((liste) => (liste ? liste.filter((p) => p.id !== prise.id) : liste));
    } catch {
      toast.error("Impossible de supprimer cette prise");
    }
  }

  if (prises === null) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Prises
        </h4>
        {peutModifier && typePrise === "reserve" && !ouvert && (
          <button
            onClick={() => setOuvert(true)}
            className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
          >
            <Plus size={14} /> Enregistrer une prise
          </button>
        )}
      </div>

      {ouvert && (
        <form onSubmit={enregistrerPriseLibre} className="flex items-end gap-2 mb-2 flex-wrap">
          <div>
            <label className="block text-xs mb-1">Quantité prise</label>
            <input
              required
              type="number"
              step="0.01"
              min="0"
              value={quantitePrise}
              onChange={(e) => setQuantitePrise(e.target.value)}
              className={`${champClasse} py-1.5 w-24`}
            />
          </div>
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs mb-1">Commentaire</label>
            <input
              value={commentaire}
              onChange={(e) => setCommentaire(e.target.value)}
              className={`${champClasse} py-1.5`}
            />
          </div>
          <button
            type="submit"
            disabled={enCours}
            className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-brand-500)] text-white hover:bg-[var(--color-brand-600)] disabled:opacity-60"
          >
            Enregistrer
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

      {prises.length === 0 ? (
        <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Aucune prise enregistrée.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {prises.slice(0, 10).map((p) => {
            const moment = p.date_heure_reelle || p.date_heure_prevue;
            return (
              <li
                key={p.id}
                className="flex items-center justify-between gap-2 text-xs bg-[var(--color-bg-light)] dark:bg-[var(--color-bg-dark)] rounded-lg px-2.5 py-1.5"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <StatusBadge ton={STATUTS[p.statut].ton}>{STATUTS[p.statut].label}</StatusBadge>
                  <span className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] truncate">
                    {moment ? new Date(moment).toLocaleString("fr-FR") : "—"}
                    {p.quantite_prise ? ` · ${p.quantite_prise}` : ""}
                  </span>
                  {p.alerte_depassement && (
                    <span title="Plafond journalier dépassé" className="text-[var(--color-danger)] shrink-0">
                      <AlertTriangle size={13} />
                    </span>
                  )}
                </div>
                {peutModifier && (
                  <div className="flex items-center gap-2 shrink-0">
                    {p.statut === "attendue" && (
                      <>
                        <button
                          onClick={() => changerStatut(p, "prise")}
                          className="text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
                        >
                          Marquer prise
                        </button>
                        <button
                          onClick={() => changerStatut(p, "oubliee")}
                          className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:underline"
                        >
                          Oubliée
                        </button>
                      </>
                    )}
                    <button onClick={() => supprimer(p)} className="text-[var(--color-danger)] hover:underline">
                      Suppr.
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
