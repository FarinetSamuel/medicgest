export function PageAVenir({ titre }: { titre: string }) {
  return (
    <div>
      <h1 className="font-[var(--font-display)] text-2xl font-semibold mb-2">{titre}</h1>
      <p className="text-sm text-[var(--color-muted-light)] dark:text-[var(--color-muted-dark)]">
        Cette section sera construite lors d'une prochaine étape. La structure de
        navigation, l'authentification et le thème clair/sombre sont en place ;
        chaque section métier viendra s'y brancher une par une.
      </p>
    </div>
  );
}
