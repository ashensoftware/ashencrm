import { useEffect, useMemo, useRef, useState } from "react";
import type { CatalogItem, Client, ClientMeeting, ParsedMapsUrl } from "../../types";
import {
  createClient,
  patchClient,
  deleteClient,
  uploadClientQuote,
  clientQuotePdfUrl,
  addClientMeeting,
  deleteClientMeeting,
  parseClientMapsUrl,
} from "../../api";
import { Trash2, X, FileText, Loader2, HelpCircle } from "lucide-react";
import { catalogCategoryOptions } from "../../utils/catalogCategoryOptions";

export function NewClientModal({
  catalog,
  onClose,
  onCreated,
}: {
  catalog: CatalogItem[];
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [mapsUrl, setMapsUrl] = useState("");
  const [parsed, setParsed] = useState<ParsedMapsUrl | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [category, setCategory] = useState("");
  const [parsing, setParsing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [mapsParseErr, setMapsParseErr] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const parseToken = useRef(0);

  useEffect(() => {
    const raw = mapsUrl.trim();
    if (raw.length < 12) {
      parseToken.current += 1;
      setParsed(null);
      setMapsParseErr(null);
      setParsing(false);
      return;
    }
    const token = ++parseToken.current;
    const t = window.setTimeout(async () => {
      setParsing(true);
      setMapsParseErr(null);
      try {
        const r = await parseClientMapsUrl(raw);
        if (token !== parseToken.current) return;
        setParsed(r);
        setDisplayName((prev) => (prev.trim() ? prev : r.suggested_display_name || ""));
      } catch (e) {
        if (token !== parseToken.current) return;
        setParsed(null);
        setMapsParseErr(e instanceof Error ? e.message : "No se pudo leer el enlace");
      } finally {
        if (token === parseToken.current) setParsing(false);
      }
    }, 750);
    return () => clearTimeout(t);
  }, [mapsUrl]);

  const categoryChoices = useMemo(() => catalogCategoryOptions(catalog, category), [catalog, category]);

  return (
    <>
      <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div
          className="modal-content small-modal new-client-modal"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="modal-header--stacked">
            <div className="modal-header-title-row">
              <h2>Nuevo cliente</h2>
              <button
                type="button"
                className="btn-icon"
                title="Cómo funciona"
                aria-label="Ayuda: cómo funciona"
                onClick={() => setHelpOpen(true)}
              >
                <HelpCircle size={20} />
              </button>
            </div>
            <p className="modal-header-subtitle">
              El <strong>nombre</strong> es obligatorio. El enlace de Maps es <strong>opcional</strong>:
              si lo pegas, se rellenan ubicación (mapa) y a veces el nombre del lugar.
            </p>
          </header>
          {err && (
            <p style={{ color: "var(--danger)", fontSize: "0.88rem", marginBottom: "0.5rem" }}>{err}</p>
          )}
          <label className="client-form-label">Nombre en el CRM</label>
          <input
            className="search-input"
            placeholder="Ej. Trengie"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoFocus
          />
          <label className="client-form-label" style={{ marginTop: "0.85rem" }}>
            Categoría <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(mismo catálogo que leads)</span>
          </label>
          <select
            className="search-input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">— Sin categoría —</option>
            {categoryChoices.map((c) => (
              <option key={c.name} value={c.name}>
                {c.label}
              </option>
            ))}
          </select>
          <label className="client-form-label" style={{ marginTop: "0.85rem" }}>
            Enlace de Google Maps <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(opcional)</span>
          </label>
          <textarea
            className="search-input client-maps-url-textarea"
            rows={3}
            placeholder="Opcional — https://maps.app.goo.gl/… o maps.google.com/…"
            value={mapsUrl}
            onChange={(e) => setMapsUrl(e.target.value)}
            spellCheck={false}
          />
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.35rem", minHeight: "1.5rem" }}>
            {parsing && (
              <>
                <Loader2 size={16} className="admin-spin" style={{ opacity: 0.8 }} />
                <span style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>Leyendo enlace…</span>
              </>
            )}
            {!parsing && parsed && (
              <span style={{ fontSize: "0.82rem", color: "var(--accent)" }}>
                Ubicación detectada · {parsed.latitude.toFixed(5)}, {parsed.longitude.toFixed(5)}
              </span>
            )}
          </div>
          {mapsParseErr && !parsing && mapsUrl.trim().length >= 12 && (
            <p style={{ color: "var(--warning)", fontSize: "0.82rem", marginTop: "0.35rem", marginBottom: 0 }}>
              {mapsParseErr} Puedes borrar el enlace y crear solo con el nombre.
            </p>
          )}
          <div className="modal-actions" style={{ marginTop: "1rem" }}>
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={busy || !displayName.trim()}
              onClick={async () => {
                const name = displayName.trim();
                if (!name) return;
                setBusy(true);
                setErr(null);
                try {
                  await createClient({
                    display_name: name,
                    category: category.trim(),
                    phone: "",
                    contact_email: "",
                    stage: "quote_sent",
                    ...(parsed
                      ? {
                          latitude: parsed.latitude,
                          longitude: parsed.longitude,
                          maps_url: parsed.resolved_url,
                        }
                      : {}),
                  });
                  await onCreated();
                } catch (e) {
                  setErr(e instanceof Error ? e.message : "Error");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Crear
            </button>
          </div>
        </div>
      </div>
      {helpOpen && (
        <div
          className="modal modal-help-overlay"
          onClick={(e) => e.target === e.currentTarget && setHelpOpen(false)}
          role="dialog"
          aria-labelledby="new-client-help-title"
        >
          <div className="modal-content modal-help-panel" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header--stacked">
              <div className="modal-header-title-row">
                <h2 id="new-client-help-title">Alta manual de cliente</h2>
                <button
                  type="button"
                  className="close-btn"
                  aria-label="Cerrar ayuda"
                  onClick={() => setHelpOpen(false)}
                >
                  ×
                </button>
              </div>
            </header>
            <ul>
              <li>
                <strong>Nombre en el CRM</strong> es el único dato obligatorio: cómo quieres ver al cliente en
                listas y pipeline.
              </li>
              <li>
                <strong>Enlace de Google Maps</strong> es opcional. Si pegas el enlace que copias con
                &quot;Compartir&quot; en Google Maps, intentamos leer coordenadas y el nombre del sitio para el
                mapa de cuentas.
              </li>
              <li>
                Si el enlace no se entiende (por ejemplo, muy corto o incompleto), puedes dejarlo vacío y
                crear igual; más tarde puedes añadir ubicación desde la ficha del cliente.
              </li>
            </ul>
            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={() => setHelpOpen(false)}>
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function ClientDetailModal({
  catalog,
  clientId,
  detail,
  loading,
  onClose,
  onSaved,
  onDeleted,
}: {
  catalog: CatalogItem[];
  clientId: number;
  detail: (Client & { meetings: ClientMeeting[] }) | null;
  loading: boolean;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onDeleted: () => Promise<void>;
}) {
  const [tab, setTab] = useState<"datos" | "cotizacion" | "reuniones" | "dev">("datos");
  const [form, setForm] = useState<Partial<Client>>({});
  const [meetings, setMeetings] = useState<ClientMeeting[]>([]);
  const [saving, setSaving] = useState(false);
  const [meetDraft, setMeetDraft] = useState({ title: "", scheduled_at: "", notes: "" });

  useEffect(() => {
    if (detail) {
      setForm(detail);
      setMeetings(detail.meetings || []);
    }
  }, [detail]);

  const categoryChoices = useMemo(
    () => catalogCategoryOptions(catalog, form.category),
    [catalog, form.category]
  );

  const save = async () => {
    setSaving(true);
    try {
      await patchClient(clientId, form);
      await onSaved();
    } finally {
      setSaving(false);
    }
  };

  const addMeeting = async () => {
    if (!meetDraft.scheduled_at) return;
    setSaving(true);
    try {
      await addClientMeeting(clientId, {
        title: meetDraft.title,
        scheduled_at: new Date(meetDraft.scheduled_at).toISOString(),
        notes: meetDraft.notes,
        status: "scheduled",
      });
      setMeetDraft({ title: "", scheduled_at: "", notes: "" });
      await onSaved();
    } finally {
      setSaving(false);
    }
  };

  const onUploadPdf = async (file: File | null) => {
    if (!file) return;
    setSaving(true);
    try {
      const qAmount = form.quote_amount != null ? Number(form.quote_amount) : undefined;
      await uploadClientQuote(clientId, file, {
        quote_amount: qAmount,
        quote_currency: form.quote_currency || "COP",
        estimated_delivery_at: form.estimated_delivery_at || undefined,
      });
      await onSaved();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal" style={{ zIndex: 9000 }} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content client-detail-modal" onClick={(e) => e.stopPropagation()}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2>{detail?.display_name || "Cliente"}</h2>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Cerrar">
            <X size={22} />
          </button>
        </header>
        {loading && (
          <div style={{ padding: "2rem", display: "flex", justifyContent: "center" }}>
            <Loader2 className="admin-spin" size={28} />
          </div>
        )}
        {!loading && detail && (
          <>
            <div className="client-detail-tabs">
              {(["datos", "cotizacion", "reuniones", "dev"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  className={tab === t ? "btn-primary" : "btn-secondary"}
                  onClick={() => setTab(t)}
                >
                  {t === "datos" && "Datos"}
                  {t === "cotizacion" && "Cotización"}
                  {t === "reuniones" && "Reuniones"}
                  {t === "dev" && "Desarrollo"}
                </button>
              ))}
            </div>

            {tab === "datos" && (
              <div className="client-detail-form">
                <label>Nombre</label>
                <input
                  className="search-input"
                  value={form.display_name ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                />
                <label>Categoría</label>
                <select
                  className="search-input"
                  value={form.category ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                >
                  <option value="">— Sin categoría —</option>
                  {categoryChoices.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.label}
                    </option>
                  ))}
                </select>
                <label>Teléfono</label>
                <input
                  className="search-input"
                  value={form.phone ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                />
                <label>Email</label>
                <input
                  className="search-input"
                  value={form.contact_email ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                />
                <label>Notas</label>
                <textarea
                  className="search-input"
                  rows={4}
                  value={form.notes ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                />
                <label>Pago</label>
                <select
                  className="search-input"
                  value={form.payment_status ?? "pending"}
                  onChange={(e) => setForm((f) => ({ ...f, payment_status: e.target.value }))}
                >
                  <option value="pending">Pendiente</option>
                  <option value="partial">Parcial</option>
                  <option value="paid">Pagado</option>
                </select>
                <label>Contrato requerido</label>
                <input
                  type="checkbox"
                  checked={!!form.contract_required}
                  onChange={(e) => setForm((f) => ({ ...f, contract_required: e.target.checked ? 1 : 0 }))}
                />
                <label>Contrato omitido (no aplica)</label>
                <input
                  type="checkbox"
                  checked={!!form.contract_skipped}
                  onChange={(e) => setForm((f) => ({ ...f, contract_skipped: e.target.checked ? 1 : 0 }))}
                />
              </div>
            )}

            {tab === "cotizacion" && (
              <div className="client-detail-form">
                <label>Precio cotización</label>
                <input
                  type="number"
                  className="search-input"
                  value={form.quote_amount ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, quote_amount: e.target.value ? parseFloat(e.target.value) : null }))
                  }
                />
                <label>Moneda</label>
                <input
                  className="search-input"
                  value={form.quote_currency ?? "COP"}
                  onChange={(e) => setForm((f) => ({ ...f, quote_currency: e.target.value }))}
                />
                <label>Entrega estimada</label>
                <input
                  type="datetime-local"
                  className="search-input"
                  value={
                    form.estimated_delivery_at
                      ? form.estimated_delivery_at.slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      estimated_delivery_at: e.target.value ? new Date(e.target.value).toISOString() : "",
                    }))
                  }
                />
                <label>PDF cotización</label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => onUploadPdf(e.target.files?.[0] || null)}
                />
                {detail.quote_pdf_path && (
                  <div className="client-pdf-preview">
                    <FileText size={16} /> Vista previa
                    <iframe title="Cotización PDF" src={clientQuotePdfUrl(clientId)} className="client-pdf-iframe" />
                  </div>
                )}
              </div>
            )}

            {tab === "reuniones" && (
              <div className="client-detail-form">
                <div className="client-meeting-add">
                  <input
                    className="search-input"
                    placeholder="Título (opcional)"
                    value={meetDraft.title}
                    onChange={(e) => setMeetDraft((d) => ({ ...d, title: e.target.value }))}
                  />
                  <input
                    type="datetime-local"
                    className="search-input"
                    value={meetDraft.scheduled_at}
                    onChange={(e) => setMeetDraft((d) => ({ ...d, scheduled_at: e.target.value }))}
                  />
                  <textarea
                    className="search-input"
                    placeholder="Notas"
                    rows={2}
                    value={meetDraft.notes}
                    onChange={(e) => setMeetDraft((d) => ({ ...d, notes: e.target.value }))}
                  />
                  <button type="button" className="btn-secondary" onClick={addMeeting} disabled={saving || !meetDraft.scheduled_at}>
                    Añadir reunión
                  </button>
                </div>
                <ul className="client-meeting-list">
                  {meetings.map((m) => (
                    <li key={m.id}>
                      <strong>{m.title || "Reunión"}</strong> — {new Date(m.scheduled_at).toLocaleString()}
                      <span className="client-meeting-status">{m.status}</span>
                      <button
                        type="button"
                        className="btn-icon"
                        title="Eliminar"
                        onClick={async () => {
                          await deleteClientMeeting(m.id);
                          await onSaved();
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {tab === "dev" && (
              <div className="client-detail-form">
                <label>Repositorio GitHub</label>
                <input
                  className="search-input"
                  value={form.github_repo_url ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, github_repo_url: e.target.value }))}
                  placeholder="https://github.com/org/repo"
                />
                <label>Dominio / producción</label>
                <input
                  className="search-input"
                  value={form.production_domain ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, production_domain: e.target.value }))}
                />
                <label>Carpeta Drive</label>
                <input
                  className="search-input"
                  value={form.drive_folder_url ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, drive_folder_url: e.target.value }))}
                />
                <label>Staging / preview</label>
                <input
                  className="search-input"
                  value={form.staging_url ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, staging_url: e.target.value }))}
                />
                <label>Google Maps</label>
                <input
                  className="search-input"
                  value={form.maps_url ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, maps_url: e.target.value }))}
                  placeholder="Enlace del lugar (mismo que en alta manual)"
                />
              </div>
            )}

            <div className="modal-actions" style={{ marginTop: "1rem", flexWrap: "wrap" }}>
              <button type="button" className="btn-danger" style={{ flex: "none" }} onClick={() => {
                if (confirm("¿Eliminar este cliente?")) {
                  deleteClient(clientId).then(onDeleted).catch(() => alert("Error al eliminar"));
                }
              }}>
                <Trash2 size={16} /> Eliminar
              </button>
              <button type="button" className="btn-primary" disabled={saving} onClick={save}>
                {saving ? "Guardando…" : "Guardar cambios"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
