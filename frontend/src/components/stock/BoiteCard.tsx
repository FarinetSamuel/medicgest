import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, ChevronDown, ChevronUp, Pencil, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { StatusBadge } from "../StatusBadge";
import { MouvementsSection } from "./MouvementsSection";
import type { Boite } from "../../types";

const STATUTS: Record<Boite["statut"], { label: string; ton: "danger" | "warning" | "success" | "muted" }> = {
  active: { label: "Active", ton: "success" },
  epuisee: { label: "Épuisée", ton: "muted" },
  perimee: { label: "Périmée", ton: "danger" },
};

export function BoiteCard({
  boite,
  peutModifier,
  onModifier,
  onSupprimee,
}: {
  boite: Boite;
  peutModifier: boolean;
  onModifier: () => void;
  onSupprimee: (id: string) => void;
}) {
  const [ouvert, setOuvert] = useState(false);

  async function supprimer() {
    try {
      await api.delete(`/boites/${boite.id}/`);
      onSupprimee(boite.id);
      toast.success("Boîte supprimée");
    } catch {
      toast.error("Suppression impossible");
    }
  }

  const pourcentage = Math.max(
    0,
    Math.min(100, (Number(boite.quantite_restante) / Number(boite.quantite_initiale || 1)) * 100)
  );

  return (
    <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl overflow-hidden">
      <button onClick={() => setOuvert((o) => !o)} className="w-full text-left px-4 py-3 flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium truncate">{boite.medicament_nom}</span>
            <StatusBadge ton={STATUTS[boite.statut].ton}>{STATUTS[boite.statut].label}</StatusBadge>
            {boite.en_alerte && (
              <span title="Seuil d'alerte atteint" className="text-[var(--color-danger)]">
                <AlertTriangle size={14} />
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-0.5">
            {boite.quantite_restante} / {boite.quantite_initiale}
            {boite.jours_restants_estimes !== null && ` · ~${boite.jours_restants_estimes} j restants`}
            {boite.date_peremption && ` · péremption ${new Date(boite.date_peremption).toLocaleDateString("fr-FR")}`}
          </p>
          <div className="mt-1.5 h-1.5 w-full max-w-xs rounded-full bg-black/5 dark:bg-white/10 overflow-hidden">
            <div
              className={`h-full rounded-full ${boite.en_alerte ? "bg-[var(--color-danger)]" : "bg-[var(--color-brand-500)]"}`}
              style={{ width: `${pourcentage}%` }}
            />
          </div>
        </div>
        {ouvert ? <ChevronUp size={18} className="shrink-0" /> : <ChevronDown size={18} className="shrink-0" />}
      </button>

      {ouvert && (
        <div className="px-4 pb-4 space-y-4 border-t border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] pt-3">
          <MouvementsSection boiteId={boite.id} />

          {peutModifier && (
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]">
              <button
                onClick={onModifier}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
              >
                <Pencil size={13} /> Modifier
              </button>
              <button
                onClick={supprimer}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-danger)] hover:underline"
              >
                <Trash2 size={13} /> Supprimer
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
