import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { RouteProtegee } from "./components/RouteProtegee";
import { Layout } from "./components/Layout";
import { Connexion } from "./pages/Connexion";
import { Dashboard } from "./pages/Dashboard";
import { Patients } from "./pages/Patients";
import { Prescriptions } from "./pages/Prescriptions";
import { Stock } from "./pages/Stock";
import { PageAVenir } from "./pages/PageAVenir";

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
          <Routes>
            <Route path="/connexion" element={<Connexion />} />
            <Route
              element={
                <RouteProtegee>
                  <Layout />
                </RouteProtegee>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/patients" element={<Patients />} />
              <Route path="/prescriptions" element={<Prescriptions />} />
              <Route path="/stock" element={<Stock />} />
              <Route path="/notifications" element={<PageAVenir titre="Notifications" />} />
              <Route path="/interactions" element={<PageAVenir titre="Interactions" />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
