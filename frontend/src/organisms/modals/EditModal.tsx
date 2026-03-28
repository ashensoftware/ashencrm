import { useMemo } from "react";
import { LABELS } from "../../constants";
import type { Prospect } from "../../types";
import type { CatalogItem } from "../../types";
import { catalogCategoryOptions } from "../../utils/catalogCategoryOptions";

interface EditForm {
  name: string;
  category: string;
  phone: string;
  address: string;
}

interface Props {
  prospect: Prospect;
  form: EditForm;
  catalog: CatalogItem[];
  onFormChange: (f: EditForm) => void;
  onClose: () => void;
  onSubmit: () => Promise<void>;
}

export function EditModal({ prospect: _prospect, form, catalog, onFormChange, onClose, onSubmit }: Props) {
  const categoryChoices = useMemo(
    () => catalogCategoryOptions(catalog, form.category),
    [catalog, form.category]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit();
  };

  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content">
        <header>
          <h2>{LABELS.EDIT_LEAD}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </header>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>{LABELS.NAME}</label>
            <input
              value={form.name}
              onChange={(e) => onFormChange({ ...form, name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>{LABELS.CATEGORY}</label>
            <select
              value={form.category}
              onChange={(e) => onFormChange({ ...form, category: e.target.value })}
            >
              <option value="">— Sin categoría —</option>
              {categoryChoices.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>{LABELS.PHONE}</label>
            <input
              value={form.phone}
              onChange={(e) => onFormChange({ ...form, phone: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>{LABELS.ADDRESS}</label>
            <input
              value={form.address}
              onChange={(e) => onFormChange({ ...form, address: e.target.value })}
            />
          </div>
          <div className="modal-actions">
            <button type="submit" className="btn-primary">{LABELS.SAVE}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
