import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

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
        className={`relative w-full ${largeur} bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] border border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] rounded-xl shadow-xl max-h-[90vh] overflow-y-auto`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]">
          <h2 id="modal-titre" className="font-[var(--font-display)] text-lg font-semibold">
            {titre}
          </h2>
          <button
            onClick={onFermer}
            aria-label="Fermer"
            className="text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)] hover:text-current transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
