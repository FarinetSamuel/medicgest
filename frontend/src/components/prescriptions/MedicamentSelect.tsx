import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import type { Medicament, PageResultat } from "../../types";

/**
 * Recherche server-side (?search=) sur /medicaments/ — indispensable avec
 * 15 857 médicaments réels importés depuis la BDPM. Ne renvoie rien tant
 * que la requête ne fait pas au moins 3 caractères, pour éviter de
 * recharger la liste complète à chaque frappe.
 *
 * Filtrée côté backend par le référentiel du patient (?patient=, voir
 * Patient.referentiel_medicaments) : les catalogues BDPM (France) et
 * Swissmedic (Suisse) ne sont jamais mélangés dans un même choix (voir
 * Medicament.verification_interactions_fiable).
 */
export function MedicamentSelect({
  patientId,
  valeur,
  onChoisir,
}: {
  patientId: string;
  valeur: Medicament | null;
  onChoisir: (medicament: Medicament) => void;
}) {
  const [requete, setRequete] = useState("");
  const [resultats, setResultats] = useState<Medicament[]>([]);
  const [ouvert, setOuvert] = useState(false);
  const [recherche, setRecherche] = useState(false);
  const delai = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (delai.current) clearTimeout(delai.current);
    if (requete.trim().length < 3) return;
    delai.current = setTimeout(async () => {
      setRecherche(true);
      try {
        const { data } = await api.get<PageResultat<Medicament>>("/medicaments/", {
          params: { search: requete.trim(), patient: patientId },
        });
        setResultats(data.results);
      } finally {
        setRecherche(false);
      }
    }, 300);
    return () => {
      if (delai.current) clearTimeout(delai.current);
    };
  }, [requete, patientId]);

  return (
    <div className="relative">
      {valeur && !ouvert ? (
        <button
          type="button"
          onClick={() => setOuvert(true)}
          className={`${champClasse} text-left flex items-center justify-between`}
        >
          <span>
            {valeur.denomination}
            {valeur.dosage ? ` — ${valeur.dosage}` : ""}
          </span>
          <span className="text-xs text-[var(--accent)]">
            Changer
          </span>
        </button>
      ) : (
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]"
          />
          <input
            autoFocus
            value={requete}
            onChange={(e) => setRequete(e.target.value)}
            onFocus={() => setOuvert(true)}
            placeholder="Rechercher un médicament (nom ou code CIS)..."
            className={`${champClasse} pl-9`}
          />
        </div>
      )}

      {ouvert && requete.trim().length >= 3 && (
        <div className="absolute z-10 mt-1 w-full max-h-64 overflow-y-auto bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-control)]">
          {recherche ? (
            <p className="text-sm text-[var(--muted)] p-3">
              Recherche...
            </p>
          ) : resultats.length === 0 ? (
            <p className="text-sm text-[var(--muted)] p-3">
              Aucun médicament trouvé.
            </p>
          ) : (
            resultats.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  onChoisir(m);
                  setRequete("");
                  setResultats([]);
                  setOuvert(false);
                }}
                className="w-full text-left px-3 py-2 text-sm hover:bg-black/5 dark:hover:bg-white/5"
              >
                <div className="font-medium">{m.denomination}</div>
                <div className="text-xs text-[var(--muted)]">
                  {m.dosage || m.forme_pharmaceutique || m.code_cis}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
