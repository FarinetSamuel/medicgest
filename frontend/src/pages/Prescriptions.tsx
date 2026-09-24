import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search } from "lucide-react";
import { api, recupererToutesPages } from "../lib/api";
import { titrePageClasse } from "../lib/ui";
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
  // tout ce qui est accessible puis on filtre côté client. Le référentiel
  // (France/Suisse) est propre à chaque patient et imposé par le backend.
  useEffect(() => {
    if (!patientSelectionneId) return;
    (async () => {
      setChargementPrescriptions(true);
      try {
        const toutes = await recupererToutesPages<Prescription>("/prescriptions/");
        setPrescriptions(
          toutes.filter(
            (p) =>
              role === "patient" || p.patient === patientSelectionneId
          )
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
  // Statut de la prescription : réservé à admin/médecin côté backend
  // (PeutAccederALaPrescription limite le patient à la lecture seule) —
  // décision clinique, un patient ne change pas lui-même le statut de sa
  // prescription.
  const peutModifierPrescription = role === "admin" || role === "medecin";
  const permissions = utilisateur?.permissions ?? [];
  // Création : admin/médecin toujours, ou un patient qui détient
  // explicitement la permission Django add_prescription (accordée via un
  // Group dans l'admin) — le backend (PrescriptionViewSet) applique la
  // même règle. Voir aussi peutGererHoraires ci-dessous pour le même
  // principe appliqué aux horaires programmés.
  const peutCreer =
    (role === "admin" || role === "medecin" || (role === "patient" && permissions.includes("prescriptions.add_prescription"))) &&
    !!patientSelectionneId;
  // Horaires programmés : admin/médecin toujours, ou un patient qui
  // détient explicitement les permissions Django add_/change_
  // horaireprogramme (accordées via un Group dans l'admin) — le backend
  // (HoraireProgrammeViewSet) applique la même règle.
  const peutGererHoraires =
    role === "admin" ||
    role === "medecin" ||
    (role === "patient" &&
      permissions.includes("prescriptions.add_horaireprogramme") &&
      permissions.includes("prescriptions.change_horaireprogramme"));
  // Enregistrement des prises : le patient garde un accès complet sur ses
  // propres prises (auto-enregistrement d'une prise de réserve).
  const peutModifierPrises = role === "admin" || role === "medecin" || role === "patient";
  // Suppression : alignée sur la permission backend (PeutAccederALaPrescription)
  // — admin toujours, médecin suiveur du patient (déjà garanti puisque seules
  // les prescriptions de patients suivis sont visibles ici), ou un patient
  // qui détient la permission Django add_prescription (celle qui lui permet
  // déjà d'en créer) — un patient qui peut ajouter sa propre prescription
  // doit pouvoir revenir dessus.
  const peutSupprimer =
    role === "admin" ||
    role === "medecin" ||
    (role === "patient" && permissions.includes("prescriptions.add_prescription"));
  // Confirmation automatique des prises programmées : même permission que
  // la création/suppression (add_prescription) — un patient qui peut gérer
  // sa propre prescription doit pouvoir choisir ce réglage, via l'action
  // dédiée /prescriptions/<id>/confirmation-automatique/ (voir
  // PrescriptionViewSet.confirmation_automatique), sans obtenir un accès
  // en écriture générique à la prescription.
  const peutModifierConfirmationAutomatique =
    role === "admin" ||
    role === "medecin" ||
    (role === "patient" && permissions.includes("prescriptions.add_prescription"));

  return (
    <div className="space-y-4">
      <div>
        <h1 className={titrePageClasse}>Prescriptions</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
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

        <div className="space-y-3">
          {(role !== "patient" || peutCreer) && (
            <div className="flex items-center justify-between">
              {role !== "patient" && (
                <h2 className="text-sm font-semibold text-[var(--muted)]">
                  {patientSelectionne
                    ? `${patientSelectionne.utilisateur_prenom} ${patientSelectionne.utilisateur_nom}`.trim() ||
                      patientSelectionne.numero_dossier
                    : "Aucun patient sélectionné"}
                </h2>
              )}
              {peutCreer && (
                <button
                  onClick={() => setModalCreation(true)}
                  className="inline-flex items-center gap-2 text-sm font-medium rounded-[var(--radius-control)] bg-[var(--cta)] text-[var(--cta-ink)] px-3 py-2 hover:brightness-95 transition-colors"
                >
                  <Plus size={16} /> Nouvelle prescription
                </button>
              )}
            </div>
          )}

          {!patientSelectionneId ? (
            <p className="text-sm text-[var(--muted)]">
              Sélectionnez un patient dans la liste pour voir ses prescriptions.
            </p>
          ) : chargementPrescriptions ? (
            <p className="text-sm text-[var(--muted)]">
              Chargement...
            </p>
          ) : prescriptions.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              Aucune prescription pour le moment.
            </p>
          ) : (
            <div className="space-y-2">
              {prescriptions.map((p) => (
                <PrescriptionCard
                  key={p.id}
                  prescription={p}
                  peutModifierPrescription={peutModifierPrescription}
                  peutModifierConfirmationAutomatique={peutModifierConfirmationAutomatique}
                  peutGererHoraires={peutGererHoraires}
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
          patientId={patientSelectionneId === "moi" ? (utilisateur?.patient_id ?? "") : patientSelectionneId}
          onFermer={() => setModalCreation(false)}
          onCree={ajouterPrescription}
        />
      )}
    </div>
  );
}
