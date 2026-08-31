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
  horaire_programme: string | null;
  statut: "attendue" | "prise" | "oubliee" | "reportee";
  date_heure_prevue: string | null;
  date_heure_reelle: string | null;
  quantite_prevue: string | null;
  quantite_prise: string | null;
  enregistre_par: string | null;
  alerte_depassement: boolean;
  commentaire: string;
  date_creation: string;
  date_modification: string;
}

export interface HoraireProgramme {
  id: string;
  prescription: string;
  heure: string;
  quantite: string;
  actif: boolean;
}

/**
 * Référentiel BDPM, lecture seule. La recherche (?search=) ne fonctionnait
 * pas avant correction du backend (filter_backends manquant) — nécessaire
 * pour choisir un médicament parmi les 15 857 importés.
 */
export interface Medicament {
  id: string;
  code_cis: string;
  denomination: string;
  forme_pharmaceutique: string;
  dosage: string;
  laboratoire: string;
  code_atc: string;
  source: string;
  date_import: string;
}

export interface Prescription {
  id: string;
  patient: string;
  medicament: string;
  medicament_nom: string;
  medecin_prescripteur: string;
  type_prise: "reguliere" | "reserve";
  dose_quantite: string;
  dose_unite: string;
  frequence_par_jour: number | null;
  dose_max_par_jour: string | null;
  date_debut: string;
  date_fin: string | null;
  instructions: string;
  statut: "active" | "arretee" | "terminee";
  horaires: HoraireProgramme[];
  date_creation: string;
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
