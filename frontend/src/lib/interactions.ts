import type { InteractionDetectee } from "../types";

export const NIVEAUX: Record<
  InteractionDetectee["niveau"],
  { label: string; ton: "danger" | "warning" | "muted"; ordre: number }
> = {
  contre_indication: { label: "Contre-indication", ton: "danger", ordre: 0 },
  association_deconseillee: { label: "Association déconseillée", ton: "danger", ordre: 1 },
  precaution_emploi: { label: "Précaution d'emploi", ton: "warning", ordre: 2 },
  a_prendre_en_compte: { label: "À prendre en compte", ton: "muted", ordre: 3 },
};
