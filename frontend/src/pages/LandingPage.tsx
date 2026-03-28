import { Link } from "react-router-dom";
import { Users, Briefcase } from "lucide-react";

export function LandingPage() {
  return (
    <div className="landing-page">
      <div className="landing-inner">
        <img src="/logo-horizontal.png" alt="Ashen" className="landing-logo" />
        <p className="landing-tagline">Elige un área de trabajo</p>
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
      </div>
    </div>
  );
}
