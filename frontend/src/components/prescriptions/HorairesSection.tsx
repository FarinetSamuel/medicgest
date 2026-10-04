import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { AlertTriangle, Pencil, Plus } from "lucide-react";
import { api } from "../../lib/api";
import { champClasse } from "../../lib/ui";
import type { HoraireProgramme } from "../../types";

type UniteRythme = "jours" | "semaines";

// Le backend ne stocke qu'un nombre de jours (intervalle_jours) : un
// multiple de 7 est présenté en semaines, le reste en jours.
function decomposerIntervalle(intervalleJours: number): { nombre: number; unite: UniteRythme } {
  return intervalleJours % 7 === 0
    ? { nombre: intervalleJours / 7, unite: "semaines" }
    : { nombre: intervalleJours, unite: "jours" };
}

function intervalleEnJours(nombre: string, unite: UniteRythme): number {
  return Number(nombre) * (unite === "semaines" ? 7 : 1);
}

// Date locale (et non UTC, qui décalerait d'un jour en soirée/nuit).
function dateLocaleISO(date: Date): string {
  const mois = String(date.getMonth() + 1).padStart(2, "0");
  const jour = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${mois}-${jour}`;
}

/** Ex. « tous les 2 jours », « toutes les 2 semaines (le lundi) » ; null si quotidien. */
function libelleRythme(horaire: HoraireProgramme, dateDebut: string): string | null {
  if (horaire.intervalle_jours === 1) return null;
  const { nombre, unite } = decomposerIntervalle(horaire.intervalle_jours);
  if (unite === "jours") return `tous les ${nombre} jours`;
  const reference = new Date(`${horaire.date_reference ?? dateDebut}T00:00:00`);
  const jourSemaine = reference.toLocaleDateString("fr-FR", { weekday: "long" });
  const rythme = nombre === 1 ? "toutes les semaines" : `toutes les ${nombre} semaines`;
  return `${rythme} (le ${jourSemaine})`;
}

function ChampsRythme({
  nombre,
  unite,
  dateReference,
  onNombre,
  onUnite,
  onDateReference,
}: {
  nombre: string;
  unite: UniteRythme;
  dateReference: string;
  onNombre: (valeur: string) => void;
  onUnite: (valeur: UniteRythme) => void;
  onDateReference: (valeur: string) => void;
}) {
  return (
    <>
      <div>
        <label className="block text-xs mb-1">Tous les</label>
        <div className="flex gap-1">
          <input
            required
            type="number"
            step="1"
            min="1"
            max={unite === "semaines" ? 52 : 365}
            value={nombre}
            onChange={(e) => onNombre(e.target.value)}
            aria-label="Nombre de jours ou de semaines entre deux prises"
            className={`${champClasse} py-1.5 w-16`}
          />
          <select
            value={unite}
            onChange={(e) => onUnite(e.target.value as UniteRythme)}
            aria-label="Unité du rythme"
            className={`${champClasse} py-1.5 w-28`}
          >
            <option value="jours">jour(s)</option>
            <option value="semaines">semaine(s)</option>
          </select>
        </div>
      </div>
      {/* Sans objet pour un horaire quotidien : chaque jour est un jour de prise. */}
      {intervalleEnJours(nombre, unite) > 1 && (
        <div>
          <label className="block text-xs mb-1">Première prise le</label>
          <input
            required
            type="date"
            value={dateReference}
            onChange={(e) => onDateReference(e.target.value)}
            className={`${champClasse} py-1.5`}
          />
        </div>
      )}
    </>
  );
}

export function HorairesSection({
  prescriptionId,
  horaires,
  doseQuantiteDefaut,
  dateDebut,
  peutModifier,
  onHoraireAjoute,
  onHoraireModifie,
}: {
  prescriptionId: string;
  horaires: HoraireProgramme[];
  doseQuantiteDefaut: string;
  dateDebut: string;
  peutModifier: boolean;
  onHoraireAjoute: (horaire: HoraireProgramme) => void;
  onHoraireModifie: (horaire: HoraireProgramme) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [heure, setHeure] = useState("08:00");
  // Pré-rempli avec la dose de la prescription : c'est la quantité de
  // l'horaire (et non dose_quantite) qui est recopiée dans les prises
  // générées, donc décomptée du stock et affichée dans les rappels.
  const [quantite, setQuantite] = useState(String(Number(doseQuantiteDefaut)));
  // Rythme : quotidien par défaut. La première prise proposée est
  // aujourd'hui, ou le début de la prescription s'il est à venir.
  const aujourdhui = dateLocaleISO(new Date());
  const dateReferenceDefaut = dateDebut > aujourdhui ? dateDebut : aujourdhui;
  const [nombre, setNombre] = useState("1");
  const [unite, setUnite] = useState<UniteRythme>("jours");
  const [dateReference, setDateReference] = useState(dateReferenceDefaut);
  const [enCours, setEnCours] = useState(false);

  const [horaireEnEdition, setHoraireEnEdition] = useState<string | null>(null);
  const [heureEdition, setHeureEdition] = useState("");
  const [quantiteEdition, setQuantiteEdition] = useState("");
  const [nombreEdition, setNombreEdition] = useState("1");
  const [uniteEdition, setUniteEdition] = useState<UniteRythme>("jours");
  const [dateReferenceEdition, setDateReferenceEdition] = useState(dateReferenceDefaut);
  const [enregistrementEnCours, setEnregistrementEnCours] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setEnCours(true);
    const intervalleJours = intervalleEnJours(nombre, unite);
    try {
      const { data } = await api.post<HoraireProgramme>("/horaires-programmes/", {
        prescription: prescriptionId,
        heure,
        quantite,
        intervalle_jours: intervalleJours,
        date_reference: intervalleJours > 1 ? dateReference : null,
        actif: true,
      });
      onHoraireAjoute(data);
      setOuvert(false);
      toast.success("Horaire ajouté");
    } catch {
      toast.error("Impossible d'ajouter cet horaire");
    } finally {
      setEnCours(false);
    }
  }

  async function basculerActif(horaire: HoraireProgramme) {
    try {
      const { data } = await api.patch<HoraireProgramme>(`/horaires-programmes/${horaire.id}/`, {
        actif: !horaire.actif,
      });
      onHoraireModifie(data);
    } catch {
      toast.error("Impossible de modifier cet horaire");
    }
  }

  function commencerEdition(horaire: HoraireProgramme) {
    setHoraireEnEdition(horaire.id);
    setHeureEdition(horaire.heure.slice(0, 5));
    setQuantiteEdition(horaire.quantite);
    const rythme = decomposerIntervalle(horaire.intervalle_jours);
    setNombreEdition(String(rythme.nombre));
    setUniteEdition(rythme.unite);
    setDateReferenceEdition(horaire.date_reference ?? dateReferenceDefaut);
  }

  function annulerEdition() {
    setHoraireEnEdition(null);
  }

  async function enregistrerEdition(e: FormEvent, horaire: HoraireProgramme) {
    e.preventDefault();
    setEnregistrementEnCours(true);
    const intervalleJours = intervalleEnJours(nombreEdition, uniteEdition);
    try {
      const { data } = await api.patch<HoraireProgramme>(`/horaires-programmes/${horaire.id}/`, {
        heure: heureEdition,
        quantite: quantiteEdition,
        intervalle_jours: intervalleJours,
        date_reference: intervalleJours > 1 ? dateReferenceEdition : null,
      });
      onHoraireModifie(data);
      setHoraireEnEdition(null);
      toast.success("Horaire modifié");
    } catch {
      toast.error("Impossible de modifier cet horaire");
    } finally {
      setEnregistrementEnCours(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Horaires
        </h4>
        {peutModifier && !ouvert && (
          <button
            onClick={() => setOuvert(true)}
            className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent)] hover:underline"
          >
            <Plus size={14} /> Ajouter
          </button>
        )}
      </div>

      {ouvert && (
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2 mb-2">
          <div>
            <label className="block text-xs mb-1">Heure</label>
            <input
              required
              type="time"
              value={heure}
              onChange={(e) => setHeure(e.target.value)}
              className={`${champClasse} py-1.5`}
            />
          </div>
          <div>
            <label className="block text-xs mb-1">Quantité</label>
            <input
              required
              type="number"
              step="1"
              min="0"
              value={quantite}
              onChange={(e) => setQuantite(e.target.value)}
              className={`${champClasse} py-1.5 w-24`}
            />
          </div>
          <ChampsRythme
            nombre={nombre}
            unite={unite}
            dateReference={dateReference}
            onNombre={setNombre}
            onUnite={setUnite}
            onDateReference={setDateReference}
          />
          <button
            type="submit"
            disabled={enCours}
            className="text-xs px-3 py-1.5 rounded-[var(--radius-control)] bg-[var(--cta)] text-[var(--cta-ink)] hover:brightness-95 disabled:opacity-60"
          >
            Ajouter
          </button>
          <button
            type="button"
            onClick={() => setOuvert(false)}
            className="text-xs px-2 py-1.5 text-[var(--muted)]"
          >
            Annuler
          </button>
        </form>
      )}

      {horaires.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">
          Aucun horaire défini.
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {horaires.map((h) =>
            horaireEnEdition === h.id ? (
              <form
                key={h.id}
                onSubmit={(e) => enregistrerEdition(e, h)}
                className="flex flex-wrap items-end gap-2 border border-[var(--hairline)] rounded-[var(--radius-control)] p-2"
              >
                <div>
                  <label className="block text-xs mb-1">Heure</label>
                  <input
                    required
                    type="time"
                    value={heureEdition}
                    onChange={(e) => setHeureEdition(e.target.value)}
                    className={`${champClasse} py-1.5`}
                  />
                </div>
                <div>
                  <label className="block text-xs mb-1">Quantité</label>
                  <input
                    required
                    type="number"
                    step="1"
                    min="0"
                    value={quantiteEdition}
                    onChange={(e) => setQuantiteEdition(e.target.value)}
                    className={`${champClasse} py-1.5 w-24`}
                  />
                </div>
                <ChampsRythme
                  nombre={nombreEdition}
                  unite={uniteEdition}
                  dateReference={dateReferenceEdition}
                  onNombre={setNombreEdition}
                  onUnite={setUniteEdition}
                  onDateReference={setDateReferenceEdition}
                />
                <button
                  type="submit"
                  disabled={enregistrementEnCours}
                  className="text-xs px-3 py-1.5 rounded-[var(--radius-control)] bg-[var(--cta)] text-[var(--cta-ink)] hover:brightness-95 disabled:opacity-60"
                >
                  Enregistrer
                </button>
                <button
                  type="button"
                  onClick={annulerEdition}
                  className="text-xs px-2 py-1.5 text-[var(--muted)]"
                >
                  Annuler
                </button>
              </form>
            ) : (
              <div
                key={h.id}
                className={`flex items-center gap-1 text-xs pl-2.5 pr-1 py-1 rounded-full border ${
                  h.actif
                    ? "border-[var(--cta)] text-[var(--accent)]"
                    : "border-[var(--hairline)] text-[var(--muted)]"
                }`}
              >
                <button
                  onClick={() => peutModifier && basculerActif(h)}
                  disabled={!peutModifier}
                  title={peutModifier ? "Cliquer pour activer/désactiver" : undefined}
                  className={h.actif ? "" : "line-through"}
                >
                  {h.heure.slice(0, 5)} · {h.quantite}
                  {libelleRythme(h, dateDebut) && ` · ${libelleRythme(h, dateDebut)}`}
                </button>
                {/* C'est la quantité de l'horaire (et non la dose de la
                    prescription) qui est recopiée dans les prises : rappels
                    et décompte du stock. Un écart est signalé, jamais corrigé
                    automatiquement — il peut être voulu (ex. 2 le matin, 1 le soir). */}
                {Number(h.quantite) !== Number(doseQuantiteDefaut) && (
                  <span
                    title={`Quantité de l'horaire (${Number(h.quantite)}) différente de la dose prescrite (${Number(doseQuantiteDefaut)}) : c'est ${Number(h.quantite)} qui sera rappelé et décompté du stock.`}
                    aria-label="Quantité différente de la dose prescrite"
                    className="text-[var(--statut-rupture)]"
                  >
                    <AlertTriangle size={12} />
                  </span>
                )}
                {peutModifier && (
                  <button
                    onClick={() => commencerEdition(h)}
                    aria-label="Modifier l'heure, la quantité ou le rythme"
                    title="Modifier l'heure, la quantité ou le rythme"
                    className="p-1 rounded-full hover:bg-black/5 dark:hover:bg-white/10"
                  >
                    <Pencil size={11} />
                  </button>
                )}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
