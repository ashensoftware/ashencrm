import { StatsPanel } from "./StatsPanel";
import { OptionsPanel } from "./OptionsPanel";
import { RegistryPanel } from "./RegistryPanel";
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
  onCategoryManage: () => void;
  onTinderNext?: () => void;
  onScrape: () => void;
}

export function Sidebar({
  prospects,
  stats,
  catalog,
  filters,
  selectedProspect,
  currentView,
  onViewChange,
  scrapeFormOpen,
  registrySearch,
  onFiltersChange,
  onSelectProspect,
  onScrapeFormToggle,
  onRegistrySearchChange,
  onCategoryManage,
  onScrape,
}: Props) {
  return (
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
          <LayoutDashboard size={18} /> Panel y Filtros
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

      {currentView === 'panel' && (
        <OptionsPanel
          filters={filters}
          onFiltersChange={onFiltersChange}
          catalog={catalog}
          optionsOpen={true}
          onOptionsToggle={() => {}}
          onCategoryManage={onCategoryManage}
        />
      )}

      {currentView === 'map' && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <button className="btn-secondary" onClick={onScrapeFormToggle} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <Search size={18} /> Scrapear Nueva Área
            </button>
            {scrapeFormOpen && (
              <div className="scrape-form-horizontal" style={{ marginTop: '1rem' }}>
                <div className="scrape-input-group" style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <select id="scrape-category" style={{ flex: 1 }}>
                    <option value="*">Todas las Categorías</option>
                    {catalog.map((c) => (
                      <option key={c.name} value={c.name}>{c.label}</option>
                    ))}
                  </select>
                  <input type="number" id="scrape-limit" defaultValue={20} min={1} max={500} style={{ width: '80px' }} />
                </div>
                <button className="btn-primary" onClick={onScrape} style={{ width: '100%' }}>
                  Iniciar Scrape
                </button>
              </div>
            )}
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <RegistryPanel
              prospects={prospects}
              search={registrySearch}
              onSearchChange={onRegistrySearchChange}
              selectedProspect={selectedProspect}
              onSelect={onSelectProspect}
              open={true}
              onToggle={() => {}}
            />
          </div>
        </div>
      )}
    </aside>
  );
}
