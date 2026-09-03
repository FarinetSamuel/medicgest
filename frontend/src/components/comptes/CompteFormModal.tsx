import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Modal } from "../Modal";
import { champClasse } from "../../lib/ui";
import { api } from "../../lib/api";
import { SPECIALITES } from "../../lib/specialites";
import type { UtilisateurCompte } from "../../types";

interface ChampsFormulaire {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role: string;
  specialite: string;
  specialite_autre: string;
  actif: boolean;
}

const VIDE: ChampsFormulaire = {
  email: "",
  first_name: "",
  last_name: "",
  password: "",
  role: "medecin",
  specialite: "",
  specialite_autre: "",
  actif: true,
};

export function CompteFormModal({
  compte,
  onFermer,
  onSauvegarde,
}: {
  /** null = création */
  compte: UtilisateurCompte | null;
  onFermer: () => void;
  onSauvegarde: (compte: UtilisateurCompte) => void;
}) {
  const modeCreation = compte === null;
  const [champs, setChamps] = useState<ChampsFormulaire>(
    compte
      ? {
          email: compte.email,
          first_name: compte.first_name,
          last_name: compte.last_name,
          password: "",
          role: compte.role,
          specialite: compte.specialite,
          specialite_autre: compte.specialite_autre,
          actif: compte.actif,
        }
      : VIDE
  );
  const [enCours, setEnCours] = useState(false);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});

  function champTexte(nom: "email" | "first_name" | "last_name" | "password" | "specialite_autre") {
    return {
      value: champs[nom],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => setChamps((c) => ({ ...c, [nom]: e.target.value })),
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreurs({});
    setEnCours(true);
    try {
      if (modeCreation) {
        const payload: Record<string, unknown> = {
          email: champs.email,
          first_name: champs.first_name,
          last_name: champs.last_name,
          password: champs.password,
          role: champs.role,
          actif: champs.actif,
        };
        if (champs.role === "medecin") {
          payload.specialite = champs.specialite;
          if (champs.specialite === "autre") payload.specialite_autre = champs.specialite_autre;
        }
        const { data } = await api.post<UtilisateurCompte>("/utilisateurs/", payload);
        toast.success("Compte créé");
        onSauvegarde(data);
      } else {
        const payload: Record<string, unknown> = {
          first_name: champs.first_name,
          last_name: champs.last_name,
          actif: champs.actif,
        };
        if (compte!.role === "medecin") {
          payload.specialite = champs.specialite;
          payload.specialite_autre = champs.specialite === "autre" ? champs.specialite_autre : "";
        }
        if (champs.password) payload.password = champs.password;
        const { data } = await api.patch<UtilisateurCompte>(`/utilisateurs/${compte!.id}/`, payload);
        toast.success("Compte mis à jour");
        onSauvegarde(data);
      }
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
      toast.error("Impossible d'enregistrer le compte");
    } finally {
      setEnCours(false);
    }
  }

  const role = modeCreation ? champs.role : compte!.role;

  return (
    <Modal titre={modeCreation ? "Nouveau compte" : "Modifier le compte"} onFermer={onFermer}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          {modeCreation ? (
            <input required type="email" {...champTexte("email")} className={champClasse} />
          ) : (
            <p className={`${champClasse} text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]`}>
              {compte!.email}
            </p>
          )}
          {erreurs.email && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.email}</p>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1.5">Prénom</label>
            <input required {...champTexte("first_name")} className={champClasse} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Nom</label>
            <input required {...champTexte("last_name")} className={champClasse} />
          </div>
        </div>

        {modeCreation ? (
          <div>
            <label className="block text-sm font-medium mb-1.5">Mot de passe</label>
            <input required type="password" minLength={8} {...champTexte("password")} className={champClasse} />
            {erreurs.password && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.password}</p>}
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium mb-1.5">Réinitialiser le mot de passe</label>
            <input
              type="password"
              minLength={8}
              placeholder="Laisser vide pour ne pas changer"
              {...champTexte("password")}
              className={champClasse}
            />
            {erreurs.password && <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.password}</p>}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-1.5">Rôle</label>
          {modeCreation ? (
            <select
              required
              value={champs.role}
              onChange={(e) => setChamps((c) => ({ ...c, role: e.target.value, specialite: "", specialite_autre: "" }))}
              className={champClasse}
            >
              <option value="admin">Administrateur</option>
              <option value="medecin">Médecin</option>
              <option value="patient">Patient</option>
            </select>
          ) : (
            <p className={`${champClasse} text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] capitalize`}>
              {compte!.role}
              <span className="text-xs block mt-0.5 normal-case">
                Le rôle ne peut pas être modifié après la création.
              </span>
            </p>
          )}
        </div>

        {role === "medecin" && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1.5">Spécialité</label>
              <select
                value={champs.specialite}
                onChange={(e) => setChamps((c) => ({ ...c, specialite: e.target.value }))}
                className={champClasse}
              >
                <option value="">Non précisée</option>
                {SPECIALITES.map((s) => (
                  <option key={s.valeur} value={s.valeur}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            {champs.specialite === "autre" && (
              <div>
                <label className="block text-sm font-medium mb-1.5">Préciser la spécialité</label>
                <input required {...champTexte("specialite_autre")} className={champClasse} />
                {erreurs.specialite_autre && (
                  <p className="text-xs text-[var(--color-danger)] mt-1">{erreurs.specialite_autre}</p>
                )}
              </div>
            )}
          </div>
        )}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={champs.actif}
            onChange={(e) => setChamps((c) => ({ ...c, actif: e.target.checked }))}
          />
          Compte actif (peut se connecter)
        </label>

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
