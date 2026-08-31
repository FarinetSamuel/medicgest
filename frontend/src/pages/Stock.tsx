import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search } from "lucide-react";
import { api, recupererToutesPages } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { BoiteFormModal } from "../components/stock/BoiteFormModal";
import { BoiteCard } from "../components/stock/BoiteCard";
import type { Boite, Patient, PageResultat } from "../types";

export function Stock() {
  const { utilisateur } = useAuth();
  const role = utilisateur?.role;

  const [patients, setPatients] = useState<Patient[]>([]);
  const [chargementPatients, setChargementPatients] = useState(role !== "patient");
  const [recherche, setRecherche] = useState("");
  const [patientSelectionneId, setPatientSelectionneId] = useState<string | null>(
    role === "patient" ? "moi" : null
  );

  const [boites, setBoites] = useState<Boite[]>([]);
  const [chargementBoites, setChargementBoites] = useState(false);
  const [modalCreation, setModalCreation] = useState(false);
  const [boiteEnEdition, setBoiteEnEdition] = useState<Boite | null>(null);

  useEffect(() => {
    if (role === "patient") return;
    (async () => {
      setChargementPatients(true);
      try {
        const { data } = await api.get<PageResultat<Patient>>("/patients/");
        setPatients(data.results);
      } catch {
        toast.error("Impossible de charger les patients");
      } finally {
        setChargementPatients(false);
      }
    })();
  }, [role]);

  // Pas de filtre serveur par patient (aucun filter_backend sur
  // BoiteViewSet) — on récupère tout ce qui est accessible puis on
  // filtre côté client, comme pour Prescriptions.
  useEffect(() => {
    if (!patientSelectionneId) return;
    (async () => {
      setChargementBoites(true);
      try {
        const toutes = await recupererToutesPages<Boite>("/boites/");
        setBoites(role === "patient" ? toutes : toutes.filter((b) => b.patient === patientSelectionneId));
      } catch {
        toast.error("Impossible de charger le stock");
      } finally {
        setChargementBoites(false);
      }
    })();
  }, [patientSelectionneId, role]);

  function ajouterBoite(boite: Boite) {
    setBoites((liste) => [boite, ...liste]);
  }

  function remplacerBoite(boite: Boite) {
    setBoites((liste) => liste.map((b) => (b.id === boite.id ? boite : b)));
  }

  function retirerBoite(id: string) {
    setBoites((liste) => liste.filter((b) => b.id !== id));
  }

  const patientsFiltres = patients.filter((p) => {
    const q = recherche.trim().toLowerCase();
    if (!q) return true;
    return (
      p.numero_dossier.toLowerCase().includes(q) ||
      p.utilisateur_email.toLowerCase().includes(q) ||
      `${p.utilisateur_prenom} ${p.utilisateur_nom}`.toLowerCase().includes(q)
    );
  });

  const patientSelectionne = patients.find((p) => p.id === patientSelectionneId) ?? null;
  const peutCreer = !!patientSelectionneId;
  const peutModifier = true;

  // Boîtes en alerte d'abord, puis actives, puis le reste — pour que ce
  // qui demande une action soit visible sans avoir à tout parcourir.
  const boitesTriees = [...boites].sort((a, b) => {
    if (a.en_alerte !== b.en_alerte) return a.en_alerte ? -1 : 1;
    if (a.statut !== b.statut) return a.statut === "active" ? -1 : 1;
    return 0;
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-[var(--font-display)] text-2xl font-semibold">Stock</h1>
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
          {role === "patient"
            ? "Vos boîtes de médicaments et leurs alertes de réapprovisionnement."
            : "Sélectionnez un patient pour voir et gérer son stock."}
        </p>
      </div>

      <div className={role === "patient" ? "" : "grid grid-cols-1 lg:grid-cols-[minmax(0,320px)_1fr] gap-4 items-start"}>
        {role !== "patient" && (
          <div className="space-y-3">
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]"
              />
              <input
                value={recherche}
                onChange={(e) => setRecherche(e.target.value)}
                placeholder="Rechercher un patient..."
                className="w-full rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-transparent pl-9 pr-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-500)]"
              />
            </div>
            <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl divide-y divide-[var(--color-border-light)] dark:divide-[var(--color-border-dark)] overflow-hidden">
              {chargementPatients ? (
                <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
                  Chargement...
                </p>
              ) : patientsFiltres.length === 0 ? (
                <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
                  Aucun patient {recherche ? "ne correspond à la recherche" : "pour le moment"}.
                </p>
              ) : (
                patientsFiltres.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPatientSelectionneId(p.id)}
                    className={`w-full text-left px-4 py-3 text-sm transition-colors ${
                      p.id === patientSelectionneId
                        ? "bg-[var(--color-brand-500)] text-white"
                        : "hover:bg-black/5 dark:hover:bg-white/5"
                    }`}
                  >
                    <div className="font-medium truncate">
                      {p.utilisateur_prenom || p.utilisateur_nom
                        ? `${p.utilisateur_prenom} ${p.utilisateur_nom}`.trim()
                        : p.numero_dossier}
                    </div>
                    <div
                      className={
                        p.id === patientSelectionneId
                          ? "text-white/80 truncate"
                          : "text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] truncate"
                      }
                    >
                      {p.numero_dossier}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {role !== "patient" && (
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
                {patientSelectionne
                  ? `${patientSelectionne.utilisateur_prenom} ${patientSelectionne.utilisateur_nom}`.trim() ||
                    patientSelectionne.numero_dossier
                  : "Aucun patient sélectionné"}
              </h2>
              {peutCreer && (
                <button
                  onClick={() => setModalCreation(true)}
                  className="inline-flex items-center gap-2 text-sm font-medium rounded-lg bg-[var(--color-brand-500)] text-white px-3 py-2 hover:bg-[var(--color-brand-600)] transition-colors"
                >
                  <Plus size={16} /> Nouvelle boîte
                </button>
              )}
            </div>
          )}

          {role === "patient" && (
            <div className="flex justify-end">
              <button
                onClick={() => setModalCreation(true)}
                className="inline-flex items-center gap-2 text-sm font-medium rounded-lg bg-[var(--color-brand-500)] text-white px-3 py-2 hover:bg-[var(--color-brand-600)] transition-colors"
              >
                <Plus size={16} /> Nouvelle boîte
              </button>
            </div>
          )}

          {!patientSelectionneId ? (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Sélectionnez un patient dans la liste pour voir son stock.
            </p>
          ) : chargementBoites ? (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Chargement...
            </p>
          ) : boitesTriees.length === 0 ? (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Aucune boîte enregistrée.
            </p>
          ) : (
            <div className="space-y-2">
              {boitesTriees.map((b) => (
                <BoiteCard
                  key={b.id}
                  boite={b}
                  peutModifier={peutModifier}
                  onModifier={() => setBoiteEnEdition(b)}
                  onSupprimee={retirerBoite}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {modalCreation && patientSelectionneId && (
        <BoiteFormModal
          patientId={patientSelectionneId === "moi" ? (utilisateur?.patient_id ?? "") : patientSelectionneId}
          boite={null}
          onFermer={() => setModalCreation(false)}
          onSauvegarde={ajouterBoite}
        />
      )}
      {boiteEnEdition && (
        <BoiteFormModal
          patientId={boiteEnEdition.patient}
          boite={boiteEnEdition}
          onFermer={() => setBoiteEnEdition(null)}
          onSauvegarde={remplacerBoite}
        />
      )}
    </div>
  );
}
