import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const CLE_ACCESS = "gm_access_token";
const CLE_REFRESH = "gm_refresh_token";

export const jetons = {
  lireAccess: () => localStorage.getItem(CLE_ACCESS),
  lireRefresh: () => localStorage.getItem(CLE_REFRESH),
  stocker(access: string, refresh: string) {
    localStorage.setItem(CLE_ACCESS, access);
    localStorage.setItem(CLE_REFRESH, refresh);
  },
  stockerAccess(access: string) {
    localStorage.setItem(CLE_ACCESS, access);
  },
  effacer() {
    localStorage.removeItem(CLE_ACCESS);
    localStorage.removeItem(CLE_REFRESH);
  },
};

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const access = jetons.lireAccess();
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

// Rafraîchissement automatique et silencieux du token d'accès expiré :
// une seule requête de refresh même si plusieurs appels échouent en
// même temps (file d'attente), pour éviter une rafale de refresh.
let rafraichissementEnCours: Promise<string | null> | null = null;

async function rafraichirToken(): Promise<string | null> {
  const refresh = jetons.lireRefresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, { refresh });
    jetons.stockerAccess(data.access);
    return data.access as string;
  } catch {
    jetons.effacer();
    return null;
  }
}

api.interceptors.response.use(
  (reponse) => reponse,
  async (erreur) => {
    const requeteOriginale = erreur.config;
    if (erreur.response?.status === 401 && !requeteOriginale._dejaRetentee) {
      requeteOriginale._dejaRetentee = true;

      if (!rafraichissementEnCours) {
        rafraichissementEnCours = rafraichirToken().finally(() => {
          rafraichissementEnCours = null;
        });
      }
      const nouvelAccess = await rafraichissementEnCours;
      if (nouvelAccess) {
        requeteOriginale.headers.Authorization = `Bearer ${nouvelAccess}`;
        return api(requeteOriginale);
      }
      window.location.href = "/connexion";
    }
    return Promise.reject(erreur);
  }
);
