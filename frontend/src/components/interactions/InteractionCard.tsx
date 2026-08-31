import { StatusBadge } from "../StatusBadge";
import { NIVEAUX } from "../../lib/interactions";
import type { InteractionDetectee } from "../../types";

export function InteractionCard({ interaction }: { interaction: InteractionDetectee }) {
  const niveau = NIVEAUX[interaction.niveau];

  return (
    <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl p-4">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
        <div className="font-medium">
          {interaction.medicament_a}
          <span className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] font-normal mx-1.5">
            +
          </span>
          {interaction.medicament_b}
        </div>
        <StatusBadge ton={niveau.ton}>{niveau.label}</StatusBadge>
      </div>
      <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mb-2">
        {interaction.substance_a} + {interaction.substance_b}
      </p>
      <p className="text-sm whitespace-pre-wrap">{interaction.libelle}</p>
    </div>
  );
}
