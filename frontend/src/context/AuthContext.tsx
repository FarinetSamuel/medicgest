import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, jetons } from "../lib/api";

export type Role = "admin" | "medecin" | "patient" | "sans_role";

export interface UtilisateurConnecte {
  id: string;
  email: string;
  prenom: string;
  nom: string;
  role: Role;
  patient_id?: string;
}

interface AuthContextValue {
  utilisateur: UtilisateurConnecte | null;
  chargement: boolean;
  connexion: (email: string, motDePasse: string) => Promise<void>;
  deconnexion: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<UtilisateurConnecte | null>(null);
  const [chargement, setChargement] = useState(true);

  const chargerUtilisateur = useCallback(async () => {
    if (!jetons.lireAccess()) {
      setChargement(false);
      return;
    }
    try {
      const { data } = await api.get<UtilisateurConnecte>("/auth/me/");
      setUtilisateur(data);
    } catch {
      jetons.effacer();
      setUtilisateur(null);
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    chargerUtilisateur();
  }, [chargerUtilisateur]);

  const connexion = useCallback(async (email: string, motDePasse: string) => {
    const { data } = await api.post("/auth/token/", { email, password: motDePasse });
    jetons.stocker(data.access, data.refresh);
    const { data: profil } = await api.get<UtilisateurConnecte>("/auth/me/");
    setUtilisateur(profil);
  }, []);

  const deconnexion = useCallback(() => {
    jetons.effacer();
    setUtilisateur(null);
  }, []);

  return (
    <AuthContext.Provider value={{ utilisateur, chargement, connexion, deconnexion }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const contexte = useContext(AuthContext);
  if (!contexte) throw new Error("useAuth doit être utilisé dans un AuthProvider");
  return contexte;
}
