import { StatsPanel } from "./StatsPanel";

import type { Prospect } from "../types";
import type { ProspectFilters } from "../types";
import type { CatalogItem } from "../types";
import { Map, Flame, LayoutDashboard, Search, ClipboardList, Activity } from "lucide-react";

interface Props {
  prospects: Prospect[];
  stats: Record<string, number>;
  catalog: CatalogItem[];
  filters: ProspectFilters;
  selectedProspect: Prospect | null;
  currentView: "overview" | "map" | "tinder" | "panel" | "todo";
  onViewChange: (v: "overview" | "map" | "tinder" | "panel" | "todo") => void;
  optionsOpen?: boolean;
  registryOpen?: boolean;
  scrapeFormOpen: boolean;
  registrySearch: string;
  onFiltersChange: (f: ProspectFilters) => void;
  onSelectProspect: (p: Prospect) => void;
  onOptionsToggle?: () => void;
  onRegistryToggle?: () => void;
  onScrapeFormToggle: () => void;
  onRegistrySearchChange: (v: string) => void;
  onTinderNext?: () => void;
  onScrape: () => void;
}

import { createPortal } from "react-dom";

export function Sidebar({
  stats,
  catalog,
  filters,
  currentView,
  onViewChange,
  scrapeFormOpen,
  onFiltersChange,
  onScrapeFormToggle,
  onScrape,
}: Props) {
  return (
    <>
    <aside className="sidebar">
      <header>
        <img src="/logo-horizontal.png" alt="Ashen" style={{ height: '32px', filter: 'brightness(0) invert(1)' }} />
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1rem', borderBottom: '1px solid var(--border)' }}>
        <button 
          className={currentView === 'overview' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => onViewChange('overview')}
          style={{ width: '100%', justifyContent: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Activity size={18} /> Resumen / Dashboard
        </button>
        <button 
          className={currentView === 'map' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => onViewChange('map')}
          style={{ width: '100%', justifyContent: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Map size={18} /> Explorar Mapa
        </button>
        <button 
          className={currentView === 'tinder' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => onViewChange('tinder')}
          style={{ width: '100%', justifyContent: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Flame size={18} /> Revisión Rápida
        </button>
        <button 
          className={currentView === 'panel' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => onViewChange('panel')}
          style={{ width: '100%', justifyContent: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <LayoutDashboard size={18} /> Gestión de Leads
        </button>
        <button 
          className={currentView === 'todo' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => onViewChange('todo')}
          style={{ width: '100%', justifyContent: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <ClipboardList size={18} /> En Progreso
        </button>
      </div>

      <StatsPanel
        stats={stats}
        filters={filters}
        onFilterChange={(status) => onFiltersChange({ ...filters, status })}
      />

      {currentView === 'map' && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <button className="btn-secondary" onClick={onScrapeFormToggle} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <Search size={18} /> Scrapear Área En Mapa
            </button>
          </div>
        </div>
      )}
    </aside>
    
    {scrapeFormOpen && createPortal(
      <div className="modal fade-in-scale" onClick={onScrapeFormToggle} style={{ zIndex: 9999 }}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '420px', width: '90%', padding: '2rem', background: 'var(--bg-base)', borderRadius: '16px', border: '1px solid var(--border)', boxShadow: '0 20px 40px rgba(0,0,0,0.4)' }}>
          <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: 'none', paddingBottom: '0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ background: 'var(--accent-muted)', color: 'var(--accent)', padding: '0.5rem', borderRadius: '8px', display: 'flex' }}>
                 <Search size={24} />
              </div>
              <div>
                <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '1.2rem' }}>Configurar Búsqueda</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Mueve el mapa para definir la zona</span>
              </div>
            </div>
            <button className="close-btn" onClick={onScrapeFormToggle} style={{ alignSelf: 'flex-start' }}>×</button>
          </header>
          
          <div className="scrape-form-horizontal">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '2rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Categoría Principal</label>
                <select id="scrape-category" className="dialog-input" style={{ width: '100%', padding: '0.85rem' }}>
                  <option value="*">⚡ Todas las Categorías ⚡</option>
                  {catalog.map((c) => (
                    <option key={c.name} value={c.name}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Límite Máximo (Leads)</label>
                <input type="number" id="scrape-limit" className="dialog-input" defaultValue={20} min={1} max={500} style={{ width: '100%', padding: '0.85rem' }} />
              </div>
            </div>
            <button className="btn-primary" onClick={() => { onScrapeFormToggle(); onScrape(); }} style={{ width: '100%', padding: '1rem', fontSize: '1rem', fontWeight: 600, display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
              <Search size={20} /> Iniciar Rastreo Ahora
            </button>
          </div>
        </div>
      </div>,
      document.body
    )}
    </>
  );
}
