import { useEffect, useState } from "react";
import { Pill, Package, Bell, AlertTriangle } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { StatusBadge } from "../components/StatusBadge";
import type { Boite, Notification, PageResultat, Prise } from "../types";

function CarteResume({
  icone: Icone, titre, valeur, ton,
}: { icone: React.ElementType; titre: string; valeur: number; ton: "danger" | "warning" | "muted" }) {
  return (
    <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">{titre}</span>
        <Icone size={18} className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]" />
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span className="font-[var(--font-display)] text-3xl font-semibold">{valeur}</span>
        {valeur > 0 && ton !== "muted" && <StatusBadge ton={ton}>à traiter</StatusBadge>}
      </div>
    </div>
  );
}

export function Dashboard() {
  const { utilisateur } = useAuth();
  const [prisesAttendues, setPrisesAttendues] = useState<Prise[]>([]);
  const [boitesEnAlerte, setBoitesEnAlerte] = useState<Boite[]>([]);
  const [notificationsNonLues, setNotificationsNonLues] = useState<Notification[]>([]);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    async function charger() {
      const [prisesRes, boitesRes, notifsRes] = await Promise.all([
        api.get<PageResultat<Prise>>("/prises/"),
        api.get<PageResultat<Boite>>("/boites/"),
        api.get<PageResultat<Notification>>("/notifications/"),
      ]);
      setPrisesAttendues(prisesRes.data.results.filter((p) => p.statut === "attendue"));
      setBoitesEnAlerte(boitesRes.data.results.filter((b) => b.en_alerte));
      setNotificationsNonLues(
        notifsRes.data.results.filter((n) => n.canal === "in_app" && n.statut !== "lue")
      );
      setChargement(false);
    }
    charger();
  }, []);

  if (chargement) {
    return <p className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">Chargement...</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[var(--font-display)] text-2xl font-semibold">
          Bonjour {utilisateur?.prenom || utilisateur?.email}
        </h1>
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
          Voici un résumé de la situation actuelle.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <CarteResume icone={Pill} titre="Prises à venir" valeur={prisesAttendues.length} ton="muted" />
        <CarteResume icone={Package} titre="Alertes de stock" valeur={boitesEnAlerte.length} ton="warning" />
        <CarteResume icone={Bell} titre="Notifications non lues" valeur={notificationsNonLues.length} ton="muted" />
      </div>

      {boitesEnAlerte.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle size={16} className="text-[var(--color-warning)]" />
            Stock à surveiller
          </h2>
          <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl divide-y divide-[var(--color-border-light)] dark:divide-[var(--color-border-dark)]">
            {boitesEnAlerte.map((boite) => (
              <div key={boite.id} className="px-4 py-3 flex items-center justify-between text-sm">
                <span>{boite.medicament_nom}</span>
                <span className="flex items-center gap-3">
                  <span className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
                    {boite.quantite_restante} restant(s)
                  </span>
                  <StatusBadge ton="warning">Stock bas</StatusBadge>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {prisesAttendues.length === 0 && boitesEnAlerte.length === 0 && notificationsNonLues.length === 0 && (
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
          Rien à signaler pour le moment.
        </p>
      )}
    </div>
  );
}
