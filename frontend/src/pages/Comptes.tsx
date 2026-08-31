import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, ShieldOff } from "lucide-react";
import { api, recupererToutesPages } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { StatusBadge } from "../components/StatusBadge";
import { CompteFormModal } from "../components/comptes/CompteFormModal";
import { libelleSpecialite } from "../lib/specialites";
import type { UtilisateurCompte } from "../types";

type FiltreRole = "tous" | "admin" | "medecin" | "patient";

const ROLES_LABELS: Record<string, string> = {
  admin: "Administrateur",
  medecin: "Médecin",
  patient: "Patient",
  sans_role: "Sans rôle",
};

export function Comptes() {
  const { utilisateur } = useAuth();

  const [comptes, setComptes] = useState<UtilisateurCompte[]>([]);
  const [chargement, setChargement] = useState(true);
  const [recherche, setRecherche] = useState("");
  const [filtreRole, setFiltreRole] = useState<FiltreRole>("tous");
  const [modalCreation, setModalCreation] = useState(false);
  const [compteEnEdition, setCompteEnEdition] = useState<UtilisateurCompte | null>(null);

  async function charger() {
    setChargement(true);
    try {
      const tous = await recupererToutesPages<UtilisateurCompte>("/utilisateurs/");
      setComptes(tous);
    } catch {
      toast.error("Impossible de charger les comptes");
    } finally {
      setChargement(false);
    }
  }

  useEffect(() => {
    if (utilisateur?.role !== "admin") return;
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [utilisateur?.role]);

  function remplacerCompte(compte: UtilisateurCompte) {
    setComptes((liste) => {
      const existe = liste.some((c) => c.id === compte.id);
      return existe ? liste.map((c) => (c.id === compte.id ? compte : c)) : [compte, ...liste];
    });
  }

  async function basculerActif(compte: UtilisateurCompte) {
    try {
      const { data } = await api.patch<UtilisateurCompte>(`/utilisateurs/${compte.id}/`, {
        actif: !compte.actif,
      });
      remplacerCompte(data);
      toast.success(data.actif ? "Compte réactivé" : "Compte désactivé");
    } catch {
      toast.error("Impossible de modifier ce compte");
    }
  }

  if (utilisateur?.role !== "admin") {
    return (
      <div className="flex items-center gap-3 bg-[var(--color-danger-bg)] text-[var(--color-danger)] rounded-xl p-4">
        <ShieldOff size={20} />
        <p className="text-sm">Cette page est réservée aux administrateurs.</p>
      </div>
    );
  }

  const comptesFiltres = comptes.filter((c) => {
    if (filtreRole !== "tous" && c.role !== filtreRole) return false;
    const q = recherche.trim().toLowerCase();
    if (!q) return true;
    return c.email.toLowerCase().includes(q) || `${c.first_name} ${c.last_name}`.toLowerCase().includes(q);
  });

  const FILTRES: { valeur: FiltreRole; label: string }[] = [
    { valeur: "tous", label: "Tous" },
    { valeur: "admin", label: "Administrateurs" },
    { valeur: "medecin", label: "Médecins" },
    { valeur: "patient", label: "Patients" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-[var(--font-display)] text-2xl font-semibold">Comptes utilisateurs</h1>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
            Création et gestion des comptes admin, médecin et patient.
          </p>
        </div>
        <button
          onClick={() => setModalCreation(true)}
          className="inline-flex items-center gap-2 text-sm font-medium rounded-lg bg-[var(--color-brand-500)] text-white px-4 py-2.5 hover:bg-[var(--color-brand-600)] transition-colors shrink-0"
        >
          <Plus size={16} /> Nouveau compte
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]"
          />
          <input
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher par nom ou email..."
            className="w-full rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-transparent pl-9 pr-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-500)]"
          />
        </div>
        <div className="flex gap-2">
          {FILTRES.map((f) => (
            <button
              key={f.valeur}
              onClick={() => setFiltreRole(f.valeur)}
              className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
                filtreRole === f.valeur
                  ? "bg-[var(--color-brand-500)] text-white border-[var(--color-brand-500)]"
                  : "border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl divide-y divide-[var(--color-border-light)] dark:divide-[var(--color-border-dark)] overflow-hidden">
        {chargement ? (
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
            Chargement...
          </p>
        ) : comptesFiltres.length === 0 ? (
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
            Aucun compte {recherche || filtreRole !== "tous" ? "ne correspond aux critères" : "pour le moment"}.
          </p>
        ) : (
          comptesFiltres.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <button onClick={() => setCompteEnEdition(c)} className="min-w-0 text-left flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`font-medium truncate ${
                      !c.actif ? "text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] line-through" : ""
                    }`}
                  >
                    {c.first_name} {c.last_name}
                  </span>
                  <StatusBadge ton={c.role === "admin" ? "warning" : c.role === "medecin" ? "success" : "muted"}>
                    {ROLES_LABELS[c.role] ?? c.role}
                  </StatusBadge>
                  {!c.actif && <StatusBadge ton="danger">Désactivé</StatusBadge>}
                </div>
                <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] truncate">
                  {c.email}
                  {c.role === "medecin" && c.specialite && ` · ${libelleSpecialite(c.specialite, c.specialite_autre)}`}
                </p>
              </button>
              <button
                onClick={() => basculerActif(c)}
                className="text-xs font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline shrink-0"
              >
                {c.actif ? "Désactiver" : "Réactiver"}
              </button>
            </div>
          ))
        )}
      </div>

      {modalCreation && (
        <CompteFormModal compte={null} onFermer={() => setModalCreation(false)} onSauvegarde={remplacerCompte} />
      )}
      {compteEnEdition && (
        <CompteFormModal
          compte={compteEnEdition}
          onFermer={() => setCompteEnEdition(null)}
          onSauvegarde={remplacerCompte}
        />
      )}
    </div>
  );
}
