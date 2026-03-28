import type { Prospect } from "../../types";
import { getScreenshotUrl } from "../../api";
import { mapStatusToLabel } from "../../utils";
import { LABELS, WHATSAPP_TEMPLATES } from "../../constants";
import { X, Check, CheckCircle, ChevronRight, ChevronLeft, MessageCircle, Sparkles, Info, ArrowRight, ChevronDown } from "lucide-react";
import { useState } from "react";

const PIPELINE_STEPS: Record<string, { nextStatus: string; label: string; color: string }> = {
  ready:        { nextStatus: "prompt_gpt",    label: "Iniciar Prompt GPT",   color: "#58a6ff" },
  prompt_gpt:   { nextStatus: "creating_demo", label: "Ya generé el prompt",  color: "#f59e0b" },
  creating_demo:{ nextStatus: "demo_created",  label: "Ya creé la demo",      color: "#f97316" },
  demo_created: { nextStatus: "contacted",     label: "Ya contacté al cliente", color: "#a78bfa" },
  contacted:    { nextStatus: "client_won",    label: "Cliente obtenido",     color: "#2ea043" },
};

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
  prospect, 
  onClose,
  onReject,
  onAccept,
  onContact,
  onWhatsApp,
  onGenerateDemo,
  onAdvanceStatus,
  onNext,
  onPrev,
  hasPrev,
  inline
}: Props) {
  const screenshotUrl = getScreenshotUrl(prospect.screenshot_path);
  const website = prospect.website || prospect.ig_website;
  const phone = prospect.phone || prospect.ig_phone;
  const pipelineStep = PIPELINE_STEPS[prospect.status || ""];
  const [waMenuOpen, setWaMenuOpen] = useState(false);

  const handleWhatsAppAction = (templateId?: string) => {
    if (!templateId) {
      if (onWhatsApp) onWhatsApp();
      setWaMenuOpen(false);
      return;
    }
    
    const template = WHATSAPP_TEMPLATES.find(t => t.id === templateId);
    if (template) {
      let msg = template.template;
      msg = msg.replace(/{name}/g, prospect.name || "empresa");
      msg = msg.replace(/{category}/g, prospect.category || "negocio");
      msg = msg.replace(/{followers}/g, String(prospect.ig_followers || "0"));
      
      const phoneInfo = prospect.phone || prospect.ig_phone || "";
      const cleanPhone = phoneInfo.replace(/\D/g, "");
      
      const url = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}`;
      window.open(url, "_blank");
    }
    setWaMenuOpen(false);
  };

  return (
    <div 
      className={inline ? "tinder-inline-container" : "modal"} 
      onClick={(e) => !inline && e.target === e.currentTarget && onClose()} 
      style={inline ? { display: 'flex', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center', position: 'relative' } : { display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      {onPrev && (
        <button 
          className="modal-nav-arrow left" 
          onClick={onPrev} 
          disabled={!hasPrev}
          style={{ position: 'absolute', left: '2rem', border: 'none', background: 'transparent', color: hasPrev ? '#fff' : '#555', cursor: hasPrev ? 'pointer' : 'default', transition: 'transform 0.2s', transform: hasPrev ? 'scale(1)' : 'scale(0.9)', zIndex: 100 }}
        >
          <ChevronLeft size={64} />
        </button>
      )}

      <div className="modal-content prospect-detail-modal" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>{LABELS.DETAIL_TITLE}</h2>
          <button className="close-btn" onClick={onClose} aria-label="Cerrar">×</button>
        </header>

        <div className="prospect-detail-grid">
          <div>
            {screenshotUrl ? (
              <img src={screenshotUrl} alt="" className="prospect-detail-logo" />
            ) : (
              <div
                className="prospect-detail-logo"
                style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "2.5rem" }}
              >
                {prospect.name.charAt(0).toUpperCase()}
              </div>
            )}
          </div>
          <div className="prospect-detail-main">
            <h2>{prospect.name}</h2>
            <p className="meta">{prospect.category || "—"} · {prospect.address || "—"}</p>
            <span className="prospect-detail-badge" style={{ background: "var(--accent-muted)", color: "var(--accent)" }}>
              {mapStatusToLabel(prospect.status)}
            </span>
            {prospect.lead_score != null && (
              <div style={{ marginTop: '0.6rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="prospect-detail-badge" style={{ background: "var(--success-muted)", color: "var(--success)" }}>
                  Score: {prospect.lead_score}
                </span>
                <span title="Calidad del prospecto basada en seguidores, web, etc." style={{ cursor: 'help', color: 'var(--text-secondary)' }}>
                  <Info size={14} />
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="prospect-detail-section">
          <h4>{LABELS.CONTACT_SECTION}</h4>
          <InfoRow label={LABELS.PHONE} value={phone} />
          <InfoRow label="Web" value={website} href={website} />
          <InfoRow label="Instagram" value={prospect.instagram_handle || prospect.instagram_url} href={prospect.instagram_url} />
          <InfoRow label="Email" value={prospect.ig_email} />
        </div>

        {(prospect.ig_bio || prospect.ig_followers) && (
          <div className="prospect-detail-section">
            <h4>{LABELS.INSTAGRAM_SECTION}</h4>
            {prospect.ig_followers ? <InfoRow label={LABELS.FOLLOWERS} value={String(prospect.ig_followers)} /> : null}
            {prospect.ig_bio ? <p>{prospect.ig_bio}</p> : null}
          </div>
        )}

        {(prospect.rating || prospect.reviews_count) ? (
          <div className="prospect-detail-section">
            <h4>{LABELS.MAPS_SECTION}</h4>
            <InfoRow label={LABELS.RATING} value={prospect.rating ? `${prospect.rating} ⭐` : undefined} />
            <InfoRow label={LABELS.REVIEWS} value={prospect.reviews_count ? String(prospect.reviews_count) : undefined} />
            <InfoRow label={LABELS.MAP_VIEW} value={LABELS.MAP_OPEN} href={prospect.maps_url} />
          </div>
        ) : prospect.maps_url ? (
          <div className="prospect-detail-section">
            <InfoRow label={LABELS.MAPS_SECTION} value={LABELS.MAP_OPEN} href={prospect.maps_url} />
          </div>
        ) : null}

        {prospect.demo_url && (
          <div className="prospect-detail-section">
            <h4>{LABELS.DEMO_SECTION}</h4>
            <InfoRow label="URL" value={LABELS.DEMO_VIEW} href={prospect.demo_url} />
          </div>
        )}

        {prospect.notes && (
          <div className="prospect-detail-section">
            <h4>{LABELS.NOTES_SECTION}</h4>
            <p>{prospect.notes}</p>
          </div>
        )}

        {/* PIPELINE PROGRESSION */}
        {pipelineStep && onAdvanceStatus && (
          <div style={{ marginTop: '1.25rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem', fontWeight: 600 }}>Siguiente Paso</p>
            <button
              onClick={() => onAdvanceStatus(pipelineStep.nextStatus)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                background: `${pipelineStep.color}22`,
                border: `1px solid ${pipelineStep.color}55`,
                borderRadius: 'var(--radius-sm)',
                color: pipelineStep.color,
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = `${pipelineStep.color}33`; e.currentTarget.style.transform = 'translateY(-1px)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = `${pipelineStep.color}22`; e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              <ArrowRight size={18} /> {pipelineStep.label}
            </button>
          </div>
        )}

        {/* CONTROLES DE ACCIÓN (TINDER / REVISIÓN) */}
        <div className="prospect-detail-actions" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div style={{ position: 'relative' }}>
              {onWhatsApp && (
                <button 
                  className="btn-whatsapp" 
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', width: '100%' }} 
                  onClick={() => setWaMenuOpen(!waMenuOpen)}
                >
                  <MessageCircle size={18} /> WhatsApp <ChevronDown size={14} />
                </button>
              )}
              {waMenuOpen && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  width: '100%',
                  marginTop: '0.5rem',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
                  zIndex: 200,
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden'
                }}>
                  {WHATSAPP_TEMPLATES.map(t => (
                    <button
                      key={t.id}
                      onClick={() => handleWhatsAppAction(t.id)}
                      style={{
                        padding: '0.75rem 1rem',
                        background: 'transparent',
                        border: 'none',
                        borderBottom: '1px solid var(--border)',
                        color: 'var(--text-primary)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        fontSize: '0.85rem'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      {t.name}
                    </button>
                  ))}
                  <button
                    onClick={() => handleWhatsAppAction()}
                    style={{
                      padding: '0.75rem 1rem',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--accent)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: 600
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    🚀 Enviar con Bot
                  </button>
                </div>
              )}
            </div>
            {onGenerateDemo && (
               <button className="btn-primary-alt" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={onGenerateDemo}>
                 <Sparkles size={18} /> Ingresar Link Demo
               </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {onReject && (
              <button className="btn-danger" onClick={onReject} title="Rechazar prospecto" style={{ padding: '0.6rem', flex: '0 0 auto' }}>
                <X size={20} />
              </button>
            )}
            {onContact && (
              <button className="btn-primary" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={onContact}>
                <Check size={18} /> Contactado
              </button>
            )}
            {onAccept && (
              <button className="btn-success" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={onAccept}>
                <CheckCircle size={18} /> Aceptar / Guardar
              </button>
            )}
          </div>
        </div>

      </div>

      {onNext && (
        <button 
          className="modal-nav-arrow right" 
          onClick={onNext}
          style={{ position: 'absolute', right: '2rem', border: 'none', background: 'transparent', color: '#fff', cursor: 'pointer', transition: 'transform 0.2s', zIndex: 100 }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.1)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <ChevronRight size={64} />
        </button>
      )}
    </div>
  );
}
