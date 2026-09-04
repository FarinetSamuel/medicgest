import { useState } from "react";
import { toast } from "sonner";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
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
  peutGererHoraires,
  peutModifierPrises,
  peutSupprimer,
  onModifiee,
  onSupprimee,
}: {
  prescription: Prescription;
  peutModifierPrescription: boolean;
  peutGererHoraires: boolean;
  peutModifierPrises: boolean;
  peutSupprimer: boolean;
  onModifiee: (prescription: Prescription) => void;
  onSupprimee: (id: string) => void;
}) {
  const [ouvert, setOuvert] = useState(false);

  async function changerStatut(statut: Prescription["statut"]) {
    try {
      const { data } = await api.patch<Prescription>(`/prescriptions/${prescription.id}/`, { statut });
      onModifiee(data);
      toast.success("Statut mis à jour");
    } catch {
      toast.error("Impossible de mettre à jour le statut");
    }
  }

  async function supprimer() {
    try {
      await api.delete(`/prescriptions/${prescription.id}/`);
      onSupprimee(prescription.id);
      toast.success("Prescription supprimée");
    } catch {
      toast.error("Suppression impossible");
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
    <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl overflow-hidden">
      <button onClick={() => setOuvert((o) => !o)} className="w-full text-left px-4 py-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium truncate">{prescription.medicament_nom}</span>
            <StatusBadge ton={STATUTS[prescription.statut].ton}>{STATUTS[prescription.statut].label}</StatusBadge>
          </div>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-0.5">
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
        <div className="px-4 pb-4 space-y-4 border-t border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] pt-3">
          {prescription.instructions && (
            <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
              {prescription.instructions}
            </p>
          )}

          {prescription.type_prise === "reguliere" && (
            <HorairesSection
              prescriptionId={prescription.id}
              horaires={prescription.horaires}
              peutModifier={peutGererHoraires}
              onHoraireAjoute={ajouterHoraire}
              onHoraireModifie={modifierHoraire}
            />
          )}

          <PrisesSection
            prescriptionId={prescription.id}
            typePrise={prescription.type_prise}
            doseQuantiteDefaut={prescription.dose_quantite}
            peutModifier={peutModifierPrises}
          />

          {(peutModifierPrescription || peutSupprimer) && (
            <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]">
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
                  onClick={supprimer}
                  aria-label="Supprimer la prescription"
                  className="p-1.5 rounded-lg hover:bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
