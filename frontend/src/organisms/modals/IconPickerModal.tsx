import { useEffect, useMemo, useState } from "react";
import { CATEGORY_ICON_PICKER } from "../../utils/categoryLucideIcons";
import { Search } from "lucide-react";

interface Props {
  open: boolean;
  title?: string;
  selectedId?: string;
  onClose: () => void;
  onSelect: (iconId: string) => void;
  onClear: () => void;
}

export function IconPickerModal({
  open,
  title = "Elegir icono",
  selectedId,
  onClose,
  onSelect,
  onClear,
}: Props) {
  const [q, setQ] = useState("");

  useEffect(() => {
    if (open) setQ("");
  }, [open]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return CATEGORY_ICON_PICKER;
    return CATEGORY_ICON_PICKER.filter(
      (o) => o.id.toLowerCase().includes(s) || o.label.toLowerCase().includes(s)
    );
  }, [q]);

  if (!open) return null;

  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content icon-picker-modal" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>{title}</h2>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </header>

        <div className="icon-picker-search-wrap">
          <Search size={18} style={{ opacity: 0.5, flexShrink: 0 }} />
          <input
            type="search"
            className="dialog-input"
            placeholder="Buscar por nombre (ej: café, gym, tienda)..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            autoFocus
          />
        </div>

        <div className="icon-picker-grid">
          {filtered.map(({ id, label, Icon }) => {
            const active = selectedId === id;
            return (
              <button
                key={id}
                type="button"
                className={`icon-picker-cell ${active ? "icon-picker-cell--active" : ""}`}
                onClick={() => {
                  onSelect(id);
                  onClose();
                }}
                aria-pressed={active}
                title={`${label} (${id})`}
              >
                <Icon size={26} strokeWidth={1.75} />
                <span className="icon-picker-cell-label">{label}</span>
              </button>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "0.5rem 0 0" }}>
            No hay iconos que coincidan. Prueba otra búsqueda.
          </p>
        )}

        <div className="modal-actions" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              onClear();
              onClose();
            }}
          >
            Quitar icono
          </button>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
