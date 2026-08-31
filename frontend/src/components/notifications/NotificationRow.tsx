import { Bell, Mail, MessageSquare, PackageX, AlertCircle } from "lucide-react";
import { StatusBadge } from "../StatusBadge";
import type { Notification } from "../../types";

const CANAUX: Record<Notification["canal"], { label: string; icone: typeof Mail }> = {
  email: { label: "E-mail", icone: Mail },
  sms: { label: "SMS", icone: MessageSquare },
  in_app: { label: "Application", icone: Bell },
};

const CATEGORIES: Record<Notification["categorie"], { label: string; icone: typeof PackageX }> = {
  rappel_prise: { label: "Rappel de prise", icone: Bell },
  alerte_stock: { label: "Alerte de stock", icone: PackageX },
  autre: { label: "Autre", icone: AlertCircle },
};

const STATUTS: Record<Notification["statut"], { label: string; ton: "danger" | "warning" | "success" | "muted" }> = {
  en_attente: { label: "En attente", ton: "muted" },
  envoyee: { label: "Envoyée", ton: "success" },
  echec: { label: "Échec", ton: "danger" },
  lue: { label: "Lue", ton: "muted" },
};

export function NotificationRow({
  notification,
  onMarquerLue,
}: {
  notification: Notification;
  onMarquerLue: (notification: Notification) => void;
}) {
  const canal = CANAUX[notification.canal];
  const categorie = CATEGORIES[notification.categorie];
  const nonLue = notification.canal === "in_app" && notification.statut !== "lue";

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 border-b border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] last:border-b-0 ${
        nonLue ? "bg-[var(--color-brand-50)] dark:bg-white/5" : ""
      }`}
    >
      <div className="mt-0.5 shrink-0 text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
        <categorie.icone size={18} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <p className={`text-sm ${nonLue ? "font-semibold" : "font-medium"}`}>{notification.titre}</p>
          <span className="text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] shrink-0">
            {new Date(notification.date_creation).toLocaleString("fr-FR")}
          </span>
        </div>
        <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-0.5">
          {notification.message}
        </p>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className="inline-flex items-center gap-1 text-xs text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
            <canal.icone size={12} /> {canal.label}
          </span>
          <StatusBadge ton={STATUTS[notification.statut].ton}>{STATUTS[notification.statut].label}</StatusBadge>
          {nonLue && (
            <button
              onClick={() => onMarquerLue(notification)}
              className="text-xs font-medium text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)] hover:underline"
            >
              Marquer comme lue
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
