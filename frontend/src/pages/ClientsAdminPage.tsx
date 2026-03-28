import { useEffect, useState } from "react";
import { fetchAdminSettings, patchAdminSettings } from "../api";
import type { ClientPreferences } from "../types";
import { Save, Loader2 } from "lucide-react";

const DEFAULT_PREFS: ClientPreferences = {
  default_currency: "COP",
  quote_footer_note: "",
};

interface Props {
  onSettingsSaved?: () => void;
}

export function ClientsAdminPage({ onSettingsSaved }: Props) {
  const [prefs, setPrefs] = useState<ClientPreferences>(DEFAULT_PREFS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const s = await fetchAdminSettings();
        const cp = s.client_preferences;
        if (!cancelled) {
          setPrefs({
            default_currency: cp?.default_currency ?? DEFAULT_PREFS.default_currency,
            quote_footer_note: cp?.quote_footer_note ?? "",
          });
        }
      } catch {
        if (!cancelled) setNotice("No se pudieron cargar los ajustes.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const save = async () => {
    setSaving(true);
    setNotice(null);
    try {
      await patchAdminSettings({ client_preferences: prefs });
      onSettingsSaved?.();
      setNotice("Parámetros de clientes guardados.");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="clients-admin-page">
      <header className="clients-page-header">
        <div>
          <h1>Parámetros — Clientes</h1>
          <p className="clients-page-sub">
            Valores por defecto (moneda, notas legales) para cotizaciones. Para editar fichas usa{" "}
            <strong>Clientes → Gestión de clientes</strong>. Categorías, scrape y WhatsApp están en{" "}
            <strong>Leads → Administración</strong>.
          </p>
        </div>
      </header>

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Cargando…</p>
      ) : (
        <div className="clients-admin-form">
          {notice && (
            <p style={{ color: notice.startsWith("Parámetros") ? "var(--success)" : "var(--warning)", fontSize: "0.9rem" }}>
              {notice}
            </p>
          )}
          <label className="clients-admin-label">Moneda por defecto en cotizaciones</label>
          <input
            className="search-input"
            value={prefs.default_currency}
            onChange={(e) => setPrefs((p) => ({ ...p, default_currency: e.target.value }))}
            placeholder="COP"
          />
          <label className="clients-admin-label">Nota al pie / texto legal (PDFs y plantillas)</label>
          <textarea
            className="search-input"
            rows={5}
            value={prefs.quote_footer_note}
            onChange={(e) => setPrefs((p) => ({ ...p, quote_footer_note: e.target.value }))}
            placeholder="Texto opcional que puedes reutilizar al exportar cotizaciones."
          />
          <button type="button" className="btn-primary" onClick={save} disabled={saving} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
            {saving ? <Loader2 size={18} className="admin-spin" /> : <Save size={18} />}
            {saving ? "Guardando…" : "Guardar parámetros"}
          </button>
        </div>
      )}
    </div>
  );
}
