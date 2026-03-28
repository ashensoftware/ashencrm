import { NavLink, Link } from "react-router-dom";
import { Activity, Map, LayoutDashboard, KanbanSquare, Settings, Home } from "lucide-react";

const navBtn = ({ isActive }: { isActive: boolean }) =>
  `${isActive ? "btn-primary" : "btn-secondary"} clients-sidebar-nav`;

export function ClientsSidebar() {
  return (
    <aside className="sidebar clients-sidebar">
      <header className="sidebar-header-brand">
        <Link to="/" className="sidebar-logo-link" aria-label="Ir a inicio">
          <img src="/logo-horizontal.png" alt="Ashen" className="sidebar-logo-img" />
        </Link>
        <NavLink to="/" className="sidebar-inicio-link" end>
          <Home size={16} strokeWidth={2.25} aria-hidden />
          Inicio
        </NavLink>
      </header>

      <nav className="clients-sidebar-nav-block" aria-label="Navegación clientes">
        <NavLink to="/clientes" end className={navBtn}>
          <Activity size={18} />
          Resumen
        </NavLink>
        <NavLink to="/clientes/mapa" className={navBtn}>
          <Map size={18} />
          Mapa de cuentas
        </NavLink>
        <NavLink to="/clientes/gestion" className={navBtn}>
          <LayoutDashboard size={18} />
          Gestión de clientes
        </NavLink>
        <NavLink to="/clientes/pipeline" className={navBtn}>
          <KanbanSquare size={18} />
          Pipeline
        </NavLink>
        <NavLink to="/clientes/admin" className={navBtn}>
          <Settings size={18} />
          Parámetros
        </NavLink>
      </nav>

      <p className="clients-sidebar-footnote">
        Área de clientes: cotizaciones, entregas y parámetros propios (independiente de leads).
      </p>
    </aside>
  );
}
