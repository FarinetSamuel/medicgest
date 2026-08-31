import { useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCheck } from "lucide-react";
import { api, recupererToutesPages } from "../lib/api";
import { NotificationRow } from "../components/notifications/NotificationRow";
import type { Notification } from "../types";

type Filtre = "toutes" | "non_lues" | Notification["categorie"];

/**
 * Le serializer n'expose pas `destinataire` — même un admin ne peut donc
 * pas distinguer à qui appartient une notification dans la liste globale
 * que lui renvoie son queryset non filtré. Cette page montre donc "mes
 * notifications" pour tous les rôles, y compris l'admin, plutôt qu'une
 * vue d'audit multi-comptes qui serait illisible sans cette information.
 */
export function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [chargement, setChargement] = useState(true);
  const [filtre, setFiltre] = useState<Filtre>("toutes");

  async function charger() {
    setChargement(true);
    try {
      const toutes = await recupererToutesPages<Notification>("/notifications/");
      setNotifications(toutes);
    } catch {
      toast.error("Impossible de charger les notifications");
    } finally {
      setChargement(false);
    }
  }

  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function marquerLue(notification: Notification) {
    try {
      const { data } = await api.patch<Notification>(`/notifications/${notification.id}/`, { statut: "lue" });
      setNotifications((liste) => liste.map((n) => (n.id === notification.id ? data : n)));
    } catch {
      toast.error("Impossible de marquer cette notification comme lue");
    }
  }

  async function toutMarquerLu() {
    const nonLues = notifications.filter((n) => n.canal === "in_app" && n.statut !== "lue");
    if (nonLues.length === 0) return;
    try {
      await Promise.all(nonLues.map((n) => api.patch(`/notifications/${n.id}/`, { statut: "lue" })));
      setNotifications((liste) =>
        liste.map((n) => (n.canal === "in_app" && n.statut !== "lue" ? { ...n, statut: "lue" } : n))
      );
      toast.success("Toutes les notifications ont été marquées comme lues");
    } catch {
      toast.error("Certaines notifications n'ont pas pu être marquées comme lues");
    }
  }

  const notificationsFiltrees = notifications.filter((n) => {
    if (filtre === "toutes") return true;
    if (filtre === "non_lues") return n.canal === "in_app" && n.statut !== "lue";
    return n.categorie === filtre;
  });

  const nombreNonLues = notifications.filter((n) => n.canal === "in_app" && n.statut !== "lue").length;

  const FILTRES: { valeur: Filtre; label: string }[] = [
    { valeur: "toutes", label: "Toutes" },
    { valeur: "non_lues", label: `Non lues${nombreNonLues > 0 ? ` (${nombreNonLues})` : ""}` },
    { valeur: "rappel_prise", label: "Rappels de prise" },
    { valeur: "alerte_stock", label: "Alertes de stock" },
    { valeur: "autre", label: "Autre" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-[var(--font-display)] text-2xl font-semibold">Notifications</h1>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
            Rappels de prise et alertes de stock.
          </p>
        </div>
        {nombreNonLues > 0 && (
          <button
            onClick={toutMarquerLu}
            className="inline-flex items-center gap-2 text-sm font-medium rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] px-3 py-2 hover:bg-black/5 dark:hover:bg-white/5 transition-colors shrink-0"
          >
            <CheckCheck size={16} /> Tout marquer comme lu
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTRES.map((f) => (
          <button
            key={f.valeur}
            onClick={() => setFiltre(f.valeur)}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
              filtre === f.valeur
                ? "bg-[var(--color-brand-500)] text-white border-[var(--color-brand-500)]"
                : "border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl overflow-hidden">
        {chargement ? (
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
            Chargement...
          </p>
        ) : notificationsFiltrees.length === 0 ? (
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] p-4">
            Aucune notification {filtre !== "toutes" ? "dans ce filtre" : "pour le moment"}.
          </p>
        ) : (
          notificationsFiltrees.map((n) => (
            <NotificationRow key={n.id} notification={n} onMarquerLue={marquerLue} />
          ))
        )}
      </div>
    </div>
  );
}
