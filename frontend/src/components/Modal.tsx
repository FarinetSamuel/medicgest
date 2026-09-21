import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { titreCarteClasse } from "../lib/ui";

export function Modal({
  titre,
  onFermer,
  children,
  largeur = "max-w-lg",
}: {
  titre: string;
  onFermer: () => void;
  children: ReactNode;
  largeur?: string;
}) {
  useEffect(() => {
    function surEchap(e: KeyboardEvent) {
      if (e.key === "Escape") onFermer();
    }
    window.addEventListener("keydown", surEchap);
    return () => window.removeEventListener("keydown", surEchap);
  }, [onFermer]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onFermer} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-titre"
        className={`relative w-full ${largeur} bg-[var(--surface)] border border-[var(--hairline)] rounded-[var(--radius-card)] max-h-[90vh] overflow-y-auto`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--hairline)]">
          <h2 id="modal-titre" className={titreCarteClasse}>
            {titre}
          </h2>
          <button
            onClick={onFermer}
            aria-label="Fermer"
            className="text-[var(--muted)] hover:text-current transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
