import { useState } from "react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import type { Patient } from "../../types";

const LABELS: Record<Patient["preference_alerte_stock"], string> = {
  patient: "Le patient",
  medecin: "Le médecin suiveur",
  les_deux: "Le patient et le médecin suiveur",
};

/**
 * Choix librement modifiable par le patient lui-même (action dédiée côté
 * backend, PatientViewSet.preference_alerte_stock — la fiche Patient reste
 * en lecture seule pour lui via le endpoint principal). Un médecin suiveur
 * ou un admin peut aussi le régler pour un patient qu'il gère.
 */
export function PreferenceAlerteStock({
  patient,
  onPatientMaj,
}: {
  patient: Patient;
  onPatientMaj: (patient: Patient) => void;
}) {
  const [enCours, setEnCours] = useState(false);

  async function changer(valeur: Patient["preference_alerte_stock"]) {
    setEnCours(true);
    try {
      const { data } = await api.patch<Patient>(`/patients/${patient.id}/preference-alerte-stock/`, {
        preference_alerte_stock: valeur,
      });
      onPatientMaj(data);
      toast.success("Préférence mise à jour");
    } catch {
      toast.error("Impossible de mettre à jour la préférence");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div>
      <h3 className="text-sm font-semibold mb-2">Alertes de stock bas / rupture</h3>
      <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mb-2">
        Qui est prévenu quand le stock d'un médicament est bas ou totalement épuisé.
      </p>
      <select
        value={patient.preference_alerte_stock}
        disabled={enCours}
        onChange={(e) => changer(e.target.value as Patient["preference_alerte_stock"])}
        className={champClasse}
      >
        {Object.entries(LABELS).map(([valeur, label]) => (
          <option key={valeur} value={valeur}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}
