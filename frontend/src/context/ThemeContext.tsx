import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  basculerTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
const CLE_STOCKAGE = "gm_theme";

function themeInitial(): Theme {
  const stocke = localStorage.getItem(CLE_STOCKAGE) as Theme | null;
  if (stocke === "light" || stocke === "dark") return stocke;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(themeInitial);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(CLE_STOCKAGE, theme);
  }, [theme]);

  const basculerTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  return <ThemeContext.Provider value={{ theme, basculerTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const contexte = useContext(ThemeContext);
  if (!contexte) throw new Error("useTheme doit être utilisé dans un ThemeProvider");
  return contexte;
}
