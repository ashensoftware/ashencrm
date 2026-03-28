import { useState, useEffect } from "react";
import { useDebounce } from "../hooks/useDebounce";
import type { Prospect, ProspectFilters, CatalogItem } from "../types";
import { STATUS_OPTIONS, IG_OPTIONS, CONTACT_OPTIONS } from "../constants";
import { Plus, Edit2, ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  prospects: Prospect[];
  filters: ProspectFilters;
  catalog: CatalogItem[];
  onFiltersChange: (f: ProspectFilters) => void;
  onAddProspect: () => void;
  onSelectProspect: (p: Prospect) => void;
}

export function PanelPage({ prospects, filters, catalog, onFiltersChange, onAddProspect, onSelectProspect }: Props) {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  
  const [localSearch, setLocalSearch] = useState(filters.name || "");
  const debouncedSearch = useDebounce(localSearch, 400);

  useEffect(() => {
    if (debouncedSearch !== (filters.name || "")) {
      onFiltersChange({ ...filters, name: debouncedSearch });
    }
  }, [debouncedSearch]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, itemsPerPage]);

  const totalPages = Math.ceil(prospects.length / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedProspects = prospects.slice(startIndex, startIndex + itemsPerPage);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", backgroundColor: "var(--bg-base)", overflow: "hidden" }}>
      {/* Header & Actions */}
      <div style={{ padding: "1.5rem", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem", color: "white" }}>Gestión de Leads y Clientes</h1>
          <p style={{ margin: "0.25rem 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>Administra tu base de datos y agrega clientes manualmente ({prospects.length} resultados filtrados).</p>
        </div>
        <button className="btn-primary" onClick={onAddProspect} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Plus size={18} /> Añadir Manualmente
        </button>
      </div>

      {/* Filters Bar */}
      <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--border)", display: "flex", gap: "1rem", flexWrap: "wrap", backgroundColor: "var(--bg-elevated)", flexShrink: 0 }}>
        <div className="filter-group" style={{ flex: "1", minWidth: "150px" }}>
          <label>Buscador</label>
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por nombre..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
          />
        </div>
        <div className="filter-group" style={{ flex: "1", minWidth: "150px" }}>
          <label>Categoría</label>
          <select value={filters.category || ""} onChange={(e) => onFiltersChange({ ...filters, category: e.target.value })}>
            <option value="">Todas las Categorías</option>
            {catalog.map((c) => <option key={c.name} value={c.name}>{c.label}</option>)}
          </select>
        </div>
        <div className="filter-group" style={{ flex: "1", minWidth: "120px" }}>
          <label>Estado de Embudo</label>
          <select value={filters.status || ""} onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}>
            {STATUS_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="filter-group" style={{ flex: "1", minWidth: "120px" }}>
          <label>Instagram</label>
          <select value={filters.has_instagram || ""} onChange={(e) => onFiltersChange({ ...filters, has_instagram: e.target.value })}>
            {IG_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="filter-group" style={{ flex: "1", minWidth: "120px" }}>
          <label>Contactado</label>
          <select value={filters.contacted || ""} onChange={(e) => onFiltersChange({ ...filters, contacted: e.target.value })}>
            {CONTACT_OPTIONS.map((o) => <option key={o.value || "any"} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div style={{ flex: 1, overflow: "auto", position: "relative" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.9rem" }}>
          <thead style={{ boxShadow: "0 1px 0 var(--border)", position: "relative", zIndex: 10 }}>
            <tr>
              <th style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-elevated)", padding: "1rem 1.5rem", color: "var(--text-secondary)", fontWeight: 600 }}>Cliente</th>
              <th style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-elevated)", padding: "1rem", color: "var(--text-secondary)", fontWeight: 600 }}>Categoría</th>
              <th style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-elevated)", padding: "1rem", color: "var(--text-secondary)", fontWeight: 600 }}>Contacto</th>
              <th style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-elevated)", padding: "1rem", color: "var(--text-secondary)", fontWeight: 600 }}>Estado</th>
              <th style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-elevated)", padding: "1rem 1.5rem", color: "var(--text-secondary)", textAlign: "right", fontWeight: 600 }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {paginatedProspects.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>No hay clientes que coincidan con los filtros.</td></tr>
            ) : (
              paginatedProspects.map((p) => (
                <tr key={p.name} style={{ borderBottom: "1px solid var(--border)", transition: "background 0.2s" }} className="table-row-hover">
                  <td style={{ padding: "1rem 1.5rem", maxWidth: "250px", whiteSpace: "normal", wordBreak: "break-word" }}>
                    <div style={{ fontWeight: 600, color: "white" }}>{p.name}</div>
                    {p.city && <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{p.city}</div>}
                  </td>
                  <td style={{ padding: "1rem" }}>
                    <span className="p-status-tag" style={{ background: "rgba(255, 255, 255, 0.08)", color: "var(--text-secondary)" }}>{p.category}</span>
                  </td>
                  <td style={{ padding: "1rem", maxWidth: "180px", whiteSpace: "normal", wordBreak: "break-all" }}>
                    {p.phone && <div>📞 {p.phone}</div>}
                    {p.instagram_handle && <div>📸 @{p.instagram_handle}</div>}
                    {(!p.phone && !p.instagram_handle) && <span style={{ color: "var(--text-secondary)" }}>Sin info</span>}
                  </td>
                  <td style={{ padding: "1rem" }}>
                    <span className={`p-status-tag ${p.status}`}>{STATUS_OPTIONS.find(o => o.value === p.status)?.label || p.status}</span>
                  </td>
                  <td style={{ padding: "1rem 1.5rem", textAlign: "right" }}>
                    <button className="btn-secondary" style={{ padding: "0.5rem" }} onClick={() => onSelectProspect(p)} title="Ver/Editar Detalles">
                      <Edit2 size={16} /> Detalle
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {prospects.length > 0 && (
        <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "var(--bg-elevated)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Mostrando {startIndex + 1} a {Math.min(startIndex + itemsPerPage, prospects.length)} de {prospects.length} resultados
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Ver:</label>
              <select 
                value={itemsPerPage} 
                onChange={(e) => setItemsPerPage(Number(e.target.value))}
                style={{ padding: "0.25rem 0.5rem", borderRadius: "var(--radius-sm)", backgroundColor: "var(--bg-elevated)", border: "1px solid var(--border)", color: "white", fontSize: "0.85rem", cursor: "pointer" }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>
          
          {totalPages > 1 && (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button 
                className="btn-secondary" 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))} 
                disabled={currentPage === 1}
                style={{ padding: "0.4rem 0.75rem", display: "flex", alignItems: "center", opacity: currentPage === 1 ? 0.5 : 1 }}
              >
                <ChevronLeft size={16} /> Anterior
              </button>
              <span style={{ display: "flex", alignItems: "center", padding: "0 0.5rem", fontSize: "0.9rem", fontWeight: 600 }}>
                {currentPage} / {totalPages}
              </span>
              <button 
                className="btn-secondary" 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))} 
                disabled={currentPage === totalPages}
                style={{ padding: "0.4rem 0.75rem", display: "flex", alignItems: "center", opacity: currentPage === totalPages ? 0.5 : 1 }}
              >
                Siguiente <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
