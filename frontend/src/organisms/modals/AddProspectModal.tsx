import { useState } from "react";
import type { Prospect, CatalogItem } from "../../types";

interface Props {
  catalog: CatalogItem[];
  onClose: () => void;
  onSubmit: (data: Partial<Prospect>) => Promise<void>;
}

export function AddProspectModal({ catalog, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<Partial<Prospect>>({
    name: "",
    category: "",
    phone: "",
    city: "",
    address: "",
    instagram_handle: "",
    notes: "",
  });

  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await onSubmit(form);
    setLoading(false);
  };

  return (
    <div className="modal" style={{ zIndex: 9999 }} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content" style={{ maxWidth: "550px", width: "100%" }}>
        <header style={{ borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
          <h2>Añadir Cliente Manualmente</h2>
          <button className="close-btn" onClick={onClose} disabled={loading}>×</button>
        </header>
        
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
          
          <div style={{ display: "flex", gap: "1rem" }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Nombre del Cliente o Negocio *</label>
              <input
                required
                placeholder="Ej. Barbería El Maestro"
                value={form.name || ""}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Categoría *</label>
              <select
                required
                value={form.category || ""}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                <option value="" disabled>Seleccionar Categoría</option>
                {catalog.map((c) => (
                  <option key={c.name} value={c.name}>{c.label}</option>
                ))}
              </select>
            </div>
          </div>

          <fieldset style={{ border: "1px solid var(--border)", borderRadius: "8px", padding: "1rem" }}>
            <legend style={{ color: "var(--text-secondary)", fontSize: "0.85rem", padding: "0 0.5rem" }}>Contacto & Ubicación (Opcionales)</legend>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
              <div className="form-group" style={{ flex: "1 1 calc(50% - 1rem)" }}>
                <label>Teléfono o WhatsApp</label>
                <input
                  placeholder="Ej. +57300000000"
                  value={form.phone || ""}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                />
              </div>
              <div className="form-group" style={{ flex: "1 1 calc(50% - 1rem)" }}>
                <label>Instagram Handle</label>
                <div style={{ position: "relative" }}>
                  <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }}>@</span>
                  <input
                    placeholder="usuario"
                    style={{ paddingLeft: "1.8rem" }}
                    value={form.instagram_handle || ""}
                    onChange={(e) => setForm({ ...form, instagram_handle: e.target.value })}
                  />
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <div className="form-group" style={{ flex: "1 1 calc(50% - 1rem)" }}>
                <label>Ciudad</label>
                <input
                  placeholder="Ej. Medellín"
                  value={form.city || ""}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                />
              </div>
              <div className="form-group" style={{ flex: "1 1 calc(50% - 1rem)" }}>
                <label>Dirección</label>
                <input
                  placeholder="Ej. Calle Falsa 123"
                  value={form.address || ""}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                />
              </div>
            </div>
          </fieldset>

          <div className="form-group">
            <label>Notas Internas</label>
            <textarea
              rows={3}
              placeholder="Puedes agregar detalles sobre el cliente aquí..."
              value={form.notes || ""}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "8px", border: "1px solid var(--border)", backgroundColor: "var(--bg-secondary)", color: "white", resize: "vertical" }}
            />
          </div>

          <div className="modal-actions" style={{ justifyContent: "flex-end", marginTop: "0.5rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Guardando..." : "Crear Cliente"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
