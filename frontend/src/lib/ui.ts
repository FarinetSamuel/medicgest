/**
 * Classes Tailwind partagées pour les champs de formulaire, extraites de
 * Connexion.tsx pour rester cohérent visuellement sans dupliquer la chaîne
 * dans chaque nouveau formulaire (Patients, puis Prescriptions/Stock...).
 */
export const champClasse =
  "w-full rounded-[var(--radius-control)] border border-[var(--hairline)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

/**
 * Échelle typographique de la charte graphique Medicgest
 * (design_handoff_medicgest_branding/README.md, section "Typographie") —
 * tailles/graisses/tracking définitifs, à utiliser pour les titres plutôt
 * que de réinventer une taille au cas par cas.
 */
export const titrePageClasse =
  "font-[var(--font-plex-sans)] text-[46px] font-light tracking-[-0.03em] leading-[1.1] text-[var(--ink)]";
export const titreSectionClasse =
  "font-[var(--font-plex-sans)] text-[26px] font-light tracking-[-0.02em] text-[var(--ink)]";
export const titreCarteClasse = "font-[var(--font-plex-sans)] text-[17px] font-medium text-[var(--ink)]";
export const eyebrowClasse =
  "font-[var(--font-plex-mono)] text-[11px] tracking-[.16em] uppercase text-[var(--muted)]";

/**
 * Boutons de référence (README, "Composants de référence"). --cta/--cta-ink
 * portent déjà l'asymétrie clair/sombre du bouton primaire (fond --ink en
 * clair, --accent en sombre) — voir index.css.
 */
export const boutonPrimaireClasse =
  "inline-flex items-center justify-center gap-2 text-[13px] font-medium rounded-[var(--radius-control)] bg-[var(--cta)] text-[var(--cta-ink)] px-[18px] py-[10px] hover:brightness-95 transition-[filter] disabled:opacity-60";
export const boutonSecondaireClasse =
  "inline-flex items-center justify-center gap-2 text-[13px] font-medium rounded-[var(--radius-control)] border border-[var(--border-strong)] text-[var(--ink)] px-[18px] py-[10px] hover:bg-[var(--hairline-soft)] dark:hover:bg-[var(--hairline)] transition-colors disabled:opacity-60";
