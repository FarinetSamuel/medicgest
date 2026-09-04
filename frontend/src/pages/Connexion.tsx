import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

/**
 * Distingue la cause d'un échec de connexion plutôt que d'afficher
 * systématiquement "mot de passe incorrect" — une absence de réponse HTTP
 * (CORS, mauvaise URL d'API, serveur injoignable) était auparavant
 * indiscernable d'un vrai mauvais mot de passe, ce qui a fait perdre du
 * temps de diagnostic en production.
 */
function messageErreurConnexion(err: unknown): string {
  const reponse = (err as { response?: { status?: number; data?: unknown } })?.response;
  if (!reponse) {
    return "Impossible de contacter le serveur. Vérifiez votre connexion ou réessayez plus tard.";
  }
  if (reponse.status === 401) {
    return "Email ou mot de passe incorrect.";
  }
  const donnees = reponse.data as { non_field_errors?: string[] } | undefined;
  if (reponse.status === 400 && donnees?.non_field_errors?.length) {
    return donnees.non_field_errors[0];
  }
  return "Erreur du serveur, réessayez plus tard.";
}

export function Connexion() {
  const { connexion } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await connexion(email, motDePasse);
      toast.success("Connexion réussie");
      navigate("/");
    } catch (err) {
      setErreur(messageErreurConnexion(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-light)] dark:bg-[var(--color-bg-dark)] text-[var(--color-text-light)] dark:text-[var(--color-text-dark)] px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-[var(--font-display)] text-3xl font-semibold text-[var(--color-brand-600)] dark:text-[var(--color-brand-300)]">
            medicgest
          </h1>
          <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] mt-1">
            Gestion des médicaments
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium mb-1.5" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-500)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5" htmlFor="password">Mot de passe</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-500)]"
            />
          </div>

          {erreur && (
            <p className="text-sm text-[var(--color-danger)]" role="alert">{erreur}</p>
          )}

          <button
            type="submit"
            disabled={enCours}
            className="w-full rounded-lg bg-[var(--color-brand-500)] text-white text-sm font-medium py-2.5 hover:bg-[var(--color-brand-600)] transition-colors disabled:opacity-60"
          >
            {enCours ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
