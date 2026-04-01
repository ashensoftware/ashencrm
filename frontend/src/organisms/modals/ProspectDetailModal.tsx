import type { Prospect } from "../../types";
import { fetchAdminSettings, getScreenshotUrl, updateProspect } from "../../api";
import { mapStatusToLabel } from "../../utils";
import { LABELS } from "../../constants";
import { X, CheckCircle, ChevronRight, ChevronLeft, Sparkles, Edit2, Globe, Send, Coffee, Utensils, Activity, Scissors, Heart, Hammer, ShoppingBag, Wrench, Briefcase, Tag, MapPin, Info, Clipboard, ClipboardCheck } from "lucide-react";
import { useState, useEffect } from "react";

function getCategoryIcon(cat?: string) {
  if (!cat) return <Tag size={14} />;
  const c = cat.toLowerCase();
  if (c.includes("cafe")) return <Coffee size={14} />;
  if (c.includes("restaurante")) return <Utensils size={14} />;
  if (c.includes("gimnasio") || c.includes("gym")) return <Activity size={14} />;
  if (c.includes("barberia") || c.includes("peluqueria")) return <Scissors size={14} />;
  if (c.includes("odontologia") || c.includes("medico") || c.includes("clinica")) return <Heart size={14} />;
  if (c.includes("veterinaria") || c.includes("mascota") || c.includes("pet")) return <Heart size={14} />;
  if (c.includes("ferreteria") || c.includes("construccion")) return <Hammer size={14} />;
  if (c.includes("panaderia") || c.includes("reposteria") || c.includes("tienda") || c.includes("petshop")) return <ShoppingBag size={14} />;
  if (c.includes("estetica") || c.includes("spa")) return <Sparkles size={14} />;
  if (c.includes("taller") || c.includes("mecanica")) return <Wrench size={14} />;
  if (c.includes("coworking") || c.includes("oficina")) return <Briefcase size={14} />;
  return <Tag size={14} />;
}

function renderTemplateWithProspect(template: string, p: Prospect): string {
  const firstName = (p.name || "").trim().split(/\s+/)[0] || "";
  const data: Record<string, string> = {
    name: p.name || "",
    first_name: firstName,
    category: p.category || "",
    city: p.city || "",
    address: p.address || "",
    phone: (p.phone || p.ig_phone || ""),
    followers: String(p.ig_followers || 0),
    instagram: p.instagram_url || "",
    instagram_handle: p.instagram_handle || "",
    demo_url: p.demo_url || "",
    website: p.website || p.ig_website || "",
    rating: String(p.rating || 0),
    reviews_count: String(p.reviews_count || 0),
    email: p.ig_email || "",
    bio: p.ig_bio || "",
    notes: p.notes || "",
    maps_url: p.maps_url || "",
  };
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_m, key: string) => data[key] ?? "");
}

interface Props {
  prospect: Prospect;
  onClose: () => void;
  onReject?: () => void;
  onAccept?: () => void;
  onContact?: () => void;
  onWhatsApp?: () => void;
  onGenerateDemo?: () => void;
  onAdvanceStatus?: (nextStatus: string) => void;
  onNext?: () => void;
  onPrev?: () => void;
  hasPrev?: boolean;
  inline?: boolean;
}

function InfoRow({ label, value, href }: { label: string; value?: string; href?: string }) {
  if (!value && !href) return null;
  return (
    <div className="prospect-detail-row">
      <span style={{ color: "var(--text-muted)", minWidth: 90 }}>{label}:</span>
      {href ? <a href={href} target="_blank" rel="noopener noreferrer">{value || href}</a> : <span>{value}</span>}
    </div>
  );
}

export function ProspectDetailModal({ 
  prospect: initialProspect, 
  onClose,
  onReject,
  onAccept,
  onAdvanceStatus,
  onNext,
  onPrev,
  hasPrev,
  inline
}: Props) {
  const [prospect, setProspect] = useState<Prospect>(initialProspect);
  // screenshot_path can be a full URL (Google/IG) or a local path
  const screenshotUrl = prospect.screenshot_path?.startsWith("http") 
    ? prospect.screenshot_path 
    : getScreenshotUrl(prospect.screenshot_path);
  const website = prospect.website || prospect.ig_website;
  const phone = prospect.phone || prospect.ig_phone;
  
  // Local UI States
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: prospect.name || "",
    phone: phone || "",
    website: website || "",
    address: prospect.address || "",
    instagram_url: prospect.instagram_url || "",
    instagram_handle: prospect.instagram_handle || "",
    category: prospect.category || "",
    maps_url: prospect.maps_url || "",
    screenshot_path: prospect.screenshot_path || "",
  });

  const [promptText, setPromptText] = useState(prospect.prompt_used || "");
  const [lovablePromptText, setLovablePromptText] = useState(prospect.lovable_prompt || "");
  const [isEditingPromptGpt, setIsEditingPromptGpt] = useState(false);
  const [isEditingPromptLovable, setIsEditingPromptLovable] = useState(false);
  const [demoUrl, setDemoUrl] = useState(prospect.demo_url || "");
  const [demoRating, setDemoRating] = useState(
    prospect.demo_rating != null ? String(prospect.demo_rating) : ""
  );
  const [demoAcc, setDemoAcc] = useState(prospect.lovable_account_used || "");
  const [waMsg, setWaMsg] = useState(prospect.whatsapp_message || "");

  const [loading, setLoading] = useState(false);
  const [loadingGptTemplate, setLoadingGptTemplate] = useState(false);
  const [loadingWaTemplate, setLoadingWaTemplate] = useState(false);
  const [copiedPromptGpt, setCopiedPromptGpt] = useState(false);
  const [copiedPromptLovable, setCopiedPromptLovable] = useState(false);
  const [isEditingDemoRating, setIsEditingDemoRating] = useState(false);

  const copyToClipboard = async (text: string, kind: "gpt" | "lovable") => {
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      if (kind === "gpt") {
        setCopiedPromptGpt(true);
        setTimeout(() => setCopiedPromptGpt(false), 1800);
      } else {
        setCopiedPromptLovable(true);
        setTimeout(() => setCopiedPromptLovable(false), 1800);
      }
    } catch {}
  };

  // Sync local state when parent passes a new prospect (e.g. arrow navigation)
  useEffect(() => {
    setProspect(initialProspect);
    const newWebsite = initialProspect.website || initialProspect.ig_website || "";
    const newPhone = initialProspect.phone || initialProspect.ig_phone || "";
    setEditForm({
      name: initialProspect.name || "",
      phone: newPhone,
      website: newWebsite,
      address: initialProspect.address || "",
      instagram_url: initialProspect.instagram_url || "",
      instagram_handle: initialProspect.instagram_handle || "",
      category: initialProspect.category || "",
      maps_url: initialProspect.maps_url || "",
      screenshot_path: initialProspect.screenshot_path || "",
    });
    setPromptText(initialProspect.prompt_used || "");
    setLovablePromptText(initialProspect.lovable_prompt || "");
    setDemoUrl(initialProspect.demo_url || "");
    setDemoRating(
      initialProspect.demo_rating != null ? String(initialProspect.demo_rating) : ""
    );
    setDemoAcc(initialProspect.lovable_account_used || "");
    setWaMsg(initialProspect.whatsapp_message || "");
    setIsEditing(false);
    setIsEditingPromptGpt(false);
    setIsEditingPromptLovable(false);
    setIsEditingDemoRating(false);
  }, [initialProspect]);

  // Computed
  const status = prospect.status || "scraped";
  const hasWebsite = Boolean(website);
  const hasGptPrompt = Boolean((prospect.prompt_used || promptText || "").trim());
  const showPromptGptCard =
    hasGptPrompt &&
    status !== "scraped" &&
    status !== "ready" &&
    status !== "waiting";

  const performUpdate = async (data: Partial<Prospect>) => {
    setLoading(true);
    try {
      const res = await updateProspect(
        prospect.name,
        data as Record<string, string | number | boolean | null>
      );
      if (res.ok) {
        setProspect(prev => ({ ...prev, ...data }));
        if (data.status && onAdvanceStatus) {
            onAdvanceStatus(data.status); // informs parent to refresh
        }
      } else {
        alert("Error al guardar en base de datos");
      }
    } catch(e) {
      alert("Error de red");
    } finally {
      setLoading(false);
    }
  };

  const handleEditSave = async () => {
    await performUpdate({
      name: editForm.name,
      phone: editForm.phone,
      website: editForm.website,
      address: editForm.address,
      instagram_url: editForm.instagram_url,
      instagram_handle: editForm.instagram_handle,
      category: editForm.category,
      maps_url: editForm.maps_url,
      screenshot_path: editForm.screenshot_path.trim(),
    });
    setIsEditing(false);
  };

  const editImagePreviewUrl =
    editForm.screenshot_path.trim().length === 0
      ? null
      : editForm.screenshot_path.trim().startsWith("http")
        ? editForm.screenshot_path.trim()
        : getScreenshotUrl(editForm.screenshot_path.trim());

  return (
    <div 
      className={inline ? "tinder-inline-container" : "modal"} 
      onClick={(e) => !inline && e.target === e.currentTarget && onClose()} 
      style={inline ? { display: 'flex', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center', position: 'relative' } : { display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      {onPrev && (
        <button 
          className="modal-nav-arrow left" 
          onClick={(e) => { e.stopPropagation(); onPrev(); }} 
          disabled={!hasPrev || loading}
          style={{ position: 'absolute', left: '2rem', border: 'none', background: 'transparent', color: hasPrev ? '#fff' : '#555', cursor: hasPrev ? 'pointer' : 'default', transition: 'transform 0.2s', transform: hasPrev ? 'scale(1)' : 'scale(0.9)', zIndex: 100 }}
        >
          <ChevronLeft size={64} />
        </button>
      )}

      <div className="modal-content prospect-detail-modal" onClick={(e) => e.stopPropagation()} style={{ overflowY: 'auto', maxHeight: '90vh' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <h2 style={{ margin: 0 }}>{LABELS.DETAIL_TITLE}</h2>
            <span className="prospect-detail-badge" style={{ background: "var(--accent-muted)", color: "var(--accent)" }}>
              {mapStatusToLabel(status)}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn-secondary" style={{ padding: '0.4rem 0.8rem', display: 'flex', gap: '0.4rem', fontSize: '0.85rem' }} onClick={() => setIsEditing(!isEditing)}>
              <Edit2 size={16} /> {isEditing ? "Cancelar" : "Editar Datos"}
            </button>
            <button className="close-btn" onClick={onClose} aria-label="Cerrar" disabled={loading}>×</button>
          </div>
        </header>

        {isEditing ? (
          <div className="fade-in-scale" style={{ background: 'var(--bg-base)', padding: '1.5rem', borderRadius: '12px', marginBottom: '1.5rem', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
            <h4 style={{ marginTop: 0, marginBottom: '1.25rem', color: 'var(--text-primary)', fontSize: '1rem' }}>Editar Información del Prospecto</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Nombre del negocio</label>
                <input type="text" className="dialog-input" value={editForm.name} onChange={e => setEditForm(f => ({...f, name: e.target.value}))} placeholder="Ej. Gran Restaurante" />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Categoría</label>
                <input type="text" className="dialog-input" value={editForm.category} onChange={e => setEditForm(f => ({...f, category: e.target.value}))} placeholder="cafe, restaurante..." />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Teléfono</label>
                <input type="text" className="dialog-input" value={editForm.phone} onChange={e => setEditForm(f => ({...f, phone: e.target.value}))} placeholder="300 000 0000" />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Sitio Web</label>
                <input type="text" className="dialog-input" value={editForm.website} onChange={e => setEditForm(f => ({...f, website: e.target.value}))} placeholder="https://..." />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Instagram URL</label>
                <input type="text" className="dialog-input" value={editForm.instagram_url} onChange={e => {
                  const val = e.target.value;
                  const handleMatch = val.match(/instagram\.com\/([^/?]+)/);
                  setEditForm(f => ({...f, instagram_url: val, instagram_handle: handleMatch ? handleMatch[1] : f.instagram_handle}));
                }} placeholder="https://instagram.com/usuario" />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Instagram @</label>
                <input type="text" className="dialog-input" value={editForm.instagram_handle} onChange={e => {
                  let val = e.target.value;
                  const handleMatch = val.match(/instagram\.com\/([^/?]+)/);
                  if (handleMatch) {
                    val = handleMatch[1];
                  }
                  val = val.replace(/^@/, '');
                  setEditForm(f => ({...f, instagram_handle: val}));
                }} placeholder="usuario" />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Dirección</label>
                <input type="text" className="dialog-input" value={editForm.address} onChange={e => setEditForm(f => ({...f, address: e.target.value}))} placeholder="Calle 1 # 2-3" />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Imagen / logo (URL o nombre de archivo en capturas)</label>
                <input
                  type="text"
                  className="dialog-input"
                  value={editForm.screenshot_path}
                  onChange={(e) => setEditForm((f) => ({ ...f, screenshot_path: e.target.value }))}
                  placeholder="https://… (imagen pública) o archivo guardado en data/screenshots"
                />
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                  Deja vacío para quitar la imagen. URLs https se muestran tal cual; rutas locales usan el servidor de capturas.
                </p>
                {editImagePreviewUrl ? (
                  <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <img
                      src={editImagePreviewUrl}
                      alt=""
                      style={{
                        width: 72,
                        height: 72,
                        borderRadius: 10,
                        objectFit: "cover",
                        border: "1px solid var(--border)",
                        background: "var(--bg-elevated)",
                      }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Vista previa</span>
                  </div>
                ) : null}
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Google Maps URL</label>
                <input type="text" className="dialog-input" value={editForm.maps_url} onChange={e => setEditForm(f => ({...f, maps_url: e.target.value}))} placeholder="https://maps.google.com/..." />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <button className="btn-primary" onClick={handleEditSave} disabled={loading} style={{ width: '100%', padding: '0.8rem' }}>
                  {loading ? "Guardando..." : "Guardar Cambios"}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="prospect-detail-grid">
              <div>
                {screenshotUrl ? (
                  <img src={screenshotUrl} alt="" className="prospect-detail-logo" />
                ) : (
                  <div className="prospect-detail-logo" style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "2.5rem" }}>
                    {prospect.name.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              <div className="prospect-detail-main">
                <h2>{prospect.name}</h2>
                <div className="meta" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.9rem', flexWrap: 'wrap' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'rgba(255,255,255,0.05)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                    {getCategoryIcon(prospect.category)} 
                    <span style={{ textTransform: 'capitalize' }}>{prospect.category || "—"}</span>
                  </span>
                  <span>·</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                     <MapPin size={14} /> {prospect.address || "—"}
                  </span>
                </div>
                {prospect.lead_score != null && (
                  <div style={{ marginTop: '0.6rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Score: {prospect.lead_score}
                  </div>
                )}
              </div>
            </div>

            <div className="prospect-detail-section">
              <InfoRow label={LABELS.PHONE} value={phone} />
              <InfoRow label="Web" value={website} href={website} />
              <InfoRow label="Instagram" value={prospect.instagram_handle || prospect.instagram_url} href={prospect.instagram_url} />
              <InfoRow label="Google Maps" value={prospect.maps_url ? "Abrir en Maps" : ""} href={prospect.maps_url} />
            </div>

            {/* Render saved data implicitly */}
            {showPromptGptCard && (
              <div className="prospect-detail-section" style={{ background: 'rgba(245, 158, 11, 0.05)', borderLeft: '3px solid #f59e0b', padding: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <h4 style={{ color: '#f59e0b', margin: 0, display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                    Prompt GPT
                    <span title="Prompt para ChatGPT (estrategia y copy base)" style={{ display: "inline-flex", cursor: "help" }}>
                      <Info size={14} />
                    </span>
                  </h4>
                  <div style={{ display: "flex", gap: "0.35rem" }}>
                    <button
                      className="btn-secondary"
                      style={{
                        padding: '0.3rem 0.5rem',
                        fontSize: '0.78rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        background: copiedPromptGpt ? '#2ea043' : undefined,
                        borderColor: copiedPromptGpt ? '#2ea043' : undefined,
                        color: copiedPromptGpt ? '#fff' : undefined
                      }}
                      onClick={() => copyToClipboard(promptText, "gpt")}
                      disabled={loading || !promptText.trim()}
                      title="Copiar Prompt GPT"
                    >
                      {copiedPromptGpt ? <ClipboardCheck size={14} /> : <Clipboard size={14} />}
                      {copiedPromptGpt ? "Copiado" : "Copiar"}
                    </button>
                    <button
                      className="btn-secondary"
                      style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                      onClick={() => setIsEditingPromptGpt(v => !v)}
                      disabled={loading}
                    >
                      <Edit2 size={14} />
                      {isEditingPromptGpt ? "Bloquear" : "Editar"}
                    </button>
                  </div>
                </div>
                <textarea
                  className="dialog-input"
                  rows={4}
                  value={promptText}
                  onChange={e => setPromptText(e.target.value)}
                  placeholder="Escribe o edita aquí el prompt GPT..."
                  readOnly={!isEditingPromptGpt}
                  style={!isEditingPromptGpt ? { opacity: 0.9, cursor: 'default' } : undefined}
                />
                {isEditingPromptGpt && promptText !== (prospect.prompt_used || "") && (
                  <button
                    className="btn-secondary"
                    style={{ marginTop: '0.65rem' }}
                    onClick={async () => {
                      await performUpdate({ prompt_used: promptText });
                      setIsEditingPromptGpt(false);
                    }}
                    disabled={loading}
                  >
                    Guardar Prompt GPT
                  </button>
                )}
              </div>
            )}
            {Boolean(prospect.lovable_prompt?.trim()) && (
              <div className="prospect-detail-section" style={{ background: 'rgba(167, 139, 250, 0.08)', borderLeft: '3px solid #a78bfa', padding: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <h4 style={{ color: '#a78bfa', margin: 0, display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                    Prompt Lovable
                    <span title="Prompt final que pegas directamente en Lovable" style={{ display: "inline-flex", cursor: "help" }}>
                      <Info size={14} />
                    </span>
                  </h4>
                  <div style={{ display: "flex", gap: "0.35rem" }}>
                    <button
                      className="btn-secondary"
                      style={{
                        padding: '0.3rem 0.5rem',
                        fontSize: '0.78rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        background: copiedPromptLovable ? '#2ea043' : undefined,
                        borderColor: copiedPromptLovable ? '#2ea043' : undefined,
                        color: copiedPromptLovable ? '#fff' : undefined
                      }}
                      onClick={() => copyToClipboard(lovablePromptText, "lovable")}
                      disabled={loading || !lovablePromptText.trim()}
                      title="Copiar Prompt Lovable"
                    >
                      {copiedPromptLovable ? <ClipboardCheck size={14} /> : <Clipboard size={14} />}
                      {copiedPromptLovable ? "Copiado" : "Copiar"}
                    </button>
                    <button
                      className="btn-secondary"
                      style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                      onClick={() => setIsEditingPromptLovable(v => !v)}
                      disabled={loading}
                    >
                      <Edit2 size={14} />
                      {isEditingPromptLovable ? "Bloquear" : "Editar"}
                    </button>
                  </div>
                </div>
                <textarea
                  className="dialog-input"
                  rows={4}
                  value={lovablePromptText}
                  onChange={e => setLovablePromptText(e.target.value)}
                  placeholder="Escribe o edita aquí el prompt para Lovable..."
                  readOnly={!isEditingPromptLovable}
                  style={!isEditingPromptLovable ? { opacity: 0.9, cursor: 'default' } : undefined}
                />
                {isEditingPromptLovable && lovablePromptText !== (prospect.lovable_prompt || "") && (
                  <button
                    className="btn-secondary"
                    style={{ marginTop: '0.65rem' }}
                    onClick={async () => {
                      await performUpdate({ lovable_prompt: lovablePromptText });
                      setIsEditingPromptLovable(false);
                    }}
                    disabled={loading}
                  >
                    Guardar Prompt Lovable
                  </button>
                )}
              </div>
            )}
            {prospect.demo_url && (
               <div className="prospect-detail-section" style={{ background: 'rgba(167, 139, 250, 0.05)', borderLeft: '3px solid #a78bfa', padding: '0.75rem' }}>
                 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                   <h4 style={{ color: '#a78bfa', margin: 0 }}>Demo Lovable</h4>
                   <button
                     className="btn-secondary"
                     style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                     onClick={() => setIsEditingDemoRating(v => !v)}
                     disabled={loading}
                   >
                     <Edit2 size={14} />
                     {isEditingDemoRating ? "Bloquear" : "Editar rating"}
                   </button>
                 </div>
                 <InfoRow label="URL" value="Ver Demo" href={prospect.demo_url} />
                 <InfoRow label="Cuenta Usada" value={prospect.lovable_account_used} />
                 <InfoRow label="Rating" value={prospect.demo_rating != null ? `${prospect.demo_rating}/10` : "—"} />
                 {isEditingDemoRating && (
                   <div style={{ marginTop: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: 10, padding: '0.5rem 0.6rem' }}>
                     {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((star) => {
                       const currentStars = Math.round(Number(demoRating || 0));
                       const active = star <= currentStars;
                       return (
                         <button
                           key={star}
                           type="button"
                           onClick={() => setDemoRating(String(star))}
                           className={active ? "btn-primary" : "btn-secondary"}
                           style={{
                             padding: '0.3rem 0.4rem',
                             minWidth: 30,
                             minHeight: 30,
                             borderRadius: 8,
                             fontWeight: 700,
                             background: active ? '#a78bfa' : 'rgba(255,255,255,0.05)',
                             borderColor: active ? '#a78bfa' : 'var(--border)',
                             color: active ? '#fff' : 'var(--text-muted)'
                           }}
                         >
                           ★
                         </button>
                       );
                     })}
                     <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: '0.35rem' }}>
                       {Number(demoRating || 0)}/10
                     </span>
                     {Number(demoRating || 0) !== Number(prospect.demo_rating || 0) && (
                       <button
                         className="btn-secondary"
                         style={{ marginLeft: '0.5rem', padding: '0.3rem 0.55rem', fontSize: '0.78rem' }}
                         onClick={async () => {
                           await performUpdate({ demo_rating: Number(demoRating || 0) });
                           setIsEditingDemoRating(false);
                         }}
                         disabled={loading}
                       >
                         Guardar rating
                       </button>
                     )}
                   </div>
                 )}
               </div>
            )}
            {prospect.whatsapp_message && (
               <div className="prospect-detail-section" style={{ background: 'rgba(46, 160, 67, 0.05)', borderLeft: '3px solid #2ea043', padding: '0.75rem' }}>
                 <h4 style={{ color: '#2ea043' }}>Mensaje Enviado</h4>
                 <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>{prospect.whatsapp_message}</p>
               </div>
            )}
          </>
        )}

        {/* GUIDED ASSISTANT LOGIC */}
        {!isEditing && (
          <div style={{ marginTop: '2rem', borderTop: '2px dashed var(--border)', paddingTop: '1.5rem' }}>
            
            {status === "scraped" && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <button 
                    className="btn-danger" 
                    onClick={() => onReject ? onReject() : performUpdate({ status: 'rejected' })} 
                    style={{ padding: '1.5rem', fontSize: '1.25rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}
                    disabled={loading}
                  >
                    <X size={32} /> Rechazar
                  </button>
                  <button 
                    className="btn-primary" 
                    onClick={() => (inline && onAccept) ? onAccept() : performUpdate({ status: 'ready' })} 
                    style={{ padding: '1.5rem', fontSize: '1.25rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', background: '#58a6ff' }}
                    disabled={loading}
                  >
                    <CheckCircle size={32} /> Aceptar
                  </button>
                </div>
                
                {hasWebsite && (
                  <button 
                    className="btn-secondary" 
                    onClick={() => performUpdate({ status: 'has_website' })} // Move to another list
                    style={{ width: '100%', padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                    disabled={loading}
                  >
                    <Globe size={20} /> Ya tiene Web ➔ Mover a lista
                  </button>
                )}
              </div>
            )}

            {(status === "ready" || status === "waiting") && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <h3 style={{ margin: 0, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  1. Generar Prompt
                  <span title="Este prompt se usa en GPT para obtener el texto base y luego construir el prompt de Lovable." style={{ display: "inline-flex", cursor: "help" }}>
                    <Info size={15} />
                  </span>
                </h3>
                <p style={{ color: 'var(--text-muted)' }}>Para crear la IA, necesitamos generar su contexto inicial.</p>
                <button
                  className="btn-secondary"
                  onClick={async () => {
                    setLoadingGptTemplate(true);
                    try {
                      const settings = await fetchAdminSettings();
                      const gptTemplate =
                        settings.whatsapp_templates.find(t => t.id === "gpt_hero")?.template ||
                        settings.whatsapp_templates.find(t => t.kind === "gpt")?.template;
                      if (!gptTemplate) {
                        alert("No hay plantilla GPT configurada en Admin > Plantillas.");
                        return;
                      }
                      setPromptText(renderTemplateWithProspect(gptTemplate, prospect));
                    } catch {
                      alert("No se pudo cargar la plantilla GPT.");
                    } finally {
                      setLoadingGptTemplate(false);
                    }
                  }}
                  disabled={loading || loadingGptTemplate}
                  style={{ alignSelf: 'flex-start' }}
                >
                  {loadingGptTemplate ? "Cargando plantilla..." : "Usar plantilla GPT automática"}
                </button>
                <textarea 
                  className="dialog-input" 
                  rows={5} 
                  value={promptText} 
                  onChange={e => setPromptText(e.target.value)} 
                  placeholder="Pega aquí el prompt generado por GPT..."
                />
                <button 
                  className="btn-primary" 
                  style={{ background: '#f59e0b' }} 
                  onClick={() => performUpdate({ status: 'prompt_gpt', prompt_used: promptText })}
                  disabled={!promptText.trim() || loading}
                >
                  <Sparkles size={18} style={{ marginRight: '6px' }}/> Guardar Prompt y Continuar
                </button>
              </div>
            )}

            {status === "prompt_gpt" && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <h3 style={{ margin: 0, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  2. Crear Demo de Lovable
                  <span title="Aquí guardas el prompt final para Lovable y los datos de la demo creada." style={{ display: "inline-flex", cursor: "help" }}>
                    <Info size={15} />
                  </span>
                </h3>
                <p style={{ color: 'var(--text-muted)' }}>Crea la demo y pega la URL y la cuenta de correo usada.</p>
                <textarea
                  className="dialog-input"
                  rows={4}
                  value={lovablePromptText}
                  onChange={e => setLovablePromptText(e.target.value)}
                  placeholder="Prompt final para Lovable..."
                />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                  <label style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Califica la demo (estrellas)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: 10, padding: '0.5rem 0.6rem' }}>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((star) => {
                      const currentStars = Math.round(Number(demoRating || 0));
                      const active = star <= currentStars;
                      return (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setDemoRating(String(star))}
                          className={active ? "btn-primary" : "btn-secondary"}
                          style={{
                            padding: '0.3rem 0.4rem',
                            minWidth: 30,
                            minHeight: 30,
                            borderRadius: 8,
                            fontWeight: 700,
                            background: active ? '#a78bfa' : 'rgba(255,255,255,0.05)',
                            borderColor: active ? '#a78bfa' : 'var(--border)',
                            color: active ? '#fff' : 'var(--text-muted)'
                          }}
                        >
                          ★
                        </button>
                      );
                    })}
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: '0.35rem' }}>
                      {Number(demoRating || 0)}/10
                    </span>
                  </div>
                </div>
                <input 
                  type="text" 
                  className="dialog-input" 
                  value={demoUrl} 
                  onChange={e => setDemoUrl(e.target.value)} 
                  placeholder="URL de la Demo (https://...)" 
                />
                <input 
                  type="text" 
                  className="dialog-input" 
                  value={demoAcc} 
                  onChange={e => setDemoAcc(e.target.value)} 
                  placeholder="Correo / Cuenta usada en Lovable" 
                />
                <button 
                  className="btn-primary" 
                  style={{ background: '#a78bfa' }} 
                  onClick={() => performUpdate({ status: 'demo_created', demo_url: demoUrl, lovable_account_used: demoAcc, lovable_prompt: lovablePromptText, demo_rating: Number(demoRating || 0) })}
                  disabled={!demoUrl.trim() || !demoAcc.trim() || !lovablePromptText.trim() || Number(demoRating || 0) <= 0 || loading}
                >
                  <CheckCircle size={18} style={{ marginRight: '6px' }}/> Guardar Demo y Continuar
                </button>
              </div>
            )}

            {status === "demo_created" && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>3. Redactar Pitch de WhatsApp</h3>
                <p style={{ color: 'var(--text-muted)' }}>Escribe o personaliza el mensaje antes de enviarlo por WhatsApp.</p>
                <button
                  className="btn-secondary"
                  onClick={async () => {
                    setLoadingWaTemplate(true);
                    try {
                      const settings = await fetchAdminSettings();
                      const waTemplate =
                        settings.whatsapp_templates.find(t => t.id === "first_contact")?.template ||
                        settings.whatsapp_templates.find(t => t.kind === "whatsapp")?.template;
                      if (!waTemplate) {
                        alert("No hay plantilla de WhatsApp configurada en Admin > Plantillas.");
                        return;
                      }
                      setWaMsg(renderTemplateWithProspect(waTemplate, prospect));
                    } catch {
                      alert("No se pudo cargar la plantilla de WhatsApp.");
                    } finally {
                      setLoadingWaTemplate(false);
                    }
                  }}
                  disabled={loading || loadingWaTemplate}
                  style={{ alignSelf: 'flex-start' }}
                >
                  {loadingWaTemplate ? "Cargando plantilla..." : "Autocompletar plantilla"}
                </button>
                <textarea 
                  className="dialog-input" 
                  rows={6} 
                  value={waMsg} 
                  onChange={e => setWaMsg(e.target.value)} 
                  placeholder="¡Hola! Pasaba por..."
                />
                <button 
                  className="btn-primary" 
                  style={{ background: '#2ea043' }} 
                  onClick={async () => {
                    await performUpdate({ status: 'contacted', whatsapp_message: waMsg });
                    // Open WA Window
                    const targetPhone = phone ? phone.replace(/\D/g, "") : ""; 
                    if(targetPhone) {
                       window.open(`https://wa.me/${targetPhone}?text=${encodeURIComponent(waMsg)}`, "_blank");
                    } else {
                       alert("El prospecto no tiene número telefónico para abrir WhatsApp automáticamente.");
                    }
                  }}
                  disabled={!waMsg.trim() || loading}
                >
                  <Send size={18} style={{ marginRight: '6px' }}/> Guardar y Enviar WhatsApp
                </button>
              </div>
            )}

            {status === "contacted" && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', textAlign: 'center', padding: '1rem' }}>
                <div>
                  <CheckCircle size={48} color="#2ea043" style={{ marginBottom: '1rem' }} />
                  <h3>¡Prospecto Contactado!</h3>
                  <p style={{ color: 'var(--text-muted)' }}>Marca el resultado de la propuesta cuando el cliente responda.</p>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <button
                    className="btn-danger"
                    onClick={() => performUpdate({ status: 'rejected' })}
                    style={{ padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                    disabled={loading}
                  >
                    <X size={18} /> No aceptó propuesta
                  </button>
                  <button
                    className="btn-primary"
                    onClick={() => performUpdate({ status: 'client_won' })}
                    style={{ padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                    disabled={loading}
                  >
                    <CheckCircle size={18} /> Sí aceptó propuesta
                  </button>
                </div>
              </div>
            )}

            {status === "has_website" && (
              <div style={{ textAlign: 'center', padding: '1rem' }}>
                <Globe size={48} color="#58a6ff" style={{ marginBottom: '1rem' }} />
                <h3>En Lista de Espera (Con Web)</h3>
                <p style={{ color: 'var(--text-muted)' }}>Este prospecto ya tiene página web. Quedará en esta lista para abordarlo en un momento distinto.</p>
              </div>
            )}

            {status === "rejected" && (
              <div style={{ textAlign: 'center', padding: '1rem' }}>
                <X size={48} color="#64748b" style={{ marginBottom: '1rem' }} />
                <h3>Prospecto Rechazado</h3>
                <p style={{ color: 'var(--text-muted)' }}>El negocio no aceptó la propuesta en este momento.</p>
              </div>
            )}

          </div>
        )}
      </div>

      {onNext && (
        <button 
          className="modal-nav-arrow right" 
          onClick={(e) => { e.stopPropagation(); onNext(); }}
          style={{ position: 'absolute', right: '2rem', border: 'none', background: 'transparent', color: '#fff', cursor: 'pointer', transition: 'transform 0.2s', zIndex: 100 }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.1)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
          disabled={loading}
        >
          <ChevronRight size={64} />
        </button>
      )}
    </div>
  );
}
