export interface NoteMedicale {
  id: string;
  patient: string;
  categorie: "allergie" | "antecedent" | "observation";
  contenu: string;
  saisi_par_email: string | null;
  date_creation: string;
}

export interface PatientMedecin {
  id: string;
  patient: string;
  medecin: string;
  medecin_email: string;
  actif: boolean;
  date_debut: string;
  date_fin: string | null;
}

export interface Patient {
  id: string;
  utilisateur: string;
  utilisateur_email: string;
  utilisateur_prenom: string;
  utilisateur_nom: string;
  numero_dossier: string;
  date_naissance: string;
  sexe: "F" | "M" | "A";
  contact_urgence_nom: string;
  contact_urgence_telephone: string;
  contact_urgence_lien: string;
  notes_medicales: NoteMedicale[];
  date_creation: string;
  date_modification: string;
}

/**
 * Compte utilisateur tel que renvoyé par /api/v1/utilisateurs/ — endpoint
 * réservé aux admins (EstAdmin sur toutes les actions, y compris la
 * lecture). Un médecin ne peut donc pas parcourir cette liste.
 */
export interface UtilisateurCompte {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "medecin" | "patient" | "sans_role";
  actif: boolean;
  date_creation: string;
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
