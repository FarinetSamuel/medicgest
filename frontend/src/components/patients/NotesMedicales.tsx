import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import { StatusBadge } from "../StatusBadge";
import type { NoteMedicale } from "../../types";

const CATEGORIES: Record<NoteMedicale["categorie"], { label: string; ton: "danger" | "warning" | "muted" }> = {
  allergie: { label: "Allergie", ton: "danger" },
  antecedent: { label: "Antécédent médical", ton: "warning" },
  observation: { label: "Observation générale", ton: "muted" },
};

export function NotesMedicales({
  patientId,
  notes,
  peutAjouter,
  onNoteAjoutee,
}: {
  patientId: string;
  notes: NoteMedicale[];
  peutAjouter: boolean;
  onNoteAjoutee: (note: NoteMedicale) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [categorie, setCategorie] = useState<NoteMedicale["categorie"]>("observation");
  const [contenu, setContenu] = useState("");
  const [enCours, setEnCours] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!contenu.trim()) return;
    setEnCours(true);
    try {
      const { data } = await api.post<NoteMedicale>("/notes-medicales/", {
        patient: patientId,
        categorie,
        contenu: contenu.trim(),
      });
      onNoteAjoutee(data);
      setContenu("");
      setCategorie("observation");
      setOuvert(false);
      toast.success("Note ajoutée");
    } catch {
      toast.error("Impossible d'ajouter la note");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Notes médicales</h3>
        {peutAjouter && !ouvert && (
          <button
            onClick={() => setOuvert(true)}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
          >
            <Plus size={16} /> Ajouter une note
          </button>
        )}
      </div>

      {ouvert && (
        <form
          onSubmit={handleSubmit}
          className="mb-4 space-y-3 bg-[var(--color-bg-light)] dark:bg-[var(--color-bg-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-lg p-3"
        >
          <select
            value={categorie}
            onChange={(e) => setCategorie(e.target.value as NoteMedicale["categorie"])}
            className={champClasse}
          >
            {(Object.entries(CATEGORIES) as [NoteMedicale["categorie"], (typeof CATEGORIES)[NoteMedicale["categorie"]]][]).map(
              ([valeur, { label }]) => (
                <option key={valeur} value={valeur}>
                  {label}
                </option>
              )
            )}
          </select>
          <textarea
            required
            rows={3}
            value={contenu}
            onChange={(e) => setContenu(e.target.value)}
            placeholder="Contenu de la note..."
            className={champClasse}
          />
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setOuvert(false)}
              className="text-sm px-3 py-1.5 rounded-lg text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={enCours}
              className="text-sm px-3 py-1.5 rounded-lg bg-[var(--color-brand-500)] text-white hover:bg-[var(--color-brand-600)] disabled:opacity-60"
            >
              {enCours ? "Ajout..." : "Ajouter"}
            </button>
          </div>
        </form>
      )}

      {notes.length === 0 ? (
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Aucune note enregistrée.
        </p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-1.5 gap-2">
                <StatusBadge ton={CATEGORIES[note.categorie].ton}>{CATEGORIES[note.categorie].label}</StatusBadge>
                <span className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] text-right">
                  {new Date(note.date_creation).toLocaleDateString("fr-FR")}
                  {note.saisi_par_email ? ` — ${note.saisi_par_email}` : ""}
                </span>
              </div>
              <p className="text-sm whitespace-pre-wrap">{note.contenu}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
