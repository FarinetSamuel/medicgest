import { useEffect, useState } from "react";
import { recupererToutesPages } from "../../lib/api";
import type { MouvementStock } from "../../types";

/**
 * Pas de filtre serveur par boîte (MouvementStockViewSet n'a aucun
 * filter_backend) — on récupère tout ce qui est accessible puis on
 * filtre côté client, comme pour les prises et les suivis médecin.
 */
export function MouvementsSection({ boiteId }: { boiteId: string }) {
  const [mouvements, setMouvements] = useState<MouvementStock[] | null>(null);

  useEffect(() => {
    (async () => {
      const tous = await recupererToutesPages<MouvementStock>("/mouvements-stock/");
      setMouvements(tous.filter((m) => m.boite === boiteId));
    })();
  }, [boiteId]);

  if (mouvements === null) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-2">
        Mouvements
      </h4>
      {mouvements.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">
          Aucun mouvement enregistré.
        </p>
      ) : (
        <ul className="space-y-1">
          {mouvements.slice(0, 10).map((m) => {
            const positif = Number(m.quantite) >= 0;
            return (
              <li
                key={m.id}
                className="flex items-center justify-between text-xs bg-[var(--bg)] rounded-[var(--radius-control)] px-2.5 py-1.5"
              >
                <span className="text-[var(--muted)]">
                  {new Date(m.date_creation).toLocaleString("fr-FR")}
                  {m.motif ? ` · ${m.motif}` : ""}
                </span>
                <span className={positif ? "text-[var(--statut-conforme)]" : "text-[var(--statut-rupture)]"}>
                  {positif ? "+" : ""}
                  {m.quantite}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
