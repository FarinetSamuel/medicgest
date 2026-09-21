import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Logo } from "../components/Logo";

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
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] text-[var(--ink)] px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Logo size={56} wordmark="full" className="justify-center" />
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[var(--surface)] border border-[var(--hairline)] rounded-[var(--radius-card)] p-6 space-y-4"
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
              className="w-full rounded-[var(--radius-control)] border border-[var(--hairline)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
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
              className="w-full rounded-[var(--radius-control)] border border-[var(--hairline)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            />
          </div>

          {erreur && (
            <p className="text-sm text-[var(--statut-rupture)]" role="alert">{erreur}</p>
          )}

          <button
            type="submit"
            disabled={enCours}
            className="w-full rounded-[var(--radius-control)] bg-[var(--cta)] text-[var(--cta-ink)] text-sm font-medium py-2.5 hover:brightness-95 transition-colors disabled:opacity-60"
          >
            {enCours ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
