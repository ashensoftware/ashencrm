import { useCallback, useEffect, useMemo, useState } from "react";
import { useDebounce } from "../hooks/useDebounce";
import type { CatalogItem, Client, ClientMeeting, Prospect } from "../types";
import {
  fetchClients,
  fetchClient,
  fetchCatalog,
  fetchProspects,
  createClientFromProspect,
} from "../api";
import { Plus, Edit2, ChevronLeft, ChevronRight, Building2 } from "lucide-react";
import { STAGE_COLUMNS, clientStageLabel } from "../constants/clientStages";
import { LeadImportCombobox } from "../organisms/LeadImportCombobox";
import { NewClientModal, ClientDetailModal } from "../organisms/modals/ClientModals";

export function ClientsManagementPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [localSearch, setLocalSearch] = useState("");
  const debouncedSearch = useDebounce(localSearch, 400);
  const [stageFilter, setStageFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const [newOpen, setNewOpen] = useState(false);
  const [importName, setImportName] = useState("");
  const [saving, setSaving] = useState(false);
  const [leadOptions, setLeadOptions] = useState<Prospect[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<(Client & { meetings: ClientMeeting[] }) | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const importableLeads = useMemo(() => {
    return leadOptions.filter((p) => {
      if (p.id == null) return true;
      return !clients.some((c) => c.prospect_id === p.id);
    });
  }, [leadOptions, clients]);

  const load = useCallback(async () => {
    setLoading(true);
    setNotice(null);
    try {
      setClients(await fetchClients());
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Error al cargar");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let cancelled = false;
    fetchProspects()
      .then((rows) => {
        if (!cancelled) setLeadOptions(rows);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchCatalog()
      .then((rows) => {
        if (!cancelled) setCatalog(rows);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    return clients.filter((c) => {
      if (stageFilter && c.stage !== stageFilter) return false;
      if (!q) return true;
      const name = (c.display_name || "").toLowerCase();
      const cat = (c.category || "").toLowerCase();
      const mail = (c.contact_email || "").toLowerCase();
      const phone = (c.phone || "").toLowerCase();
      return name.includes(q) || cat.includes(q) || mail.includes(q) || phone.includes(q);
    });
  }, [clients, debouncedSearch, stageFilter]);

  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearch, stageFilter, itemsPerPage]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const pageRows = filtered.slice(startIndex, startIndex + itemsPerPage);

  const openDetail = async (id: number) => {
    setSelectedId(id);
    setDetailLoading(true);
    setNotice(null);
    try {
      setDetail(await fetchClient(id));
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Error");
      setSelectedId(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const refreshDetail = async (id: number) => {
    try {
      const d = await fetchClient(id);
      setDetail(d);
      setClients(await fetchClients());
    } catch {
      /* ignore */
    }
  };

  return (
    <div
      className="clients-management-page"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "var(--bg-base)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "1.5rem",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          flexShrink: 0,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem", color: "white" }}>Gestión de clientes</h1>
          <p style={{ margin: "0.25rem 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
            Lista completa, búsqueda y edición de fichas ({filtered.length} resultado
            {filtered.length !== 1 ? "s" : ""}).
          </p>
        </div>
        <div className="clients-management-toolbar">
          <LeadImportCombobox
            prospects={importableLeads}
            value={importName}
            onSelectName={setImportName}
            disabled={saving}
          />
          <button
            type="button"
            className="btn-secondary clients-pipeline-toolbar-btn"
            disabled={!importName.trim() || saving}
            onClick={async () => {
              setSaving(true);
              setNotice(null);
              try {
                const c = await createClientFromProspect(importName.trim());
                setImportName("");
                await load();
                await openDetail(c.id);
              } catch (e) {
                setNotice(e instanceof Error ? e.message : "Error");
              } finally {
                setSaving(false);
              }
            }}
          >
            Importar desde lead
          </button>
          <button
            type="button"
            className="btn-primary clients-pipeline-toolbar-btn"
            onClick={() => setNewOpen(true)}
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            <Plus size={18} /> Nuevo cliente
          </button>
        </div>
      </div>

      <div
        style={{
          padding: "1rem 1.5rem",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
          backgroundColor: "var(--bg-elevated)",
          flexShrink: 0,
        }}
      >
        <div className="filter-group" style={{ flex: "1", minWidth: "160px" }}>
          <label>Buscador</label>
          <input
            type="text"
            className="search-input"
            placeholder="Nombre, categoría, email o teléfono…"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
          />
        </div>
        <div className="filter-group" style={{ flex: "0 1 200px", minWidth: "140px" }}>
          <label>Etapas del pipeline</label>
          <select
            className="search-input"
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
          >
            <option value="">Todas las etapas</option>
            {STAGE_COLUMNS.map((col) => (
              <option key={col.stage} value={col.stage}>
                {col.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {notice && (
        <div style={{ padding: "0.5rem 1.5rem", color: "var(--warning)", fontSize: "0.9rem", flexShrink: 0 }}>
          {notice}
        </div>
      )}

      <div style={{ flex: 1, overflow: "auto", position: "relative" }}>
        {loading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>Cargando…</div>
        ) : (
          <table
            style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.9rem" }}
          >
            <thead style={{ boxShadow: "0 1px 0 var(--border)", position: "relative", zIndex: 10 }}>
              <tr>
                <th
                  style={{
                    position: "sticky",
                    top: 0,
                    backgroundColor: "var(--bg-elevated)",
                    padding: "1rem 1.5rem",
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                  }}
                >
                  Cliente
                </th>
                <th
                  style={{
                    position: "sticky",
                    top: 0,
                    backgroundColor: "var(--bg-elevated)",
                    padding: "1rem",
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                  }}
                >
                  Categoría
                </th>
                <th
                  style={{
                    position: "sticky",
                    top: 0,
                    backgroundColor: "var(--bg-elevated)",
                    padding: "1rem",
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                  }}
                >
                  Contacto
                </th>
                <th
                  style={{
                    position: "sticky",
                    top: 0,
                    backgroundColor: "var(--bg-elevated)",
                    padding: "1rem",
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                  }}
                >
                  Etapa
                </th>
                <th
                  style={{
                    position: "sticky",
                    top: 0,
                    backgroundColor: "var(--bg-elevated)",
                    padding: "1rem 1.5rem",
                    color: "var(--text-secondary)",
                    textAlign: "right",
                    fontWeight: 600,
                  }}
                >
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody>
              {pageRows.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>
                    No hay clientes que coincidan con los filtros.
                  </td>
                </tr>
              ) : (
                pageRows.map((c) => (
                  <tr
                    key={c.id}
                    style={{ borderBottom: "1px solid var(--border)", transition: "background 0.2s" }}
                    className="table-row-hover"
                  >
                    <td style={{ padding: "1rem 1.5rem", maxWidth: "320px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: "8px",
                            flexShrink: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "linear-gradient(135deg, var(--accent), var(--accent-hover))",
                            color: "white",
                          }}
                          aria-hidden
                        >
                          <Building2 size={18} />
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, color: "white" }}>{c.display_name}</div>
                          {c.contact_email && (
                            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                              {c.contact_email}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: "1rem" }}>
                      <span
                        className="p-status-tag"
                        style={{ background: "rgba(255, 255, 255, 0.08)", color: "var(--text-secondary)" }}
                      >
                        {c.category || "—"}
                      </span>
                    </td>
                    <td style={{ padding: "1rem", maxWidth: "200px", wordBreak: "break-word" }}>
                      {c.phone && <div>📞 {c.phone}</div>}
                      {!c.phone && <span style={{ color: "var(--text-secondary)" }}>—</span>}
                    </td>
                    <td style={{ padding: "1rem" }}>
                      <span className="p-status-tag" style={{ background: "rgba(139, 92, 246, 0.2)" }}>
                        {clientStageLabel(c.stage)}
                      </span>
                    </td>
                    <td style={{ padding: "1rem 1.5rem", textAlign: "right" }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ padding: "0.5rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
                        onClick={() => openDetail(c.id)}
                        title="Ver y editar ficha"
                      >
                        <Edit2 size={16} /> Detalle
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {filtered.length > 0 && !loading && (
        <div
          style={{
            padding: "1rem 1.5rem",
            borderTop: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "var(--bg-elevated)",
            flexShrink: 0,
            flexWrap: "wrap",
            gap: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Mostrando {startIndex + 1} a {Math.min(startIndex + itemsPerPage, filtered.length)} de{" "}
              {filtered.length} resultados
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Ver:</label>
              <select
                value={itemsPerPage}
                onChange={(e) => setItemsPerPage(Number(e.target.value))}
                style={{
                  padding: "0.25rem 0.5rem",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  color: "white",
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
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
                type="button"
                className="btn-secondary"
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                style={{
                  padding: "0.4rem 0.75rem",
                  display: "flex",
                  alignItems: "center",
                  opacity: currentPage === 1 ? 0.5 : 1,
                }}
              >
                <ChevronLeft size={16} /> Anterior
              </button>
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "0 0.5rem",
                  fontSize: "0.9rem",
                  fontWeight: 600,
                }}
              >
                {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage === totalPages}
                style={{
                  padding: "0.4rem 0.75rem",
                  display: "flex",
                  alignItems: "center",
                  opacity: currentPage === totalPages ? 0.5 : 1,
                }}
              >
                Siguiente <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>
      )}

      {newOpen && (
        <NewClientModal
          catalog={catalog}
          onClose={() => setNewOpen(false)}
          onCreated={async () => {
            setNewOpen(false);
            await load();
          }}
        />
      )}

      {selectedId !== null && (
        <ClientDetailModal
          catalog={catalog}
          clientId={selectedId}
          detail={detail}
          loading={detailLoading}
          onClose={() => {
            setSelectedId(null);
            setDetail(null);
          }}
          onSaved={() => refreshDetail(selectedId)}
          onDeleted={async () => {
            setSelectedId(null);
            setDetail(null);
            await load();
          }}
        />
      )}
    </div>
  );
}
