import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search } from "lucide-react";
import { api, recupererToutesPages } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { PrescriptionFormModal } from "../components/prescriptions/PrescriptionFormModal";
import { PrescriptionCard } from "../components/prescriptions/PrescriptionCard";
import type { Patient, PageResultat, Prescription } from "../types";

export function Prescriptions() {
  const { utilisateur } = useAuth();
  const role = utilisateur?.role;

  const [patients, setPatients] = useState<Patient[]>([]);
  const [chargementPatients, setChargementPatients] = useState(role !== "patient");
  const [recherche, setRecherche] = useState("");
  const [patientSelectionneId, setPatientSelectionneId] = useState<string | null>(
    role === "patient" ? "moi" : null
  );

  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [chargementPrescriptions, setChargementPrescriptions] = useState(false);
  const [modalCreation, setModalCreation] = useState(false);

  // Admin/médecin : liste des patients pour choisir sur qui travailler.
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

  // Prescriptions du patient sélectionné. Pas de filtre serveur par
  // patient (aucun filter_backend sur PrescriptionViewSet) — on récupère
  // tout ce qui est accessible puis on filtre côté client.
  useEffect(() => {
    if (!patientSelectionneId) return;
    (async () => {
      setChargementPrescriptions(true);
      try {
        const toutes = await recupererToutesPages<Prescription>("/prescriptions/");
        setPrescriptions(
          role === "patient" ? toutes : toutes.filter((p) => p.patient === patientSelectionneId)
        );
      } catch {
        toast.error("Impossible de charger les prescriptions");
      } finally {
        setChargementPrescriptions(false);
      }
    })();
  }, [patientSelectionneId, role]);

  function ajouterPrescription(prescription: Prescription) {
    setPrescriptions((liste) => [prescription, ...liste]);
  }

  function remplacerPrescription(prescription: Prescription) {
    setPrescriptions((liste) => liste.map((p) => (p.id === prescription.id ? prescription : p)));
  }

  function retirerPrescription(id: string) {
    setPrescriptions((liste) => liste.filter((p) => p.id !== id));
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
  const peutCreer = (role === "admin" || role === "medecin") && !!patientSelectionneId;
  // Statut de la prescription et horaires programmés : réservés à
  // admin/médecin côté backend (PeutAccederALaPrescription limite le
  // patient à la lecture seule, HoraireProgrammeViewSet exige
  // EstAdminOuMedecin) — un patient ne peut pas modifier son propre
  // schéma posologique, décision clinique du médecin.
  const peutModifierPrescription = role === "admin" || role === "medecin";
  // Enregistrement des prises : le patient garde un accès complet sur ses
  // propres prises (auto-enregistrement d'une prise de réserve).
  const peutModifierPrises = role === "admin" || role === "medecin" || role === "patient";
  const peutSupprimer = role === "admin";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-[var(--font-display)] text-2xl font-semibold">Prescriptions</h1>
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
          {role === "patient"
            ? "Vos traitements en cours et leur historique de prises."
            : "Sélectionnez un patient pour voir et gérer ses prescriptions."}
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
                  <Plus size={16} /> Nouvelle prescription
                </button>
              )}
            </div>
          )}

          {!patientSelectionneId ? (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Sélectionnez un patient dans la liste pour voir ses prescriptions.
            </p>
          ) : chargementPrescriptions ? (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Chargement...
            </p>
          ) : prescriptions.length === 0 ? (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Aucune prescription pour le moment.
            </p>
          ) : (
            <div className="space-y-2">
              {prescriptions.map((p) => (
                <PrescriptionCard
                  key={p.id}
                  prescription={p}
                  peutModifierPrescription={peutModifierPrescription}
                  peutModifierPrises={peutModifierPrises}
                  peutSupprimer={peutSupprimer}
                  onModifiee={remplacerPrescription}
                  onSupprimee={retirerPrescription}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {modalCreation && patientSelectionneId && (
        <PrescriptionFormModal
          patientId={patientSelectionneId}
          onFermer={() => setModalCreation(false)}
          onCree={ajouterPrescription}
        />
      )}
    </div>
  );
}
