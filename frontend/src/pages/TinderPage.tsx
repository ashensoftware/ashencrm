import type { Prospect } from "../types";
import { ProspectDetailModal } from "../organisms/modals/ProspectDetailModal";

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
  if (!props.prospect) {
    return (
      <div style={{ width: "100%", height: "100%", backgroundColor: "var(--bg-base)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "var(--text-muted)" }}>Cargando prospecto aleatorio...</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", backgroundColor: "var(--bg-base)" }}>
      <ProspectDetailModal {...props} prospect={props.prospect} inline={true} />
    </div>
  );
}
