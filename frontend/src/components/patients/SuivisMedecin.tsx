import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";
import { api, recupererToutesPages } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import type { PatientMedecin, UtilisateurCompte } from "../../types";

/**
 * Gestion des suivis médecin-patient — action réservée à l'admin côté
 * backend (PatientMedecinViewSet.get_permissions). L'endpoint /suivis-medecin/
 * ne propose pas de filtre par patient : on récupère tout puis on filtre
 * côté client (borné à 10 pages / 250 suivis, voir recupererToutesPages).
 */
export function SuivisMedecin({ patientId }: { patientId: string }) {
  const [suivis, setSuivis] = useState<PatientMedecin[]>([]);
  const [chargement, setChargement] = useState(true);
  const [ouvert, setOuvert] = useState(false);
  const [medecins, setMedecins] = useState<UtilisateurCompte[]>([]);
  const [medecinChoisi, setMedecinChoisi] = useState("");
  const [enCours, setEnCours] = useState(false);

  async function charger() {
    setChargement(true);
    const tous = await recupererToutesPages<PatientMedecin>("/suivis-medecin/");
    setSuivis(tous.filter((s) => s.patient === patientId));
    setChargement(false);
  }

  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  async function ouvrirFormulaire() {
    setOuvert(true);
    const tous = await recupererToutesPages<UtilisateurCompte>("/utilisateurs/");
    setMedecins(tous.filter((u) => u.role === "medecin" && u.actif));
  }

  async function handleAssigner(e: FormEvent) {
    e.preventDefault();
    if (!medecinChoisi) return;
    setEnCours(true);
    try {
      await api.post("/suivis-medecin/", { patient: patientId, medecin: medecinChoisi, actif: true });
      toast.success("Médecin assigné");
      setOuvert(false);
      setMedecinChoisi("");
      await charger();
    } catch {
      toast.error("Impossible d'assigner ce médecin (un suivi actif existe peut-être déjà)");
    } finally {
      setEnCours(false);
    }
  }

  async function revoquer(suivi: PatientMedecin) {
    try {
      await api.patch(`/suivis-medecin/${suivi.id}/`, {
        actif: false,
        date_fin: new Date().toISOString().slice(0, 10),
      });
      toast.success("Suivi révoqué");
      await charger();
    } catch {
      toast.error("Impossible de révoquer ce suivi");
    }
  }

  if (chargement) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Médecins suiveurs</h3>
        {!ouvert && (
          <button
            onClick={ouvrirFormulaire}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
          >
            <Plus size={16} /> Assigner
          </button>
        )}
      </div>

      {ouvert && (
        <form onSubmit={handleAssigner} className="mb-3 flex gap-2">
          <select
            required
            value={medecinChoisi}
            onChange={(e) => setMedecinChoisi(e.target.value)}
            className={champClasse}
          >
            <option value="">Choisir un médecin...</option>
            {medecins.map((m) => (
              <option key={m.id} value={m.id}>
                {m.first_name} {m.last_name} ({m.email})
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={enCours}
            className="shrink-0 text-sm px-3 py-2 rounded-lg bg-[var(--color-brand-500)] text-white hover:bg-[var(--color-brand-600)] disabled:opacity-60"
          >
            Valider
          </button>
          <button
            type="button"
            onClick={() => setOuvert(false)}
            aria-label="Annuler"
            className="shrink-0 text-sm px-2 rounded-lg text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
          >
            <X size={18} />
          </button>
        </form>
      )}

      {suivis.length === 0 ? (
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Aucun médecin suiveur.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {suivis.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between text-sm bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-lg px-3 py-2"
            >
              <span>
                {s.medecin_email}
                {!s.actif && (
                  <span className="ml-2 text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
                    (terminé{s.date_fin ? ` le ${new Date(s.date_fin).toLocaleDateString("fr-FR")}` : ""})
                  </span>
                )}
              </span>
              {s.actif && (
                <button onClick={() => revoquer(s)} className="text-xs text-[var(--color-danger)] hover:underline">
                  Révoquer
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
