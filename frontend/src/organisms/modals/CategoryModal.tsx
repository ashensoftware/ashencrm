import { LABELS } from "../../constants";
import type { CatalogItem } from "../../types";

interface Props {
  catalog: CatalogItem[];
  onClose: () => void;
  onDelete: (name: string) => Promise<void>;
  onAdd: () => Promise<void>;
}

export function CategoryModal({ catalog, onClose, onDelete, onAdd }: Props) {
  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content">
        <header>
          <h2>{LABELS.MANAGE_CATEGORIES}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </header>
        <ul className="category-list">
          {catalog.map((c) => (
            <li key={c.name} className="category-item">
              <span>{c.label}</span>
              <button
                className="btn-icon"
                onClick={() => onDelete(c.name)}
              >
                🗑
              </button>
            </li>
          ))}
        </ul>
        <div className="modal-actions" style={{ marginTop: "1rem" }}>
          <button className="btn-secondary" onClick={onAdd}>
            {LABELS.ADD_CATEGORY}
          </button>
        </div>
      </div>
    </div>
  );
}
