/**
 * Logo Medicgest — croix pharmaceutique dans une tuile à coins arrondis.
 * Géométrie et couleurs d'après design_handoff_medicgest_branding/README.md
 * (section "Logotype — construction exacte"), paramétrées par la taille de
 * tuile `size` (référence S=76). Couleurs lues via les tokens --surface-2/
 * --accent/--ink (voir index.css) : un seul composant, pas un fichier par
 * thème — il suit .dark comme le reste de l'app.
 */

type LogoVariant = "symbole" | "app" | "mono";

function LogoSymbol({
  size = 76,
  variant = "symbole",
  decorative = true,
  className,
}: {
  size?: number;
  variant?: LogoVariant;
  decorative?: boolean;
  className?: string;
}) {
  const rx = size * 0.234;
  const vW = size * 0.158;
  const vH = size * 0.526;
  const hW = size * 0.526;
  const hH = size * 0.158;
  const vX = (size - vW) / 2;
  const vY = (size - vH) / 2;
  const hX = (size - hW) / 2;
  const hY = (size - hH) / 2;

  const estMono = variant === "mono";
  const estApp = variant === "app";
  const strokeWidth = 1.5;

  const tileFill = estApp ? "#17707F" : estMono ? "none" : "var(--surface-2)";
  const verticalFill = estMono ? "var(--ink)" : "#FFFFFF";
  const horizontalFill = estApp ? "rgba(255,255,255,.45)" : estMono ? "var(--ink)" : "var(--accent)";

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role={decorative ? undefined : "img"}
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : "Medicgest"}
    >
      <rect
        x={estMono ? strokeWidth / 2 : 0}
        y={estMono ? strokeWidth / 2 : 0}
        width={estMono ? size - strokeWidth : size}
        height={estMono ? size - strokeWidth : size}
        rx={rx}
        fill={tileFill}
        stroke={estMono ? "var(--ink)" : "none"}
        strokeWidth={estMono ? strokeWidth : 0}
      />
      {/* barre horizontale (accent) au-dessus de la verticale (blanc) */}
      <rect x={vX} y={vY} width={vW} height={vH} rx={vW / 2} fill={verticalFill} />
      <rect x={hX} y={hY} width={hW} height={hH} rx={hH / 2} fill={horizontalFill} />
    </svg>
  );
}

export function Logo({
  size = 76,
  variant = "symbole",
  wordmark = "full",
  className,
}: {
  size?: number;
  variant?: LogoVariant;
  /**
   * "full" : lockup de référence (medic/gest 34px + eyebrow mono, gap
   * 0.26×size) — contextes de marque (écran de connexion, à propos...).
   * "compact" : recette "App bar" du README (medicgest 15px, gap fixe
   * 10px, sans eyebrow) — barre de navigation.
   * false : symbole seul.
   */
  wordmark?: "full" | "compact" | false;
  className?: string;
}) {
  if (!wordmark) {
    return <LogoSymbol size={size} variant={variant} decorative={false} className={className} />;
  }

  return (
    <span
      className={`inline-flex items-center ${className ?? ""}`}
      style={{ gap: wordmark === "full" ? size * 0.26 : 10 }}
    >
      <LogoSymbol size={size} variant={variant} />
      {wordmark === "full" ? (
        <span className="flex flex-col" style={{ gap: 6 }}>
          <span
            style={{
              fontFamily: "var(--font-plex-sans)",
              fontWeight: 600,
              fontSize: 34,
              letterSpacing: "-0.035em",
              lineHeight: 1,
              color: "var(--ink)",
            }}
          >
            medic
            <span style={{ fontWeight: 300, color: "var(--muted)" }}>gest</span>
          </span>
          <span
            style={{
              fontFamily: "var(--font-plex-mono)",
              fontSize: 9.5,
              letterSpacing: ".3em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            Gestion pharmaceutique
          </span>
        </span>
      ) : (
        <span
          style={{
            fontFamily: "var(--font-plex-sans)",
            fontWeight: 600,
            fontSize: 15,
            letterSpacing: "-0.035em",
            lineHeight: 1,
            color: "var(--ink)",
          }}
        >
          medic
          <span style={{ fontWeight: 300, color: "var(--muted)" }}>gest</span>
        </span>
      )}
    </span>
  );
}
