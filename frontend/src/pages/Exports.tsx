import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { FileDown } from "lucide-react";
import { api, recupererToutesPages } from "../lib/api";
import { boutonPrimaireClasse, champClasse, titreCarteClasse, titrePageClasse } from "../lib/ui";
import { useAuth } from "../context/AuthContext";
import type { Patient } from "../types";

type Contenu = "complet" | "prescriptions" | "prises" | "stock" | "a_venir";

interface MedecinPrescripteur {
  id: string;
  nom: string;
}

const CONTENUS: { valeur: Contenu; label: string; description: string }[] = [
  {
    valeur: "complet",
    label: "Rapport complet",
    description: "Prescriptions actives, interactions détectées, prises de la période et stock actuel.",
  },
  {
    valeur: "prescriptions",
    label: "Prescriptions par médecin",
    description: "Prescriptions regroupées par médecin prescripteur, avec leurs horaires.",
  },
  {
    valeur: "prises",
    label: "Prises sur une période",
    description: "Ce que le patient a pris sur la période choisie, avec le total par médicament.",
  },
  {
    valeur: "stock",
    label: "Stock",
    description: "Boîtes actives : quantité restante, péremption et alerte.",
  },
  {
    valeur: "a_venir",
    label: "Prises à venir et stock (liste de vacances)",
    description:
      "Prises prévues sur une période à venir, quantité nécessaire par médicament et stock correspondant.",
  },
];

/** AAAA-MM-JJ en heure locale (toISOString() décalerait le jour en UTC). */
function dateLocaleIso(date: Date): string {
  const mois = String(date.getMonth() + 1).padStart(2, "0");
  const jour = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${mois}-${jour}`;
}

function dansNJours(n: number): string {
  const date = new Date();
  date.setDate(date.getDate() + n);
  return dateLocaleIso(date);
}

export function Exports() {
  const { utilisateur } = useAuth();
  const role = utilisateur?.role;

  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState<string>(
    role === "patient" ? utilisateur?.patient_id ?? "" : ""
  );
  const [contenu, setContenu] = useState<Contenu>("complet");
  const [dateDebut, setDateDebut] = useState(() => dansNJours(-30));
  const [dateFin, setDateFin] = useState(() => dansNJours(0));
  const [medecins, setMedecins] = useState<MedecinPrescripteur[]>([]);
  const [medecinId, setMedecinId] = useState("");
  const [inclureInactives, setInclureInactives] = useState(false);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    if (role === "patient") return;
    (async () => {
      try {
        setPatients(await recupererToutesPages<Patient>("/patients/"));
      } catch {
        toast.error("Impossible de charger les patients");
      }
    })();
  }, [role]);

  // Les médecins proposés sont ceux qui ont prescrit pour ce patient.
  useEffect(() => {
    if (!patientId) return;
    (async () => {
      try {
        const { data } = await api.get<{ medecins: MedecinPrescripteur[] }>(
          `/patients/${patientId}/export-options/`
        );
        setMedecins(data.medecins);
      } catch {
        toast.error("Impossible de charger les médecins prescripteurs");
      }
    })();
  }, [patientId]);

  const aVenir = contenu === "a_venir";
  const avecPeriode = contenu === "complet" || contenu === "prises" || aVenir;
  const aujourdhui = dansNJours(0);
  const periodeInvalide =
    avecPeriode && (!dateDebut || !dateFin || dateDebut > dateFin || (aVenir && dateFin < aujourdhui));

  // La période par défaut dépend du sens : passée pour les prises
  // effectuées (30 derniers jours), future pour les prises à venir.
  function changerContenu(nouveau: Contenu) {
    if ((nouveau === "a_venir") !== aVenir) {
      setDateDebut(dansNJours(nouveau === "a_venir" ? 0 : -30));
      setDateFin(dansNJours(nouveau === "a_venir" ? 14 : 0));
    }
    setContenu(nouveau);
  }

  async function telecharger(e: FormEvent) {
    e.preventDefault();
    if (!patientId || periodeInvalide) return;
    setEnCours(true);
    try {
      const params: Record<string, string> = { contenu };
      if (avecPeriode) {
        params.date_debut = dateDebut;
        params.date_fin = dateFin;
      } else if (contenu === "prescriptions") {
        if (medecinId) params.medecin = medecinId;
        if (inclureInactives) params.inclure_inactives = "true";
      }
      const { data } = await api.get<Blob>(`/patients/${patientId}/export-pdf/`, {
        params,
        responseType: "blob",
      });
      const url = URL.createObjectURL(data);
      const lien = document.createElement("a");
      lien.href = url;
      lien.download = `medicgest-${contenu}-${dateLocaleIso(new Date())}.pdf`;
      document.body.appendChild(lien);
      lien.click();
      lien.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Impossible de générer le PDF");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className={titrePageClasse}>Exports</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Choisissez le contenu du PDF à télécharger.
        </p>
      </div>

      <form
        onSubmit={telecharger}
        className="max-w-2xl bg-[var(--surface)] border border-[var(--hairline)] rounded-[var(--radius-card)] p-5 space-y-5"
      >
        {role !== "patient" && (
          <div>
            <label htmlFor="export-patient" className="block text-sm font-medium mb-1.5">
              Patient
            </label>
            <select
              id="export-patient"
              value={patientId}
              onChange={(e) => {
                setPatientId(e.target.value);
                setMedecins([]);
                setMedecinId("");
              }}
              className={champClasse}
            >
              <option value="">Sélectionnez un patient</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {`${p.utilisateur_prenom} ${p.utilisateur_nom}`.trim() || p.utilisateur_email} —{" "}
                  {p.numero_dossier}
                </option>
              ))}
            </select>
          </div>
        )}

        <fieldset className="space-y-2">
          <legend className={`${titreCarteClasse} mb-2`}>Contenu</legend>
          {CONTENUS.map((c) => (
            <label
              key={c.valeur}
              className="flex items-start gap-3 rounded-[var(--radius-control)] border border-[var(--hairline)] px-3 py-2.5 cursor-pointer"
            >
              <input
                type="radio"
                name="contenu"
                value={c.valeur}
                checked={contenu === c.valeur}
                onChange={() => changerContenu(c.valeur)}
                className="mt-1"
              />
              <span>
                <span className="block text-sm font-medium">{c.label}</span>
                <span className="block text-sm text-[var(--muted)]">{c.description}</span>
              </span>
            </label>
          ))}
        </fieldset>

        {avecPeriode && (
          <div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="export-date-debut" className="block text-sm font-medium mb-1.5">
                  {aVenir ? "Du" : "Prises du"}
                </label>
                <input
                  id="export-date-debut"
                  type="date"
                  required
                  value={dateDebut}
                  min={aVenir ? aujourdhui : undefined}
                  max={dateFin || undefined}
                  onChange={(e) => setDateDebut(e.target.value)}
                  className={champClasse}
                />
              </div>
              <div>
                <label htmlFor="export-date-fin" className="block text-sm font-medium mb-1.5">
                  au (inclus)
                </label>
                <input
                  id="export-date-fin"
                  type="date"
                  required
                  value={dateFin}
                  min={dateDebut || undefined}
                  onChange={(e) => setDateFin(e.target.value)}
                  className={champClasse}
                />
              </div>
            </div>
            {dateDebut && dateFin && dateDebut > dateFin && (
              <p className="text-xs text-[var(--statut-rupture)] mt-1">
                La date de fin précède la date de début.
              </p>
            )}
            {aVenir && (
              <p className="text-xs text-[var(--muted)] mt-1">
                Seules les prescriptions régulières sont comptées ; les médicaments de réserve sont listés
                à part, sans estimation.
              </p>
            )}
          </div>
        )}

        {contenu === "prescriptions" && (
          <div className="space-y-3">
            <div>
              <label htmlFor="export-medecin" className="block text-sm font-medium mb-1.5">
                Médecin prescripteur
              </label>
              <select
                id="export-medecin"
                value={medecinId}
                onChange={(e) => setMedecinId(e.target.value)}
                className={champClasse}
              >
                <option value="">Tous les médecins</option>
                {medecins.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nom}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={inclureInactives}
                onChange={(e) => setInclureInactives(e.target.checked)}
              />
              Inclure les prescriptions arrêtées et terminées
            </label>
          </div>
        )}

        <button
          type="submit"
          disabled={!patientId || periodeInvalide || enCours}
          className={boutonPrimaireClasse}
        >
          <FileDown size={16} />
          {enCours ? "Génération..." : "Télécharger le PDF"}
        </button>
      </form>
    </div>
  );
}
