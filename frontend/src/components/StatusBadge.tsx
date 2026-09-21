/**
 * Élément signature de l'interface : un point de statut (6px) + libellé,
 * réutilisé partout où un statut clinique doit être visible d'un coup d'œil
 * (niveau d'interaction, alerte de stock, statut de prise). Conforme à la
 * charte graphique Medicgest : le statut n'est jamais porté par un fond de
 * pastille coloré, seulement par le point + le texte qui l'accompagne
 * toujours (voir design_handoff_medicgest_branding/README.md, "Couleurs de
 * statut").
 */
type Ton = "danger" | "warning" | "success" | "muted";

const POINTS: Record<Ton, string> = {
  danger: "bg-[var(--statut-rupture)]",
  warning: "bg-[var(--statut-attention)]",
  success: "bg-[var(--statut-conforme)]",
  muted: "bg-[var(--muted)]",
};

export function StatusBadge({ ton, children }: { ton: Ton; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--ink)]">
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${POINTS[ton]}`} />
      {children}
    </span>
  );
}
