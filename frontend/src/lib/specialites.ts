export const SPECIALITES: { valeur: string; label: string }[] = [
  { valeur: "generale", label: "Médecine générale" },
  { valeur: "cardiologie", label: "Cardiologie" },
  { valeur: "dermatologie", label: "Dermatologie" },
  { valeur: "endocrinologie", label: "Endocrinologie" },
  { valeur: "gastroenterologie", label: "Gastro-entérologie" },
  { valeur: "gynecologie", label: "Gynécologie-obstétrique" },
  { valeur: "hematologie", label: "Hématologie" },
  { valeur: "neurologie", label: "Neurologie" },
  { valeur: "oncologie", label: "Oncologie" },
  { valeur: "ophtalmologie", label: "Ophtalmologie" },
  { valeur: "orl", label: "ORL" },
  { valeur: "pediatrie", label: "Pédiatrie" },
  { valeur: "pneumologie", label: "Pneumologie" },
  { valeur: "psychiatrie", label: "Psychiatrie" },
  { valeur: "rhumatologie", label: "Rhumatologie" },
  { valeur: "urologie", label: "Urologie" },
  { valeur: "autre", label: "Autre" },
];

export function libelleSpecialite(specialite: string, specialiteAutre: string): string {
  if (!specialite) return "";
  if (specialite === "autre") return specialiteAutre || "Autre";
  return SPECIALITES.find((s) => s.valeur === specialite)?.label ?? specialite;
}
