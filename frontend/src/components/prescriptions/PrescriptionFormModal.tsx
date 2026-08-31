import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Modal } from "../Modal";
import { champClasse } from "../../lib/ui";
import { api, recupererToutesPages } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { MedicamentSelect } from "./MedicamentSelect";
import type { Medicament, Prescription, UtilisateurCompte } from "../../types";

export function PrescriptionFormModal({
  patientId,
  onFermer,
  onCree,
}: {
  patientId: string;
  onFermer: () => void;
  onCree: (prescription: Prescription) => void;
}) {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";

  const [medicament, setMedicament] = useState<Medicament | null>(null);
  const [medecinPrescripteur, setMedecinPrescripteur] = useState("");
  const [medecins, setMedecins] = useState<UtilisateurCompte[] | null>(null);
  const [typePrise, setTypePrise] = useState<"reguliere" | "reserve">("reguliere");
  const [doseQuantite, setDoseQuantite] = useState("");
  const [doseUnite, setDoseUnite] = useState("");
  const [frequenceParJour, setFrequenceParJour] = useState("");
  const [doseMaxParJour, setDoseMaxParJour] = useState("");
  const [dateDebut, setDateDebut] = useState(new Date().toISOString().slice(0, 10));
  const [dateFin, setDateFin] = useState("");
  const [instructions, setInstructions] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});

  // Admin : le prescripteur doit être précisé côté client (voir
  // PrescriptionViewSet.perform_create) — on propose donc la liste des
  // comptes médecin actifs.
  useEffect(() => {
    if (!estAdmin) return;
    (async () => {
      const tous = await recupererToutesPages<UtilisateurCompte>("/utilisateurs/");
      setMedecins(tous.filter((u) => u.role === "medecin" && u.actif));
    })();
  }, [estAdmin]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreurs({});
    if (!medicament) {
      setErreurs({ medicament: "Choisissez un médicament." });
      return;
    }
    setEnCours(true);
    try {
      const payload: Record<string, unknown> = {
        patient: patientId,
        medicament: medicament.id,
        type_prise: typePrise,
        dose_quantite: doseQuantite,
        dose_unite: doseUnite,
        date_debut: dateDebut,
        date_fin: dateFin || null,
        instructions,
      };
      if (typePrise === "reguliere") {
        if (frequenceParJour) payload.frequence_par_jour = Number(frequenceParJour);
      } else {
        if (doseMaxParJour) payload.dose_max_par_jour = doseMaxParJour;
      }
      if (estAdmin) payload.medecin_prescripteur = medecinPrescripteur;

      const { data } = await api.post<Prescription>("/prescriptions/", payload);
      toast.success("Prescription créée");
      onCree(data);
      onFermer();
    } catch (err) {
      const donnees = (err as { response?: { data?: unknown } })?.response?.data;
      if (donnees && typeof donnees === "object") {
        const messages: Record<string, string> = {};
        for (const [cle, val] of Object.entries(donnees as Record<string, unknown>)) {
          messages[cle] = Array.isArray(val) ? val.join(" ") : String(val);
        }
        setErreurs(messages);
      }
      toast.error("Impossible de créer la prescription");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <Modal titre="Nouvelle prescription" onFermer={onFermer} largeur="max-w-xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Médicament</label>
          <MedicamentSelect valeur={medicament} onChoisir={setMedicament} />
          {erreurs.medicament && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.medicament}</p>}
        </div>

        {estAdmin && (
          <div>
            <label className="block text-sm font-medium mb-1.5">Médecin prescripteur</label>
            {medecins === null ? (
              <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
                Chargement...
              </p>
            ) : (
              <select
                required
                value={medecinPrescripteur}
                onChange={(e) => setMedecinPrescripteur(e.target.value)}
                className={champClasse}
              >
                <option value="">Choisir un médecin...</option>
                {medecins.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.first_name} {m.last_name} ({m.email})
                  </option>
                ))}
              </select>
            )}
            {erreurs.medecin_prescripteur && (
              <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.medecin_prescripteur}</p>
            )}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-1.5">Type de prise</label>
          <div className="flex gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                checked={typePrise === "reguliere"}
                onChange={() => setTypePrise("reguliere")}
              />
              Régulière (horaires fixes)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={typePrise === "reserve"} onChange={() => setTypePrise("reserve")} />
              Réserve (au besoin)
            </label>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1.5">Quantité par prise</label>
            <input
              required
              type="number"
              step="0.01"
              min="0"
              value={doseQuantite}
              onChange={(e) => setDoseQuantite(e.target.value)}
              className={champClasse}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Unité</label>
            <input
              required
              placeholder="comprimé, ml, mg..."
              value={doseUnite}
              onChange={(e) => setDoseUnite(e.target.value)}
              className={champClasse}
            />
          </div>
        </div>

        {typePrise === "reguliere" ? (
          <div>
            <label className="block text-sm font-medium mb-1.5">Prises par jour (facultatif)</label>
            <input
              type="number"
              min="1"
              value={frequenceParJour}
              onChange={(e) => setFrequenceParJour(e.target.value)}
              className={champClasse}
            />
            <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
              Les horaires précis se règlent après création de la prescription.
            </p>
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium mb-1.5">Plafond journalier (facultatif)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={doseMaxParJour}
              onChange={(e) => setDoseMaxParJour(e.target.value)}
              className={champClasse}
            />
            <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
              Un dépassement sera enregistré quand même, avec une alerte — jamais bloqué.
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1.5">Date de début</label>
            <input
              required
              type="date"
              value={dateDebut}
              onChange={(e) => setDateDebut(e.target.value)}
              className={champClasse}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Date de fin (facultatif)</label>
            <input type="date" value={dateFin} onChange={(e) => setDateFin(e.target.value)} className={champClasse} />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1.5">Instructions (facultatif)</label>
          <textarea
            rows={2}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            className={champClasse}
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onFermer}
            className="text-sm px-4 py-2 rounded-lg text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={enCours}
            className="text-sm px-4 py-2 rounded-lg bg-[var(--color-brand-500)] text-white hover:bg-[var(--color-brand-600)] disabled:opacity-60"
          >
            {enCours ? "Création..." : "Créer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
