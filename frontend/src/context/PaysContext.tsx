import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

/**
 * Pays du référentiel médicaments actif côté client — mêmes valeurs que
 * Medicament.Source côté backend (voir apps/medicaments/models.py), pour
 * passer directement `?source=<pays>` à l'API sans table de conversion.
 * Purement un filtre d'affichage : les deux catalogues (BDPM français,
 * Swissmedic latin) ne sont jamais mélangés dans un même formulaire, ni
 * dans la liste des prescriptions, pour éviter toute confusion entre
 * référentiels dont les noms de substances ne se recoupent pas.
 */
export type Pays = "BDPM" | "SWISSMEDIC";

interface PaysContextValue {
  pays: Pays;
  setPays: (pays: Pays) => void;
}

const PaysContext = createContext<PaysContextValue | undefined>(undefined);
const CLE_STOCKAGE = "gm_pays";

function paysInitial(): Pays {
  const stocke = localStorage.getItem(CLE_STOCKAGE) as Pays | null;
  return stocke === "SWISSMEDIC" ? "SWISSMEDIC" : "BDPM";
}

export function PaysProvider({ children }: { children: ReactNode }) {
  const [pays, setPays] = useState<Pays>(paysInitial);

  useEffect(() => {
    localStorage.setItem(CLE_STOCKAGE, pays);
  }, [pays]);

  return <PaysContext.Provider value={{ pays, setPays }}>{children}</PaysContext.Provider>;
}

export function usePays() {
  const contexte = useContext(PaysContext);
  if (!contexte) throw new Error("usePays doit être utilisé dans un PaysProvider");
  return contexte;
}
