import { useState, useRef, useEffect } from "react";
import type { Prospect } from "../types";
import { ProspectDetailModal } from "../organisms/modals/ProspectDetailModal";
import { Check, X as XIcon, ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  prospect: Prospect | null;
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
}

export function TinderPage(props: Props) {
  const [dragX, setDragX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing
      if (["input", "textarea"].includes((e.target as HTMLElement)?.tagName.toLowerCase())) return;
      if (e.key === "ArrowRight") {
        if (props.onNext) props.onNext();
      } else if (e.key === "ArrowLeft") {
        if (props.hasPrev && props.onPrev) props.onPrev();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [props.onNext, props.onPrev, props.hasPrev]);

  if (!props.prospect) {
    return (
      <div style={{ width: "100%", height: "100%", backgroundColor: "var(--bg-base)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "var(--text-muted)" }}>Cargando prospecto aleatorio...</p>
      </div>
    );
  }

  const isScraped = props.prospect.status === 'scraped';

  const handlePointerDown = (e: React.PointerEvent) => {
    const target = e.target as HTMLElement;
    if (["input", "textarea", "button", "a", "select"].includes(target.tagName.toLowerCase())) return;
    if (target.closest('button') || target.closest('a')) return;
    
    startX.current = e.clientX - dragX;
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    setDragX(e.clientX - startX.current);
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!isDragging) return;
    setIsDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);

    const THRESHOLD = window.innerWidth * 0.15; // 15% width needed to trigger

    if (dragX > THRESHOLD) {
      if (isScraped && props.onAccept) props.onAccept();
      else if (!isScraped && props.onPrev) props.onPrev();
    } else if (dragX < -THRESHOLD) {
      if (isScraped && props.onReject) props.onReject();
      else if (!isScraped && props.onNext) props.onNext();
    }
    
    setDragX(0); 
  };

  const ratio = Math.min(Math.abs(dragX) / 150, 1);
  const bgColor = dragX > 0 
    ? (isScraped ? `rgba(46, 160, 67, ${ratio * 0.6})` : `rgba(88, 166, 255, ${ratio * 0.5})`) 
    : `rgba(248, 81, 73, ${ratio * 0.6})`;

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", backgroundColor: "var(--bg-base)", overflow: "hidden" }}>
      
      {/* Background Overlay Feedback */}
      <div style={{ position: "absolute", inset: 0, backgroundColor: bgColor, pointerEvents: "none", zIndex: 1, display: "flex", alignItems: "center", justifyContent: dragX > 0 ? "flex-start" : "flex-end", padding: "4rem", transition: isDragging ? "none" : "background-color 0.3s" }}>
         {dragX > 50 && (
           <div style={{ color: "white", display: "flex", flexDirection: "column", alignItems: "center", opacity: ratio }}>
             {isScraped ? <Check size={80} /> : <ChevronLeft size={80} />}
             <h2>{isScraped ? "Aceptar" : "Atrás"}</h2>
           </div>
         )}
         {dragX < -50 && (
           <div style={{ color: "white", display: "flex", flexDirection: "column", alignItems: "center", opacity: ratio }}>
             {isScraped ? <XIcon size={80} /> : <ChevronRight size={80} />}
             <h2>{isScraped ? "Rechazar" : "Siguiente"}</h2>
           </div>
         )}
      </div>

      <div 
        style={{ 
          width: "100%", height: "100%", 
          transform: `translateX(${dragX}px) rotate(${dragX * 0.05}deg)`, 
          transition: isDragging ? "none" : "transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
          zIndex: 10,
          position: "relative",
          cursor: isDragging ? "grabbing" : "grab",
          touchAction: "none"
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <ProspectDetailModal {...props} prospect={props.prospect} inline={true} />
      </div>
    </div>
  );
}
