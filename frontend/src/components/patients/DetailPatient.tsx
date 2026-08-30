import { Pencil, Trash2 } from "lucide-react";
import { NotesMedicales } from "./NotesMedicales";
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
}: {
  patient: Patient;
  peutEditer: boolean;
  peutSupprimer: boolean;
  peutAjouterNote: boolean;
  peutGererSuivis: boolean;
  onModifier: () => void;
  onSupprimer: () => void;
  onNoteAjoutee: (note: NoteMedicale) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-[var(--font-display)] text-xl font-semibold">
            {patient.utilisateur_prenom} {patient.utilisateur_nom}
          </h2>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-0.5 break-all">
            Dossier {patient.numero_dossier} — {patient.utilisateur_email}
          </p>
        </div>
        {(peutEditer || peutSupprimer) && (
          <div className="flex gap-1 shrink-0">
            {peutEditer && (
              <button
                onClick={onModifier}
                aria-label="Modifier"
                className="p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]"
              >
                <Pencil size={16} />
              </button>
            )}
            {peutSupprimer && (
              <button
                onClick={onSupprimer}
                aria-label="Supprimer"
                className="p-2 rounded-lg hover:bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">Date de naissance</span>
          <p className="mt-0.5">{new Date(patient.date_naissance).toLocaleDateString("fr-FR")}</p>
        </div>
        <div>
          <span className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">Sexe</span>
          <p className="mt-0.5">{SEXE_LABELS[patient.sexe]}</p>
        </div>
      </div>

      {(patient.contact_urgence_nom || patient.contact_urgence_telephone) && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Contact d'urgence</h3>
          <div className="text-sm bg-[var(--color-bg-light)] dark:bg-[var(--color-bg-dark)] rounded-lg p-3 space-y-0.5">
            {patient.contact_urgence_nom && (
              <p>
                {patient.contact_urgence_nom}
                {patient.contact_urgence_lien ? ` (${patient.contact_urgence_lien})` : ""}
              </p>
            )}
            {patient.contact_urgence_telephone && (
              <p className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
                {patient.contact_urgence_telephone}
              </p>
            )}
          </div>
        </div>
      )}

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
