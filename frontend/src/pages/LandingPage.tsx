import { Link } from "react-router-dom";
import { Users, Briefcase } from "lucide-react";
import { accessToken, clearAccessToken } from "../api";
import { AdminAccessTokenForm } from "../organisms/AdminAccessTokenForm";

export function LandingPage() {
  const signedIn = Boolean(accessToken());

  const signOut = () => {
    clearAccessToken();
    window.location.assign("/");
  };

  return (
    <div className="landing-page">
      <div className="landing-inner">
        <img src="/logo-horizontal.png" alt="Ashen" className="landing-logo" />
        <p className="landing-tagline">
          {signedIn ? "Elige un área de trabajo" : "Inicia sesión para continuar"}
        </p>

        {!signedIn && (
          <AdminAccessTokenForm hint="La sesión queda en esta pestaña. El rol lo asigna Supabase en app_metadata." />
        )}

        {signedIn && (
          <>
            <div className="landing-actions">
              <Link to="/leads" className="landing-card landing-card-leads">
                <Users size={40} strokeWidth={1.75} aria-hidden />
                <span className="landing-card-title">Leads</span>
                <span className="landing-card-desc">
                  Captación, mapa, revisión rápida y pipeline de prospectos
                </span>
              </Link>
              <Link to="/clientes" className="landing-card landing-card-clients">
                <Briefcase size={40} strokeWidth={1.75} aria-hidden />
                <span className="landing-card-title">Clientes</span>
                <span className="landing-card-desc">
                  Cotizaciones, reuniones, pagos, desarrollo y entrega
                </span>
              </Link>
            </div>
            <button type="button" className="btn-secondary landing-signout" onClick={signOut}>
              Cerrar sesión
            </button>
          </>
        )}
      </div>
    </div>
  );
}
