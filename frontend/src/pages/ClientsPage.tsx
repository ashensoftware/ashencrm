import { useCallback, useEffect, useMemo, useState } from "react";
import type { CatalogItem, Client, ClientMeeting, Prospect } from "../types";
import {
  fetchClients,
  fetchClient,
  fetchCatalog,
  fetchProspects,
  patchClient,
  createClientFromProspect,
} from "../api";
import { Building2, Plus } from "lucide-react";
import { STAGE_COLUMNS } from "../constants/clientStages";
import { LeadImportCombobox } from "../organisms/LeadImportCombobox";
import { NewClientModal, ClientDetailModal } from "../organisms/modals/ClientModals";

function ClientCard({
  c,
  onOpen,
  onDragStart,
}: {
  c: Client;
  onOpen: () => void;
  onDragStart: (e: React.DragEvent) => void;
}) {
  const price =
    c.quote_amount != null && c.quote_amount !== undefined
      ? `${c.quote_currency || "COP"} ${Number(c.quote_amount).toLocaleString()}`
      : null;
  return (
    <div className="todo-card" onClick={onOpen} draggable onDragStart={onDragStart}>
      <div className="todo-card-header">
        <div className="todo-card-avatar">
          <Building2 size={16} />
        </div>
        <span className="todo-card-title">{c.display_name}</span>
      </div>
      <div className="todo-card-meta">
        {c.category && <span className="todo-card-category">{c.category}</span>}
        {price && <span className="todo-card-category">{price}</span>}
      </div>
    </div>
  );
}

export function ClientsPipelinePage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<(Client & { meetings: ClientMeeting[] }) | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [newOpen, setNewOpen] = useState(false);
  const [importName, setImportName] = useState("");
  const [saving, setSaving] = useState(false);
  const [leadOptions, setLeadOptions] = useState<Prospect[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);

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

  const handleDragStart = (e: React.DragEvent, clientId: number) => {
    e.dataTransfer.setData("text/plain", String(clientId));
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDrop = async (e: React.DragEvent, targetStage: string) => {
    e.preventDefault();
    const idStr = e.dataTransfer.getData("text/plain");
    setDragOverCol(null);
    const clientId = parseInt(idStr, 10);
    if (!clientId) return;
    try {
      await patchClient(clientId, { stage: targetStage });
      await load();
      if (selectedId === clientId) await refreshDetail(clientId);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Error al mover");
    }
  };

  return (
    <div className="todo-view">
      <header className="todo-header">
        <div className="clients-pipeline-header-row">
          <div>
            <h2>Clientes</h2>
            <p>Pipeline después del contacto — arrastra tarjetas entre etapas</p>
          </div>
          <div className="clients-pipeline-toolbar">
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
            >
              <Plus size={18} /> Nuevo cliente
            </button>
          </div>
        </div>
      </header>
      {notice && (
        <div style={{ padding: "0.5rem 0", color: "var(--warning)", fontSize: "0.9rem" }}>{notice}</div>
      )}
      {loading ? (
        <div style={{ padding: "2rem", color: "var(--text-muted)" }}>Cargando…</div>
      ) : (
        <div className="todo-columns clients-kanban-columns">
          {STAGE_COLUMNS.map((col) => {
            const items = clients.filter((c) => c.stage === col.stage);
            const isOver = dragOverCol === col.stage;
            return (
              <div
                className={`todo-column ${isOver ? "todo-column-dragover" : ""}`}
                key={col.stage}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.dataTransfer.dropEffect = "move";
                  setDragOverCol(col.stage);
                }}
                onDragLeave={() => setDragOverCol(null)}
                onDrop={(e) => handleDrop(e, col.stage)}
              >
                <div className="todo-column-header" style={{ borderTopColor: col.color }}>
                  <span className="todo-column-title">{col.label}</span>
                  <span className="todo-column-count">{items.length}</span>
                </div>
                <div className="todo-column-body">
                  {items.length === 0 && (
                    <div className="todo-empty">{isOver ? "Soltar aquí" : "Vacío"}</div>
                  )}
                  {items.map((c) => (
                    <ClientCard
                      key={c.id}
                      c={c}
                      onOpen={() => openDetail(c.id)}
                      onDragStart={(e) => handleDragStart(e, c.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
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
