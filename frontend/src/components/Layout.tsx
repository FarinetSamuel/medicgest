import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, Pill, Package, Bell, AlertTriangle, UserCog,
  Moon, Sun, LogOut,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const LIENS = [
  { to: "/", label: "Tableau de bord", icone: LayoutDashboard, fin: true },
  { to: "/patients", label: "Patients", icone: Users },
  { to: "/prescriptions", label: "Prescriptions", icone: Pill },
  { to: "/stock", label: "Stock", icone: Package },
  { to: "/notifications", label: "Notifications", icone: Bell },
  { to: "/interactions", label: "Interactions", icone: AlertTriangle },
  { to: "/comptes", label: "Comptes", icone: UserCog, reserveAdmin: true },
];

export function Layout() {
  const { utilisateur, deconnexion } = useAuth();
  const { theme, basculerTheme } = useTheme();
  const navigate = useNavigate();

  function handleDeconnexion() {
    deconnexion();
    navigate("/connexion");
  }

  return (
    <div className="flex min-h-screen bg-[var(--color-bg-light)] dark:bg-[var(--color-bg-dark)] text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]">
      <aside className="w-64 shrink-0 border-r border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] flex flex-col">
        <div className="px-5 py-5 border-b border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]">
          <span className="font-[var(--font-display)] text-xl font-semibold text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)]">
            medicgest
          </span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {LIENS.filter((lien) => !lien.reserveAdmin || utilisateur?.role === "admin").map(
            ({ to, label, icone: Icone, fin }) => (
            <NavLink
              key={to}
              to={to}
              end={fin}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[var(--color-brand-500)] text-white"
                    : "text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5"
                }`
              }
            >
              <Icone size={18} />
              {label}
            </NavLink>
            )
          )}
        </nav>
        <div className="px-3 py-4 border-t border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] space-y-1">
          <button
            onClick={basculerTheme}
            className="w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            {theme === "light" ? "Thème sombre" : "Thème clair"}
          </button>
          <button
            onClick={handleDeconnexion}
            className="w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <LogOut size={18} />
            Déconnexion
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 border-b border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] flex items-center justify-end px-6">
          <div className="text-sm text-right">
            <div className="font-medium">{utilisateur?.prenom} {utilisateur?.nom}</div>
            <div className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] capitalize">
              {utilisateur?.role}
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
