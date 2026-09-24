import { useState } from "react";
import { toast } from "sonner";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import { Modal } from "../Modal";
import { StatusBadge } from "../StatusBadge";
import { HorairesSection } from "./HorairesSection";
import { PrisesSection } from "./PrisesSection";
import type { HoraireProgramme, Prescription } from "../../types";

const STATUTS: Record<Prescription["statut"], { label: string; ton: "danger" | "warning" | "success" | "muted" }> = {
  active: { label: "Active", ton: "success" },
  arretee: { label: "Arrêtée", ton: "danger" },
  terminee: { label: "Terminée", ton: "muted" },
};

export function PrescriptionCard({
  prescription,
  peutModifierPrescription,
  peutModifierConfirmationAutomatique,
  peutGererHoraires,
  peutModifierPrises,
  peutSupprimer,
  onModifiee,
  onSupprimee,
}: {
  prescription: Prescription;
  peutModifierPrescription: boolean;
  peutModifierConfirmationAutomatique: boolean;
  peutGererHoraires: boolean;
  peutModifierPrises: boolean;
  peutSupprimer: boolean;
  onModifiee: (prescription: Prescription) => void;
  onSupprimee: (id: string) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [confirmationSuppression, setConfirmationSuppression] = useState(false);

  async function changerStatut(statut: Prescription["statut"]) {
    try {
      const { data } = await api.patch<Prescription>(`/prescriptions/${prescription.id}/`, { statut });
      onModifiee(data);
      toast.success("Statut mis à jour");
    } catch {
      toast.error("Impossible de mettre à jour le statut");
    }
  }

  async function changerConfirmationAutomatique(confirmation_automatique: boolean) {
    try {
      // Action dédiée (pas le PATCH générique de la prescription) : c'est
      // elle qui autorise un patient disposant de la permission
      // add_prescription à changer ce réglage, sans lui ouvrir le reste
      // des champs cliniques (voir PrescriptionViewSet.confirmation_automatique).
      const { data } = await api.patch<Prescription>(
        `/prescriptions/${prescription.id}/confirmation-automatique/`,
        { confirmation_automatique }
      );
      onModifiee(data);
      toast.success("Préférence mise à jour");
    } catch {
      toast.error("Impossible de mettre à jour la préférence");
    }
  }

  async function supprimer() {
    try {
      await api.delete(`/prescriptions/${prescription.id}/`);
      onSupprimee(prescription.id);
      toast.success("Prescription supprimée");
    } catch {
      toast.error("Suppression impossible");
    } finally {
      setConfirmationSuppression(false);
    }
  }

  function ajouterHoraire(horaire: HoraireProgramme) {
    onModifiee({ ...prescription, horaires: [...prescription.horaires, horaire] });
  }

  function modifierHoraire(horaire: HoraireProgramme) {
    onModifiee({
      ...prescription,
      horaires: prescription.horaires.map((h) => (h.id === horaire.id ? horaire : h)),
    });
  }

  return (
    <div className="bg-[var(--surface)] border border-[var(--hairline)] rounded-[var(--radius-card)] overflow-hidden">
      <button onClick={() => setOuvert((o) => !o)} className="w-full text-left px-4 py-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium truncate">{prescription.medicament_nom}</span>
            <StatusBadge ton={STATUTS[prescription.statut].ton}>{STATUTS[prescription.statut].label}</StatusBadge>
          </div>
          <p className="text-sm text-[var(--muted)] mt-0.5">
            {prescription.dose_quantite} {prescription.dose_unite} ·{" "}
            {prescription.type_prise === "reguliere"
              ? `Régulière${prescription.frequence_par_jour ? ` (${prescription.frequence_par_jour}×/jour)` : ""}`
              : "Réserve"}{" "}
            · depuis le {new Date(prescription.date_debut).toLocaleDateString("fr-FR")}
          </p>
        </div>
        {ouvert ? <ChevronUp size={18} className="shrink-0" /> : <ChevronDown size={18} className="shrink-0" />}
      </button>

      {ouvert && (
        <div className="px-4 pb-4 space-y-4 border-t border-[var(--hairline)] pt-3">
          {prescription.instructions && (
            <p className="text-sm text-[var(--muted)]">
              {prescription.instructions}
            </p>
          )}

          {prescription.type_prise === "reguliere" && (
            <>
              {peutModifierConfirmationAutomatique ? (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={prescription.confirmation_automatique}
                    onChange={(e) => changerConfirmationAutomatique(e.target.checked)}
                  />
                  <span>
                    Confirmer automatiquement les prises programmées
                    <span className="block text-xs text-[var(--muted)] mt-0.5">
                      Chaque prise passe à « Prise » dès son heure prévue atteinte, sans action manuelle. Sinon,
                      elle reste « Attendue » jusqu'à confirmation.
                    </span>
                  </span>
                </label>
              ) : (
                // Lecture seule (comme le statut de la prescription, voir plus bas)
                // pour un patient sans la permission add_prescription : pas de case
                // à cocher désactivée, qui donnerait l'impression trompeuse d'un
                // contrôle interactif bloqué.
                <p className="text-sm">
                  Confirmation automatique des prises :{" "}
                  <span className="font-medium">
                    {prescription.confirmation_automatique ? "activée" : "désactivée"}
                  </span>
                  <span className="block text-xs text-[var(--muted)] mt-0.5">
                    {prescription.confirmation_automatique
                      ? "Chaque prise passe à « Prise » dès son heure prévue atteinte, sans action manuelle."
                      : "Chaque prise reste « Attendue » jusqu'à confirmation manuelle."}{" "}
                    Réglage modifiable par votre médecin.
                  </span>
                </p>
              )}

              <HorairesSection
                prescriptionId={prescription.id}
                horaires={prescription.horaires}
                peutModifier={peutGererHoraires}
                onHoraireAjoute={ajouterHoraire}
                onHoraireModifie={modifierHoraire}
              />
            </>
          )}

          <PrisesSection
            prescriptionId={prescription.id}
            typePrise={prescription.type_prise}
            doseQuantiteDefaut={prescription.dose_quantite}
            peutModifier={peutModifierPrises}
          />

          {(peutModifierPrescription || peutSupprimer) && (
            <div className="flex items-center justify-between pt-2 border-t border-[var(--hairline)]">
              {peutModifierPrescription ? (
                <select
                  value={prescription.statut}
                  onChange={(e) => changerStatut(e.target.value as Prescription["statut"])}
                  className={`${champClasse} py-1.5 w-auto text-xs`}
                >
                  <option value="active">Active</option>
                  <option value="arretee">Arrêtée</option>
                  <option value="terminee">Terminée</option>
                </select>
              ) : (
                <span />
              )}
              {peutSupprimer && (
                <button
                  onClick={() => setConfirmationSuppression(true)}
                  aria-label="Supprimer la prescription"
                  className="p-1.5 rounded-[var(--radius-control)] hover:bg-[var(--hairline-soft)] dark:hover:bg-[var(--hairline)] text-[var(--statut-rupture)]"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {confirmationSuppression && (
        <Modal titre="Supprimer cette prescription ?" onFermer={() => setConfirmationSuppression(false)} largeur="max-w-sm">
          <p className="text-sm mb-4">
            La prescription de <strong>{prescription.medicament_nom}</strong> et l'historique des prises associées
            seront supprimés définitivement. Cette action est irréversible.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmationSuppression(false)}
              className="text-sm px-4 py-2 rounded-[var(--radius-control)] text-[var(--muted)] hover:bg-black/5 dark:hover:bg-white/5"
            >
              Annuler
            </button>
            <button
              onClick={supprimer}
              className="text-sm px-4 py-2 rounded-[var(--radius-control)] bg-[var(--statut-rupture)] text-[var(--surface)] hover:opacity-90"
            >
              Supprimer
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
