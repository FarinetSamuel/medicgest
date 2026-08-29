export interface Patient {
  id: string;
  utilisateur_email: string;
  numero_dossier: string;
  date_naissance: string;
  sexe: string;
}

export interface Prise {
  id: string;
  prescription: string;
  statut: "attendue" | "prise" | "oubliee" | "reportee";
  date_heure_prevue: string | null;
  date_heure_reelle: string | null;
  quantite_prevue: string | null;
  quantite_prise: string | null;
  alerte_depassement: boolean;
}

export interface Boite {
  id: string;
  medicament_nom: string;
  quantite_restante: string;
  quantite_initiale: string;
  en_alerte: boolean;
  en_alerte_quantite: boolean;
  en_alerte_jours: boolean;
  jours_restants_estimes: number | null;
}

export interface Notification {
  id: string;
  canal: "email" | "sms" | "in_app";
  categorie: "rappel_prise" | "alerte_stock" | "autre";
  titre: string;
  message: string;
  statut: "en_attente" | "envoyee" | "echec" | "lue";
  date_creation: string;
}

export interface PageResultat<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
