import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Modal } from "../components/Modal";
import { PatientFormModal } from "../components/patients/PatientFormModal";
import { DetailPatient } from "../components/patients/DetailPatient";
import type { NoteMedicale, PageResultat, Patient } from "../types";

export function Patients() {
  const { utilisateur } = useAuth();
  const role = utilisateur?.role;

  const [patients, setPatients] = useState<Patient[]>([]);
  const [pageSuivante, setPageSuivante] = useState<string | null>(null);
  const [pagePrecedente, setPagePrecedente] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [recherche, setRecherche] = useState("");
  const [selectionId, setSelectionId] = useState<string | null>(null);
  const [modalCreation, setModalCreation] = useState(false);
  const [patientEnEdition, setPatientEnEdition] = useState<Patient | null>(null);
  const [patientASupprimer, setPatientASupprimer] = useState<Patient | null>(null);

  async function charger(url = "/patients/") {
    setChargement(true);
    try {
      const { data } = await api.get<PageResultat<Patient>>(url);
      setPatients(data.results);
      setPageSuivante(data.next);
      setPagePrecedente(data.previous);
      if (role === "patient" && data.results.length > 0) {
        setSelectionId(data.results[0].id);
      }
    } catch {
      toast.error("Impossible de charger les patients");
    } finally {
      setChargement(false);
    }
  }

  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patientsFiltres = patients.filter((p) => {
    const q = recherche.trim().toLowerCase();
    if (!q) return true;
    return p.numero_dossier.toLowerCase().includes(q) || p.utilisateur_email.toLowerCase().includes(q);
  });

  const patientSelectionne = patients.find((p) => p.id === selectionId) ?? null;

  function remplacerPatient(patientMaj: Patient) {
    setPatients((liste) => {
      const existe = liste.some((p) => p.id === patientMaj.id);
      return existe ? liste.map((p) => (p.id === patientMaj.id ? patientMaj : p)) : [patientMaj, ...liste];
    });
    setSelectionId(patientMaj.id);
  }

  function ajouterNote(note: NoteMedicale) {
    setPatients((liste) =>
      liste.map((p) => (p.id === note.patient ? { ...p, notes_medicales: [note, ...p.notes_medicales] } : p))
    );
  }

  async function confirmerSuppression() {
    if (!patientASupprimer) return;
    try {
      await api.delete(`/patients/${patientASupprimer.id}/`);
      setPatients((liste) => liste.filter((p) => p.id !== patientASupprimer.id));
      if (selectionId === patientASupprimer.id) setSelectionId(null);
      toast.success("Patient supprimé");
    } catch {
      toast.error("Suppression impossible");
    } finally {
      setPatientASupprimer(null);
    }
  }

  const peutCreer = role === "admin" || role === "medecin";

  if (chargement) {
    return <p className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">Chargement...</p>;
  }

  // Rôle patient : pas de liste (l'API ne renvoie que sa propre fiche),
  // affichage direct en lecture seule.
  if (role === "patient") {
    if (!patientSelectionne) {
      return (
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Aucune fiche patient associée à votre compte.
        </p>
      );
    }
    return (
      <div className="max-w-2xl bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl p-6">
        <DetailPatient
          patient={patientSelectionne}
          peutEditer={false}
          peutSupprimer={false}
          peutAjouterNote={false}
          peutGererSuivis={false}
          onModifier={() => {}}
          onSupprimer={() => {}}
          onNoteAjoutee={() => {}}
          onPatientMaj={remplacerPatient}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-[var(--font-display)] text-2xl font-semibold">Patients</h1>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
            {role === "medecin" ? "Patients que vous suivez activement." : "Ensemble des patients."}
          </p>
        </div>
        {peutCreer && (
          <button
            onClick={() => setModalCreation(true)}
            className="inline-flex items-center gap-2 text-sm font-medium rounded-lg bg-[var(--color-brand-500)] text-white px-4 py-2.5 hover:bg-[var(--color-brand-600)] transition-colors shrink-0"
          >
            <Plus size={16} /> Nouveau patient
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,360px)_1fr] gap-4 items-start">
        <div className="space-y-3">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]"
            />
            <input
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              placeholder="Rechercher par dossier ou email..."
              className="w-full rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-transparent pl-9 pr-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-500)]"
            />
          </div>

          <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl divide-y divide-[var(--color-border-light)] dark:divide-[var(--color-border-dark)] overflow-hidden">
            {patientsFiltres.length === 0 ? (
              <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
                Aucun patient {recherche ? "ne correspond à la recherche" : "pour le moment"}.
              </p>
            ) : (
              patientsFiltres.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectionId(p.id)}
                  className={`w-full text-left px-4 py-3 text-sm transition-colors ${
                    p.id === selectionId
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
                      p.id === selectionId
                        ? "text-white/80 truncate"
                        : "text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] truncate"
                    }
                  >
                    {p.numero_dossier} · {p.utilisateur_email}
                  </div>
                </button>
              ))
            )}
          </div>

          {(pageSuivante || pagePrecedente) && (
            <div className="flex justify-between text-sm px-1">
              <button
                disabled={!pagePrecedente}
                onClick={() => pagePrecedente && charger(pagePrecedente)}
                className="disabled:opacity-40 text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
              >
                ← Précédent
              </button>
              <button
                disabled={!pageSuivante}
                onClick={() => pageSuivante && charger(pageSuivante)}
                className="disabled:opacity-40 text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
              >
                Suivant →
              </button>
            </div>
          )}
        </div>

        <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl p-6">
          {patientSelectionne ? (
            <DetailPatient
              patient={patientSelectionne}
              peutEditer
              peutSupprimer={role === "admin"}
              peutAjouterNote
              peutGererSuivis={role === "admin"}
              onModifier={() => setPatientEnEdition(patientSelectionne)}
              onSupprimer={() => setPatientASupprimer(patientSelectionne)}
              onNoteAjoutee={ajouterNote}
              onPatientMaj={remplacerPatient}
            />
          ) : (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              Sélectionnez un patient dans la liste.
            </p>
          )}
        </div>
      </div>

      {modalCreation && (
        <PatientFormModal patient={null} onFermer={() => setModalCreation(false)} onSauvegarde={remplacerPatient} />
      )}
      {patientEnEdition && (
        <PatientFormModal
          patient={patientEnEdition}
          onFermer={() => setPatientEnEdition(null)}
          onSauvegarde={remplacerPatient}
        />
      )}
      {patientASupprimer && (
        <Modal titre="Supprimer ce patient ?" onFermer={() => setPatientASupprimer(null)} largeur="max-w-sm">
          <p className="text-sm mb-4">
            La fiche de <strong>{patientASupprimer.utilisateur_email}</strong> (dossier{" "}
            {patientASupprimer.numero_dossier}) et toutes ses notes médicales seront supprimées définitivement.
            Cette action est irréversible.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setPatientASupprimer(null)}
              className="text-sm px-4 py-2 rounded-lg text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
            >
              Annuler
            </button>
            <button
              onClick={confirmerSuppression}
              className="text-sm px-4 py-2 rounded-lg bg-[var(--color-danger)] text-white hover:opacity-90"
            >
              Supprimer
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
