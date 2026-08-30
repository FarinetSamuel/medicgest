import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { toast } from "sonner";
import { Modal } from "../Modal";
import { champClasse } from "../../lib/ui";
import { api, recupererToutesPages } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import type { Patient, UtilisateurCompte } from "../../types";

interface ChampsFormulaire {
  utilisateur: string;
  numero_dossier: string;
  date_naissance: string;
  sexe: string; // "F" | "M" | "A" — élargi en string pour simplifier le formulaire, contraint par les <option>
  contact_urgence_nom: string;
  contact_urgence_telephone: string;
  contact_urgence_lien: string;
}

const VIDE: ChampsFormulaire = {
  utilisateur: "",
  numero_dossier: "",
  date_naissance: "",
  sexe: "A",
  contact_urgence_nom: "",
  contact_urgence_telephone: "",
  contact_urgence_lien: "",
};

export function PatientFormModal({
  patient,
  onFermer,
  onSauvegarde,
}: {
  /** null = création, sinon édition de ce patient */
  patient: Patient | null;
  onFermer: () => void;
  onSauvegarde: (patient: Patient) => void;
}) {
  const { utilisateur: utilisateurConnecte } = useAuth();
  const estAdmin = utilisateurConnecte?.role === "admin";
  const modeCreation = patient === null;

  const [champs, setChamps] = useState<ChampsFormulaire>(
    patient
      ? {
          utilisateur: patient.utilisateur,
          numero_dossier: patient.numero_dossier,
          date_naissance: patient.date_naissance,
          sexe: patient.sexe,
          contact_urgence_nom: patient.contact_urgence_nom,
          contact_urgence_telephone: patient.contact_urgence_telephone,
          contact_urgence_lien: patient.contact_urgence_lien,
        }
      : VIDE
  );
  const [candidats, setCandidats] = useState<UtilisateurCompte[] | null>(null);
  const [chargementCandidats, setChargementCandidats] = useState(modeCreation && estAdmin);
  const [enCours, setEnCours] = useState(false);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});

  // Admin en création : ne proposer que les comptes de rôle "patient",
  // actifs, et qui n'ont pas déjà une fiche Patient (relation OneToOne).
  useEffect(() => {
    if (!modeCreation || !estAdmin) return;
    (async () => {
      const [tousUtilisateurs, tousPatients] = await Promise.all([
        recupererToutesPages<UtilisateurCompte>("/utilisateurs/"),
        recupererToutesPages<Patient>("/patients/"),
      ]);
      const idsDejaFiches = new Set(tousPatients.map((p) => p.utilisateur));
      setCandidats(
        tousUtilisateurs.filter((u) => u.role === "patient" && u.actif && !idsDejaFiches.has(u.id))
      );
      setChargementCandidats(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function champ(nom: keyof ChampsFormulaire) {
    return {
      value: champs[nom],
      onChange: (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
        setChamps((c) => ({ ...c, [nom]: e.target.value })),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreurs({});
    setEnCours(true);
    try {
      if (modeCreation) {
        const { data } = await api.post<Patient>("/patients/", champs);
        toast.success("Patient créé");
        onSauvegarde(data);
        onFermer();
      } else {
        const { utilisateur: _ignore, ...modifiable } = champs;
        const { data } = await api.patch<Patient>(`/patients/${patient!.id}/`, modifiable);
        toast.success("Patient mis à jour");
        onSauvegarde(data);
        onFermer();
      }
    } catch (err) {
      const donnees = (err as { response?: { data?: unknown } })?.response?.data;
      if (donnees && typeof donnees === "object") {
        const messages: Record<string, string> = {};
        for (const [cle, valeur] of Object.entries(donnees as Record<string, unknown>)) {
          messages[cle] = Array.isArray(valeur) ? valeur.join(" ") : String(valeur);
        }
        setErreurs(messages);
      }
      toast.error("Impossible d'enregistrer le patient");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <Modal titre={modeCreation ? "Nouveau patient" : "Modifier le patient"} onFermer={onFermer}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {modeCreation ? (
          <div>
            <label className="block text-sm font-medium mb-1.5">Compte utilisateur</label>
            {estAdmin ? (
              chargementCandidats ? (
                <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
                  Chargement des comptes disponibles...
                </p>
              ) : candidats && candidats.length === 0 ? (
                <p className="text-sm text-[var(--color-warning)]">
                  Aucun compte "patient" disponible sans fiche existante. Créez d'abord le compte utilisateur
                  dans la gestion des comptes.
                </p>
              ) : (
                <select required {...champ("utilisateur")} className={champClasse}>
                  <option value="">Choisir un compte...</option>
                  {candidats?.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name} {u.last_name} ({u.email})
                    </option>
                  ))}
                </select>
              )
            ) : (
              <>
                <input required placeholder="UUID du compte utilisateur" {...champ("utilisateur")} className={champClasse} />
                <p className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
                  Le compte doit déjà exister (créé par un administrateur). En tant que médecin, vous ne
                  pouvez pas parcourir la liste des comptes ici — demandez l'identifiant à un administrateur.
                </p>
              </>
            )}
            {erreurs.utilisateur && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.utilisateur}</p>}
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium mb-1.5">Compte utilisateur</label>
            <p className={`${champClasse} text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]`}>
              {patient!.utilisateur_email}
            </p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-1.5">Numéro de dossier</label>
          <input required {...champ("numero_dossier")} className={champClasse} />
          {erreurs.numero_dossier && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.numero_dossier}</p>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1.5">Date de naissance</label>
            <input required type="date" {...champ("date_naissance")} className={champClasse} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Sexe</label>
            <select required {...champ("sexe")} className={champClasse}>
              <option value="F">Féminin</option>
              <option value="M">Masculin</option>
              <option value="A">Autre / non précisé</option>
            </select>
          </div>
        </div>

        <fieldset className="border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-lg p-3 space-y-3">
          <legend className="text-xs font-medium px-1 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
            Contact d'urgence (facultatif)
          </legend>
          <input placeholder="Nom" {...champ("contact_urgence_nom")} className={champClasse} />
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Téléphone" {...champ("contact_urgence_telephone")} className={champClasse} />
            <input placeholder="Lien (conjoint, enfant...)" {...champ("contact_urgence_lien")} className={champClasse} />
          </div>
        </fieldset>

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
            {enCours ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
