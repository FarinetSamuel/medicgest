/**
 * Élément signature de l'interface : un badge à pastille colorée, réutilisé
 * partout où un statut clinique doit être visible d'un coup d'œil (niveau
 * d'interaction, alerte de stock, statut de prise) — cohérence visuelle
 * plutôt qu'un badge générique différent par section.
 */
type Ton = "danger" | "warning" | "success" | "muted";

const TONS: Record<Ton, string> = {
  danger: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  success: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  muted: "bg-black/5 dark:bg-white/10 text-current",
};

const POINTS: Record<Ton, string> = {
  danger: "bg-[var(--color-danger)]",
  warning: "bg-[var(--color-warning)]",
  success: "bg-[var(--color-success)]",
  muted: "bg-current opacity-50",
};

export function StatusBadge({ ton, children }: { ton: Ton; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${TONS[ton]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${POINTS[ton]}`} />
      {children}
    </span>
  );
}
