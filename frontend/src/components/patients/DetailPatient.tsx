import { Pencil, Trash2 } from "lucide-react";
import { titreSectionClasse } from "../../lib/ui";
import { NotesMedicales } from "./NotesMedicales";
import { PreferenceAlerteStock } from "./PreferenceAlerteStock";
import { SuivisMedecin } from "./SuivisMedecin";
import type { NoteMedicale, Patient } from "../../types";

const SEXE_LABELS: Record<Patient["sexe"], string> = {
  F: "Féminin",
  M: "Masculin",
  A: "Autre / non précisé",
};

export function DetailPatient({
  patient,
  peutEditer,
  peutSupprimer,
  peutAjouterNote,
  peutGererSuivis,
  onModifier,
  onSupprimer,
  onNoteAjoutee,
  onPatientMaj,
}: {
  patient: Patient;
  peutEditer: boolean;
  peutSupprimer: boolean;
  peutAjouterNote: boolean;
  peutGererSuivis: boolean;
  onModifier: () => void;
  onSupprimer: () => void;
  onNoteAjoutee: (note: NoteMedicale) => void;
  onPatientMaj: (patient: Patient) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className={titreSectionClasse}>
            {patient.utilisateur_prenom} {patient.utilisateur_nom}
          </h2>
          <p className="text-sm text-[var(--muted)] mt-0.5 break-all">
            Dossier {patient.numero_dossier} — {patient.utilisateur_email}
          </p>
        </div>
        {(peutEditer || peutSupprimer) && (
          <div className="flex gap-1 shrink-0">
            {peutEditer && (
              <button
                onClick={onModifier}
                aria-label="Modifier"
                className="p-2 rounded-[var(--radius-control)] hover:bg-black/5 dark:hover:bg-white/5 text-[var(--muted)]"
              >
                <Pencil size={16} />
              </button>
            )}
            {peutSupprimer && (
              <button
                onClick={onSupprimer}
                aria-label="Supprimer"
                className="p-2 rounded-[var(--radius-control)] hover:bg-[var(--hairline-soft)] dark:hover:bg-[var(--hairline)] text-[var(--statut-rupture)]"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-[var(--muted)]">Date de naissance</span>
          <p className="mt-0.5">{new Date(patient.date_naissance).toLocaleDateString("fr-FR")}</p>
        </div>
        <div>
          <span className="text-[var(--muted)]">Sexe</span>
          <p className="mt-0.5">{SEXE_LABELS[patient.sexe]}</p>
        </div>
      </div>

      {(patient.contact_urgence_nom || patient.contact_urgence_telephone) && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Contact d'urgence</h3>
          <div className="text-sm bg-[var(--bg)] rounded-[var(--radius-control)] p-3 space-y-0.5">
            {patient.contact_urgence_nom && (
              <p>
                {patient.contact_urgence_nom}
                {patient.contact_urgence_lien ? ` (${patient.contact_urgence_lien})` : ""}
              </p>
            )}
            {patient.contact_urgence_telephone && (
              <p className="text-[var(--muted)]">
                {patient.contact_urgence_telephone}
              </p>
            )}
          </div>
        </div>
      )}

      <PreferenceAlerteStock patient={patient} onPatientMaj={onPatientMaj} />

      {peutGererSuivis && <SuivisMedecin patientId={patient.id} />}

      <NotesMedicales
        patientId={patient.id}
        notes={patient.notes_medicales}
        peutAjouter={peutAjouterNote}
        onNoteAjoutee={onNoteAjoutee}
      />
    </div>
  );
}
