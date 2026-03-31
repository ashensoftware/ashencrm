import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { AppSettings, CatalogItem, WhatsappTemplate } from "../types";
import {
  fetchAdminSettings,
  patchAdminSettings,
  patchCatalogCategory,
  renameCatalogCategory,
  resetCategoryAssignments,
  normalizeCategories,
} from "../api";
import { Tags, SlidersHorizontal, MessageSquare, ChevronLeft, ChevronRight, Save, Loader2, Braces, Trash2 } from "lucide-react";
import { IconPickerModal } from "../organisms/modals/IconPickerModal";
import { LucideCategoryIcon, getCategoryIconLabel } from "../utils/categoryLucideIcons";
import { WHATSAPP_TEMPLATE_PLACEHOLDERS } from "../constants/whatsappTemplatePlaceholders";

type Tab = "categories" | "parameters" | "templates";

interface Props {
  catalog: CatalogItem[];
  refreshCatalog: () => Promise<void>;
  refreshProspects: () => Promise<void>;
  onSettingsSaved: () => void;
}

export function AdminPage({
  catalog,
  refreshCatalog,
  refreshProspects,
  onSettingsSaved,
}: Props) {
  const [tab, setTab] = useState<Tab>("categories");
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState<AppSettings | null>(null);
  const [renameOld, setRenameOld] = useState("");
  const [renameNew, setRenameNew] = useState("");
  const [resetCat, setResetCat] = useState("");
  const [catPage, setCatPage] = useState(1);
  const [catPageSize, setCatPageSize] = useState(8);
  const [templatesBaseline, setTemplatesBaseline] = useState<WhatsappTemplate[] | null>(null);
  const [activeTemplateIndex, setActiveTemplateIndex] = useState<number | null>(null);
  const [savingTemplateIndex, setSavingTemplateIndex] = useState<number | null>(null);
  const [templateDeleteIndex, setTemplateDeleteIndex] = useState<number | null>(null);
  const textareaRefs = useRef<(HTMLTextAreaElement | null)[]>([]);

  const loadDraft = useCallback(async () => {
    try {
      const data = await fetchAdminSettings();
      setDraft(data);
      if (tab === "templates") {
        setTemplatesBaseline(JSON.parse(JSON.stringify(data.whatsapp_templates)));
      }
    } catch {
      setNotice("No se pudieron cargar los parametros.");
    }
  }, [tab]);

  useEffect(() => {
    if (tab === "parameters" || tab === "templates") loadDraft();
  }, [tab, loadDraft]);

  const saveParams = async () => {
    if (!draft) return;
    setNotice(null);
    try {
      const next = await patchAdminSettings({
        default_city: draft.default_city,
        default_scrape_limit: draft.default_scrape_limit,
        map_center_lat: draft.map_center_lat,
        map_center_lng: draft.map_center_lng,
        map_zoom: draft.map_zoom,
        ig_min_delay: draft.ig_min_delay,
        ig_max_delay: draft.ig_max_delay,
        max_results_per_category: draft.max_results_per_category,
        scraper_headless: draft.scraper_headless,
        whatsapp_min_delay: draft.whatsapp_min_delay,
        whatsapp_max_delay: draft.whatsapp_max_delay,
        whatsapp_max_daily: draft.whatsapp_max_daily,
        whatsapp_phone: draft.whatsapp_phone,
        lovable_timeout: draft.lovable_timeout,
        lovable_headless: draft.lovable_headless,
      });
      setDraft(next);
      onSettingsSaved();
      setNotice("Parametros guardados.");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Error al guardar");
    }
  };

  const isTemplateRowDirty = (i: number): boolean => {
    if (!draft || !templatesBaseline) return false;
    const cur = draft.whatsapp_templates[i];
    const base = templatesBaseline[i];
    if (!cur) return false;
    if (!base) return true;
    return JSON.stringify(cur) !== JSON.stringify(base);
  };

  const saveTemplateAt = async (index: number) => {
    if (!draft) return;
    setNotice(null);
    setSavingTemplateIndex(index);
    try {
      const next = await patchAdminSettings({ whatsapp_templates: draft.whatsapp_templates });
      setDraft(next);
      setTemplatesBaseline(JSON.parse(JSON.stringify(next.whatsapp_templates)));
      onSettingsSaved();
      const label = next.whatsapp_templates[index]?.name ?? `plantilla ${index + 1}`;
      setNotice(`Guardado: ${label}`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSavingTemplateIndex(null);
    }
  };

  const updateTemplate = (i: number, field: keyof WhatsappTemplate, v: string) => {
    if (!draft) return;
    const copy = [...draft.whatsapp_templates];
    copy[i] = { ...copy[i], [field]: v };
    setDraft({ ...draft, whatsapp_templates: copy });
  };

  const insertPlaceholderAtCursor = (key: string) => {
    if (!draft) return;
    const i = activeTemplateIndex;
    if (i === null) {
      setNotice("Haz clic dentro del texto de una plantilla para insertar el placeholder.");
      return;
    }
    const el = textareaRefs.current[i];
    if (!el) {
      setNotice("Selecciona el recuadro de mensaje de una plantilla.");
      return;
    }
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const text = draft.whatsapp_templates[i].template;
    const ins = `{${key}}`;
    const newText = text.slice(0, start) + ins + text.slice(end);
    updateTemplate(i, "template", newText);
    requestAnimationFrame(() => {
      const node = textareaRefs.current[i];
      if (!node) return;
      node.focus();
      const pos = start + ins.length;
      node.setSelectionRange(pos, pos);
    });
  };

  const addTemplate = () => {
    if (!draft) return;
    const id = `tpl_${Date.now()}`;
    const row: WhatsappTemplate = { id, name: "Nueva", kind: "whatsapp", audience: "cliente", template: "Hola {name}, " };
    setDraft({
      ...draft,
      whatsapp_templates: [...draft.whatsapp_templates, row],
    });
    setTemplatesBaseline((b) => (b ? [...b, { ...row }] : null));
  };

  const removeTemplate = (i: number) => {
    if (!draft) return;
    const next = draft.whatsapp_templates.filter((_, j) => j !== i);
    setDraft({ ...draft, whatsapp_templates: next });
    setTemplatesBaseline((b) => (b ? b.filter((_, j) => j !== i) : null));
    setActiveTemplateIndex((cur) => {
      if (cur === null) return null;
      if (cur === i) return null;
      if (cur > i) return cur - 1;
      return cur;
    });
  };

  const confirmRemoveTemplate = () => {
    if (templateDeleteIndex === null) return;
    removeTemplate(templateDeleteIndex);
    setTemplateDeleteIndex(null);
  };

  const saveRow = async (name: string, label: string, icon: string) => {
    setNotice(null);
    const r = await patchCatalogCategory(name, { label, icon });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      setNotice((err as { detail?: string }).detail || "Error al actualizar categoria");
      return;
    }
    await refreshCatalog();
    setNotice("Categoria actualizada.");
  };

  const doRename = async () => {
    if (!renameOld || !renameNew.trim()) return;
    setNotice(null);
    const r = await renameCatalogCategory(renameOld, renameNew.trim().toLowerCase().replace(/\s+/g, "_"));
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      setNotice((err as { detail?: string }).detail || "Error al renombrar");
      return;
    }
    await refreshCatalog();
    await refreshProspects();
    setRenameNew("");
    setNotice("Categoria renombrada (catalogo y leads).");
  };

  const doReset = async () => {
    if (!resetCat) return;
    setNotice(null);
    const r = await resetCategoryAssignments(resetCat);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      setNotice((err as { detail?: string }).detail || "Error");
      return;
    }
    await refreshProspects();
    setNotice('Leads con esa categoria pasaron a "Sin categoria".');
  };

  const doNormalize = async () => {
    setNotice(null);
    await normalizeCategories();
    await refreshProspects();
    setNotice("Categorias normalizadas.");
  };

  const catTotalPages = Math.max(1, Math.ceil(catalog.length / catPageSize) || 1);
  const paginatedCatalog = useMemo(() => {
    const start = (catPage - 1) * catPageSize;
    return catalog.slice(start, start + catPageSize);
  }, [catalog, catPage, catPageSize]);

  useEffect(() => {
    if (catPage > catTotalPages) setCatPage(catTotalPages);
  }, [catPage, catTotalPages]);

  useEffect(() => {
    if (tab !== "templates") setTemplateDeleteIndex(null);
  }, [tab]);

  const tabBtn = (id: Tab, icon: ReactNode, label: string) => (
    <button
      key={id}
      type="button"
      className={tab === id ? "btn-primary" : "btn-secondary"}
      onClick={() => { setTab(id); setNotice(null); }}
      style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", backgroundColor: "var(--bg-base)", overflow: "auto" }}>
      <div style={{ padding: "1.5rem", borderBottom: "1px solid var(--border)" }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem", color: "white" }}>Administracion</h1>
        <p style={{ margin: "0.25rem 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
          Categorias del catalogo, parametros operativos y plantillas configurables (persistidas en base de datos).
        </p>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", flexWrap: "wrap" }}>
          {tabBtn("categories", <Tags size={18} />, "Categorias")}
          {tabBtn("parameters", <SlidersHorizontal size={18} />, "Parametros")}
          {tabBtn("templates", <MessageSquare size={18} />, "Plantillas")}
        </div>
      </div>

      {notice && (
        <div style={{ padding: "0.75rem 1.5rem", background: "var(--bg-elevated)", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
          {notice}
        </div>
      )}

      <div style={{ padding: "1.5rem", flex: 1 }}>
        {tab === "categories" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div className="admin-cat-toolbar">
              <button type="button" className="btn-secondary" onClick={doNormalize}>
                Normalizar categorías en leads
              </button>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0, lineHeight: 1.5 }}>
              Los iconos por defecto vienen del catálogo en la base de datos; edita aquí y guarda. El icono es{" "}
              <strong style={{ color: "var(--text-secondary)" }}>Lucide</strong> (modal). El id interno (
              <code style={{ fontSize: "0.8em" }}>name</code>) solo cambia con Renombrar.
            </p>
            <div className="admin-cat-card">
              <div className="admin-cat-table-wrap">
                <table className="admin-cat-table">
                  <thead>
                    <tr>
                      <th style={{ width: "18%" }}>Id</th>
                      <th style={{ width: "26%" }}>Etiqueta</th>
                      <th style={{ width: "40%" }}>Icono</th>
                      <th style={{ width: "16%", textAlign: "right" }}>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedCatalog.map((c) => (
                      <CategoryRow key={c.name} item={c} onSave={saveRow} />
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="admin-cat-pagination">
                <span>
                  {catalog.length === 0
                    ? "Sin categorías"
                    : `Mostrando ${(catPage - 1) * catPageSize + 1}–${Math.min(catPage * catPageSize, catalog.length)} de ${catalog.length}`}
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem" }}>
                    Por página
                    <select
                      className="search-input"
                      style={{ padding: "0.35rem 0.5rem", fontSize: "0.85rem", width: "auto" }}
                      value={catPageSize}
                      onChange={(e) => {
                        setCatPageSize(Number(e.target.value));
                        setCatPage(1);
                      }}
                    >
                      {[6, 8, 12, 20].map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="btn-secondary admin-cat-page-btn"
                    disabled={catPage <= 1}
                    onClick={() => setCatPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft size={18} /> Anterior
                  </button>
                  <span style={{ minWidth: "5.5rem", textAlign: "center" }}>
                    Página {catPage} / {catTotalPages}
                  </span>
                  <button
                    type="button"
                    className="btn-secondary admin-cat-page-btn"
                    disabled={catPage >= catTotalPages}
                    onClick={() => setCatPage((p) => Math.min(catTotalPages, p + 1))}
                  >
                    Siguiente <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <h3 style={{ color: "white", fontSize: "1rem" }}>Renombrar id de categoria</h3>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "flex-end" }}>
                <div className="filter-group">
                  <label>Actual</label>
                  <select value={renameOld} onChange={(e) => setRenameOld(e.target.value)}>
                    <option value="">Elegir...</option>
                    {catalog.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                  </select>
                </div>
                <div className="filter-group">
                  <label>Nuevo id</label>
                  <input className="search-input" value={renameNew} onChange={(e) => setRenameNew(e.target.value)} placeholder="ej: farmacia" />
                </div>
                <button type="button" className="btn-primary" onClick={doRename}>Renombrar</button>
              </div>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <h3 style={{ color: "white", fontSize: "1rem" }}>Reasignar leads a Sin categoria</h3>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "flex-end" }}>
                <div className="filter-group">
                  <label>Categoria en leads</label>
                  <select value={resetCat} onChange={(e) => setResetCat(e.target.value)}>
                    <option value="">Elegir...</option>
                    {catalog.map((c) => <option key={c.name} value={c.name}>{c.label}</option>)}
                  </select>
                </div>
                <button type="button" className="btn-secondary" onClick={doReset}>Resetear asignaciones</button>
              </div>
            </div>
          </div>
        )}

        {tab === "parameters" && draft && (
          <ParametersForm draft={draft} setDraft={setDraft} onSave={saveParams} />
        )}

        {tab === "templates" && draft && (
          <div className="admin-templates-layout">
            <div className="admin-templates-topbar">
              <div>
                <h2 className="admin-templates-title">Plantillas</h2>
                <p className="admin-templates-subtitle">
                  Define plantillas por tipo y destino (GPT, Lovable, WhatsApp). Cada plantilla se guarda con su propio botón cuando la edites.
                </p>
              </div>
            </div>

            <div className="admin-templates-grid">
              <aside className="admin-templates-placeholders" aria-label="Placeholders disponibles">
                <h3 className="admin-templates-aside-title">Placeholders</h3>
                <p className="admin-templates-hint">
                  Haz clic en el mensaje de una plantilla y luego en un placeholder para insertar <code>{"{clave}"}</code> en la posición del cursor.
                </p>
                <p className="admin-templates-hint admin-templates-hint-secondary">
                  Los cambios no se guardan solos: usa <strong>Guardar</strong> en la tarjeta de esa plantilla.
                </p>
                <ul className="admin-templates-ph-list">
                  {WHATSAPP_TEMPLATE_PLACEHOLDERS.map((ph) => (
                    <li key={ph.key}>
                      <button
                        type="button"
                        className="admin-templates-ph-chip"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          insertPlaceholderAtCursor(ph.key);
                        }}
                        title={ph.description}
                      >
                        <code>{"{" + ph.key + "}"}</code>
                        <Braces size={14} aria-hidden />
                      </button>
                      <span className="admin-templates-ph-desc">{ph.description}</span>
                    </li>
                  ))}
                </ul>
              </aside>

              <div className="admin-templates-editor">
                {draft.whatsapp_templates.map((t, i) => (
                  <div key={t.id} className="admin-templates-card">
                    <div className="admin-templates-card-head">
                      <span className="admin-templates-card-id">id: <code>{t.id}</code></span>
                      <input
                        className="search-input admin-templates-card-name"
                        value={t.name}
                        onChange={(e) => updateTemplate(i, "name", e.target.value)}
                        onFocus={() => setActiveTemplateIndex(i)}
                        placeholder="Nombre visible"
                        aria-label={`Nombre plantilla ${t.id}`}
                      />
                      <select
                        className="search-input"
                        style={{ width: "150px" }}
                        value={t.kind || "whatsapp"}
                        onChange={(e) => updateTemplate(i, "kind", e.target.value)}
                        onFocus={() => setActiveTemplateIndex(i)}
                        aria-label={`Tipo plantilla ${t.id}`}
                      >
                        <option value="whatsapp">WhatsApp</option>
                        <option value="gpt">GPT</option>
                        <option value="lovable">Lovable</option>
                      </select>
                      <select
                        className="search-input"
                        style={{ width: "150px" }}
                        value={t.audience || "cliente"}
                        onChange={(e) => updateTemplate(i, "audience", e.target.value)}
                        onFocus={() => setActiveTemplateIndex(i)}
                        aria-label={`Destino plantilla ${t.id}`}
                      >
                        <option value="cliente">Cliente</option>
                        <option value="ia">IA</option>
                        <option value="equipo_interno">Equipo interno</option>
                      </select>
                      {isTemplateRowDirty(i) && (
                        <button
                          type="button"
                          className="btn-primary admin-templates-card-save"
                          onClick={() => saveTemplateAt(i)}
                          disabled={savingTemplateIndex !== null}
                        >
                          {savingTemplateIndex === i ? (
                            <Loader2 size={16} className="admin-spin" />
                          ) : (
                            <Save size={16} strokeWidth={2.25} />
                          )}
                          {savingTemplateIndex === i ? "Guardando…" : "Guardar"}
                        </button>
                      )}
                      <button
                        type="button"
                        className="admin-templates-delete-btn"
                        onClick={() => setTemplateDeleteIndex(i)}
                        aria-label={`Eliminar plantilla ${t.name}`}
                      >
                        <Trash2 size={16} strokeWidth={2.25} aria-hidden />
                        Eliminar
                      </button>
                    </div>
                    <textarea
                      ref={(el) => {
                        textareaRefs.current[i] = el;
                      }}
                      className="search-input admin-templates-textarea"
                      value={t.template}
                      onChange={(e) => updateTemplate(i, "template", e.target.value)}
                      onFocus={() => setActiveTemplateIndex(i)}
                      placeholder="Escribe el mensaje usando placeholders como {name}, {city}…"
                      rows={6}
                    />
                  </div>
                ))}
                <button type="button" className="btn-secondary" onClick={addTemplate}>
                  + Añadir plantilla
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {templateDeleteIndex !== null && draft && draft.whatsapp_templates[templateDeleteIndex] && (
        <div
          className="modal"
          style={{ zIndex: 10000 }}
          onClick={(e) => e.target === e.currentTarget && setTemplateDeleteIndex(null)}
        >
          <div className="modal-content small-modal" onClick={(e) => e.stopPropagation()}>
            <header>
              <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Trash2 size={22} strokeWidth={2} style={{ color: "var(--danger)", opacity: 0.95 }} aria-hidden />
                Eliminar plantilla
              </h2>
            </header>
            <p style={{ marginBottom: "1rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              ¿Seguro que deseas eliminar la plantilla{" "}
              <strong>«{draft.whatsapp_templates[templateDeleteIndex].name}»</strong>{" "}
              <span style={{ color: "var(--text-muted)", fontSize: "0.9em" }}>
                (id: <code>{draft.whatsapp_templates[templateDeleteIndex].id}</code>)
              </span>
              ? Los cambios en la lista se aplican al borrador; usa <strong>Guardar</strong> en otra plantilla si
              quieres persistir en el servidor.
            </p>
            <div className="modal-actions" style={{ marginTop: "1.25rem", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button type="button" className="btn-secondary" onClick={() => setTemplateDeleteIndex(null)}>
                Cancelar
              </button>
              <button type="button" className="btn-danger" style={{ flex: "none" }} onClick={confirmRemoveTemplate}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                  <Trash2 size={16} strokeWidth={2.25} aria-hidden />
                  Eliminar
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryRow({
  item,
  onSave,
}: {
  item: CatalogItem;
  onSave: (name: string, label: string, icon: string) => void;
}) {
  const [label, setLabel] = useState(item.label);
  const [icon, setIcon] = useState(item.icon || "");
  const [pickerOpen, setPickerOpen] = useState(false);
  useEffect(() => {
    setLabel(item.label);
    setIcon(item.icon || "");
  }, [item.label, item.icon, item.name]);

  const hasIcon = Boolean(icon && icon.trim());
  const iconSummary = hasIcon ? getCategoryIconLabel(icon) || icon : "Sin icono";

  return (
    <tr>
      <td>
        <code>{item.name}</code>
      </td>
      <td>
        <input className="search-input" value={label} onChange={(e) => setLabel(e.target.value)} />
      </td>
      <td>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              minWidth: 0,
              color: "var(--accent)",
            }}
          >
            <LucideCategoryIcon iconId={icon || undefined} size={24} />
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", maxWidth: 200 }} title={icon || undefined}>
              {iconSummary}
            </span>
          </div>
          <button
            type="button"
            className="btn-secondary"
            style={{ fontSize: "0.8rem", padding: "0.4rem 0.7rem" }}
            onClick={() => setPickerOpen(true)}
          >
            Elegir icono
          </button>
        </div>
        <IconPickerModal
          open={pickerOpen}
          selectedId={icon || undefined}
          onClose={() => setPickerOpen(false)}
          onSelect={(id) => setIcon(id)}
          onClear={() => setIcon("")}
        />
      </td>
      <td style={{ textAlign: "right" }}>
        <button
          type="button"
          className="btn-primary admin-cat-save"
          onClick={() => onSave(item.name, label, icon)}
        >
          <Save size={16} strokeWidth={2.25} />
          Guardar
        </button>
      </td>
    </tr>
  );
}

function ParametersForm({
  draft,
  setDraft,
  onSave,
}: {
  draft: AppSettings;
  setDraft: (d: AppSettings) => void;
  onSave: () => void;
}) {
  const n = (k: keyof AppSettings, v: number) => setDraft({ ...draft, [k]: v } as AppSettings);
  const s = (k: keyof AppSettings, v: string) => setDraft({ ...draft, [k]: v } as AppSettings);
  const b = (k: keyof AppSettings, v: boolean) => setDraft({ ...draft, [k]: v } as AppSettings);
  const row = (label: string, child: ReactNode) => (
    <div className="filter-group" style={{ minWidth: 200 }}>
      <label>{label}</label>
      {child}
    </div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {row("Ciudad por defecto", <input className="search-input" value={draft.default_city} onChange={(e) => s("default_city", e.target.value)} />)}
        {row("Limite scrape por defecto", <input type="number" className="search-input" value={draft.default_scrape_limit} onChange={(e) => n("default_scrape_limit", parseInt(e.target.value, 10) || 0)} />)}
      </div>
      <h3 style={{ color: "white", fontSize: "1rem", margin: 0 }}>Mapa</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {row("Latitud centro", <input type="number" step="any" className="search-input" value={draft.map_center_lat} onChange={(e) => n("map_center_lat", parseFloat(e.target.value) || 0)} />)}
        {row("Longitud centro", <input type="number" step="any" className="search-input" value={draft.map_center_lng} onChange={(e) => n("map_center_lng", parseFloat(e.target.value) || 0)} />)}
        {row("Zoom", <input type="number" className="search-input" value={draft.map_zoom} onChange={(e) => n("map_zoom", parseInt(e.target.value, 10) || 1)} />)}
      </div>
      <h3 style={{ color: "white", fontSize: "1rem", margin: 0 }}>Scraper</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {row("IG min delay (s)", <input type="number" step="any" className="search-input" value={draft.ig_min_delay} onChange={(e) => n("ig_min_delay", parseFloat(e.target.value) || 0)} />)}
        {row("IG max delay (s)", <input type="number" step="any" className="search-input" value={draft.ig_max_delay} onChange={(e) => n("ig_max_delay", parseFloat(e.target.value) || 0)} />)}
        {row("Max resultados / categoria", <input type="number" className="search-input" value={draft.max_results_per_category} onChange={(e) => n("max_results_per_category", parseInt(e.target.value, 10) || 0)} />)}
        {row("Headless", (
          <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={draft.scraper_headless} onChange={(e) => b("scraper_headless", e.target.checked)} />
            Navegador sin ventana
          </label>
        ))}
      </div>
      <h3 style={{ color: "white", fontSize: "1rem", margin: 0 }}>WhatsApp / outreach</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {row("Telefono", <input className="search-input" value={draft.whatsapp_phone} onChange={(e) => s("whatsapp_phone", e.target.value)} />)}
        {row("Min delay (s)", <input type="number" className="search-input" value={draft.whatsapp_min_delay} onChange={(e) => n("whatsapp_min_delay", parseInt(e.target.value, 10) || 0)} />)}
        {row("Max delay (s)", <input type="number" className="search-input" value={draft.whatsapp_max_delay} onChange={(e) => n("whatsapp_max_delay", parseInt(e.target.value, 10) || 0)} />)}
        {row("Max diario", <input type="number" className="search-input" value={draft.whatsapp_max_daily} onChange={(e) => n("whatsapp_max_daily", parseInt(e.target.value, 10) || 0)} />)}
      </div>
      <h3 style={{ color: "white", fontSize: "1rem", margin: 0 }}>Lovable / generador</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {row("Timeout (s)", <input type="number" className="search-input" value={draft.lovable_timeout} onChange={(e) => n("lovable_timeout", parseInt(e.target.value, 10) || 30)} />)}
        {row("Headless Lovable", (
          <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={draft.lovable_headless} onChange={(e) => b("lovable_headless", e.target.checked)} />
            Sin ventana
          </label>
        ))}
      </div>
      <button type="button" className="btn-primary" onClick={onSave}>Guardar parametros</button>
    </div>
  );
}
