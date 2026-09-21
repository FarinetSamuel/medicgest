import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Search, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { titrePageClasse } from "../lib/ui";
import { useAuth } from "../context/AuthContext";
import { InteractionCard } from "../components/interactions/InteractionCard";
import { NIVEAUX } from "../lib/interactions";
import type { Patient, PageResultat, VerificationInteractions } from "../types";

export function Interactions() {
  const { utilisateur } = useAuth();
  const role = utilisateur?.role;

  const [patients, setPatients] = useState<Patient[]>([]);
  const [chargementPatients, setChargementPatients] = useState(role !== "patient");
  const [recherche, setRecherche] = useState("");
  const [patientSelectionneId, setPatientSelectionneId] = useState<string | null>(
    role === "patient" ? utilisateur?.patient_id ?? null : null
  );

  const [verification, setVerification] = useState<VerificationInteractions | null>(null);
  const [chargementVerification, setChargementVerification] = useState(false);

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

  useEffect(() => {
    if (!patientSelectionneId) return;
    (async () => {
      setChargementVerification(true);
      setVerification(null);
      try {
        const { data } = await api.get<VerificationInteractions>(
          `/patients/${patientSelectionneId}/verifier-interactions/`
        );
        setVerification(data);
      } catch {
        toast.error("Impossible de vérifier les interactions");
      } finally {
        setChargementVerification(false);
      }
    })();
  }, [patientSelectionneId]);

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

  const interactionsTriees = verification
    ? [...verification.interactions].sort((a, b) => NIVEAUX[a.niveau].ordre - NIVEAUX[b.niveau].ordre)
    : [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className={titrePageClasse}>Interactions médicamenteuses</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          {role === "patient"
            ? "Vérification entre vos traitements actuellement actifs."
            : "Sélectionnez un patient pour vérifier ses traitements actuels."}
        </p>
      </div>

      <div className={role === "patient" ? "" : "grid grid-cols-1 lg:grid-cols-[minmax(0,320px)_1fr] gap-4 items-start"}>
        {role !== "patient" && (
          <div className="space-y-3">
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]"
              />
              <input
                value={recherche}
                onChange={(e) => setRecherche(e.target.value)}
                placeholder="Rechercher un patient..."
                className="w-full rounded-[var(--radius-control)] border border-[var(--hairline)] bg-transparent pl-9 pr-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              />
            </div>
            <div className="bg-[var(--surface)] border border-[var(--hairline)] rounded-[var(--radius-card)] divide-y divide-[var(--hairline)] overflow-hidden">
              {chargementPatients ? (
                <p className="text-sm text-[var(--muted)] p-4">
                  Chargement...
                </p>
              ) : patientsFiltres.length === 0 ? (
                <p className="text-sm text-[var(--muted)] p-4">
                  Aucun patient {recherche ? "ne correspond à la recherche" : "pour le moment"}.
                </p>
              ) : (
                patientsFiltres.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPatientSelectionneId(p.id)}
                    className={`w-full text-left px-4 py-3 text-sm transition-colors ${
                      p.id === patientSelectionneId
                        ? "bg-[var(--cta)] text-[var(--cta-ink)]"
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
                          ? "text-[var(--cta-ink)]/80 truncate"
                          : "text-[var(--muted)] truncate"
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

        <div className="space-y-4">
          {role !== "patient" && (
            <h2 className="text-sm font-semibold text-[var(--muted)]">
              {patientSelectionne
                ? `${patientSelectionne.utilisateur_prenom} ${patientSelectionne.utilisateur_nom}`.trim() ||
                  patientSelectionne.numero_dossier
                : "Aucun patient sélectionné"}
            </h2>
          )}

          {!patientSelectionneId ? (
            <p className="text-sm text-[var(--muted)]">
              Sélectionnez un patient dans la liste pour vérifier ses interactions.
            </p>
          ) : chargementVerification || !verification ? (
            <p className="text-sm text-[var(--muted)]">
              Vérification en cours...
            </p>
          ) : (
            <>
              {/* Avertissement de fraîcheur — texte du backend, affiché tel
                  quel et toujours visible, jamais escamotable : sujet santé. */}
              <div className="flex items-start gap-3 bg-[color-mix(in_srgb,var(--statut-rupture)_14%,var(--surface))] text-[var(--statut-rupture)] rounded-[var(--radius-card)] p-4">
                <AlertTriangle size={20} className="shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold">
                    Thésaurus ANSM figé depuis le{" "}
                    {new Date(verification.date_publication_source).toLocaleDateString("fr-FR")}
                  </p>
                  <p className="text-sm mt-1">{verification.avertissement}</p>
                </div>
              </div>

              {verification.medicaments_non_verifiables.length > 0 && (
                <div className="flex items-start gap-3 bg-[color-mix(in_srgb,var(--statut-attention)_14%,var(--surface))] text-[var(--statut-attention)] rounded-[var(--radius-card)] p-4">
                  <AlertTriangle size={20} className="shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold">Vérification non disponible pour certains médicaments</p>
                    <p className="text-sm mt-1">
                      {verification.medicaments_non_verifiables.join(", ")} — les substances de{" "}
                      {verification.medicaments_non_verifiables.length > 1 ? "ces médicaments" : "ce médicament"}{" "}
                      n'ont pas pu être rapprochées du Thésaurus avec certitude (référentiel non français). L'absence
                      d'interaction signalée ci-dessous ne les concerne pas : renseignez-vous auprès d'un pharmacien
                      ou d'un médecin.
                    </p>
                  </div>
                </div>
              )}

              {interactionsTriees.length === 0 ? (
                <div className="flex items-start gap-3 bg-[color-mix(in_srgb,var(--statut-conforme)_14%,var(--surface))] text-[var(--statut-conforme)] rounded-[var(--radius-card)] p-4">
                  <ShieldCheck size={20} className="shrink-0 mt-0.5" />
                  <p className="text-sm">
                    Aucune interaction connue détectée parmi les substances actuellement prescrites, selon le
                    Thésaurus figé ci-dessus.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {interactionsTriees.map((interaction, i) => (
                    <InteractionCard key={`${interaction.substance_a}-${interaction.substance_b}-${i}`} interaction={interaction} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
