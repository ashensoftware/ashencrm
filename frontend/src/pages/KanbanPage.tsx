import { useState, useCallback } from "react";
import type { Prospect } from "../types";
import { getScreenshotUrl } from "../api";
import { Eye, Phone, Globe, MessageCircle, Building2, X } from "lucide-react";

interface Props {
  prospects: Prospect[];
  onSelectProspect: (p: Prospect) => void;
  onWhatsApp?: (p: Prospect) => void;
  onChangeStatus?: (prospectName: string, newStatus: string) => void;
}

const COLUMNS = [
  { status: "ready", label: "Potencial", color: "#58a6ff" },
  { status: "prompt_gpt", label: "Prompt GPT", color: "#f59e0b" },
  { status: "demo_created", label: "Demo Lista", color: "#a78bfa" },
  { status: "contacted", label: "Contactado", color: "#2ea043" },
  { status: "client_won", label: "Cliente Obtenido", color: "#10b981" },
] as const;

function ProspectCard({ prospect, onSelect, onWhatsApp, onDragStart }: {
  prospect: Prospect;
  onSelect: () => void;
  onWhatsApp?: () => void;
  onDragStart: (e: React.DragEvent) => void;
}) {
  const phone = prospect.phone || prospect.ig_phone;
  const website = prospect.website || prospect.ig_website;
  const initial = prospect.name?.charAt(0)?.toUpperCase() || "?";
  const pfp = prospect.screenshot_path?.startsWith("http")
    ? prospect.screenshot_path
    : getScreenshotUrl(prospect.screenshot_path);
  const [imgError, setImgError] = useState(false);

  return (
    <div className="todo-card" onClick={onSelect} draggable onDragStart={onDragStart}>
      <div className="todo-card-header">
        <div className="todo-card-avatar">
          {pfp && !imgError ? (
            <img src={pfp} alt={initial} onError={() => setImgError(true)} />
          ) : (
            <Building2 size={16} />
          )}
        </div>
        <span className="todo-card-title">{prospect.name}</span>
        {prospect.lead_score != null && <span className="todo-card-score">{prospect.lead_score}</span>}
      </div>
      <div className="todo-card-meta">
        {prospect.category && <span className="todo-card-category">{prospect.category}</span>}
      </div>
      <div className="todo-card-actions">
        <button className="todo-action-btn" onClick={(e) => { e.stopPropagation(); onSelect(); }} title="Ver detalle"><Eye size={14} /></button>
        {phone && <a className="todo-action-btn" href={`tel:${phone}`} onClick={(e) => e.stopPropagation()} title="Llamar"><Phone size={14} /></a>}
        {website && <a className="todo-action-btn" href={website} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} title="Web"><Globe size={14} /></a>}
        {onWhatsApp && phone && <button className="todo-action-btn whatsapp" onClick={(e) => { e.stopPropagation(); onWhatsApp(); }} title="WhatsApp"><MessageCircle size={14} /></button>}
      </div>
    </div>
  );
}

export function KanbanPage({ prospects, onSelectProspect, onWhatsApp, onChangeStatus }: Props) {
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const [showRejectedModal, setShowRejectedModal] = useState(false);
  const rejectedProspects = prospects.filter((p) => p.status === "rejected");

  const handleDragStart = useCallback((e: React.DragEvent, prospectName: string) => {
    e.dataTransfer.setData("text/plain", prospectName);
    e.dataTransfer.effectAllowed = "move";
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetStatus: string) => {
    e.preventDefault();
    const prospectName = e.dataTransfer.getData("text/plain");
    setDragOverCol(null);
    if (prospectName && onChangeStatus) onChangeStatus(prospectName, targetStatus);
  }, [onChangeStatus]);

  return (
    <div className="todo-view">
      <header className="todo-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <h2>Pipeline de Prospectos</h2>
            <p>Seguimiento de leads en progreso — arrastra tarjetas entre columnas</p>
          </div>
          <button className="btn-secondary" onClick={() => setShowRejectedModal(true)}>
            Ver rechazados ({rejectedProspects.length})
          </button>
        </div>
      </header>
      <div className="todo-columns">
        {COLUMNS.map((col) => {
          const items = prospects.filter(p => p.status === col.status || (col.status === "contacted" && p.is_contacted));
          const isOver = dragOverCol === col.status;
          return (
            <div
              className={`todo-column ${isOver ? "todo-column-dragover" : ""}`}
              key={col.status}
              onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverCol(col.status); }}
              onDragLeave={() => setDragOverCol(null)}
              onDrop={(e) => handleDrop(e, col.status)}
            >
              <div className="todo-column-header" style={{ borderTopColor: col.color }}>
                <span className="todo-column-title">{col.label}</span>
                <span className="todo-column-count">{items.length}</span>
              </div>
              <div className="todo-column-body">
                {items.length === 0 && <div className="todo-empty">{isOver ? "Soltar aquí" : "Sin prospectos"}</div>}
                {items.map((p) => (
                  <ProspectCard
                    key={p.name}
                    prospect={p}
                    onSelect={() => onSelectProspect(p)}
                    onWhatsApp={onWhatsApp ? () => onWhatsApp(p) : undefined}
                    onDragStart={(e) => handleDragStart(e, p.name)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {showRejectedModal && (
        <div className="modal" onClick={(e) => e.target === e.currentTarget && setShowRejectedModal(false)}>
          <div className="modal-content" style={{ width: "760px", maxHeight: "88vh" }}>
            <header>
              <h2>Prospectos rechazados</h2>
              <button className="close-btn" onClick={() => setShowRejectedModal(false)} aria-label="Cerrar">×</button>
            </header>
            {rejectedProspects.length === 0 ? (
              <div className="empty-state" style={{ padding: "1rem 0 0.25rem" }}>
                No hay prospectos rechazados por ahora.
              </div>
            ) : (
              <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.6rem", paddingRight: "0.25rem" }}>
                {rejectedProspects.map((p) => (
                  <div key={p.name} className="todo-card" style={{ cursor: "default" }}>
                    <div className="todo-card-header">
                      <div className="todo-card-avatar">
                        <X size={16} />
                      </div>
                      <span className="todo-card-title">{p.name}</span>
                      {p.lead_score != null && <span className="todo-card-score">{p.lead_score}</span>}
                    </div>
                    <div className="todo-card-meta">
                      {p.category && <span className="todo-card-category">{p.category}</span>}
                    </div>
                    <div className="todo-card-actions">
                      <button className="todo-action-btn" onClick={() => onSelectProspect(p)} title="Ver detalle">
                        <Eye size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
