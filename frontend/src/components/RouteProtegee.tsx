import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function RouteProtegee({ children }: { children: React.ReactNode }) {
  const { utilisateur, chargement } = useAuth();

  if (chargement) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[var(--muted)]">
        Chargement...
      </div>
    );
  }
  if (!utilisateur) {
    return <Navigate to="/connexion" replace />;
  }
  return <>{children}</>;
}
