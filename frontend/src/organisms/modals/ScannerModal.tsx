import { LABELS } from "../../constants";

interface Props {
  logs: string[];
  active: boolean;
  onMinimize: () => void;
}

export function ScannerModal({ logs, active, onMinimize }: Props) {
  const logClass = (log: string) => {
    if (log.includes("FINALIZADO") || log.includes("nuevos")) return "text-success";
    if (log.includes("ERROR")) return "text-danger";
    return "text-secondary";
  };

  return (
    <div className="modal">
      <div className="modal-content terminal-modal">
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "1rem", borderBottom: "1px solid var(--border)" }}>
          <h2>{LABELS.SCANNER_TITLE}</h2>
          <button className="close-btn" onClick={onMinimize}>×</button>
        </header>
        <div className="terminal-body" style={{ maxHeight: 320, overflowY: "auto" }}>
          {logs.map((log, i) => (
            <div key={i} className={`log-line ${logClass(log)}`}>{log}</div>
          ))}
        </div>
        <div style={{ padding: "1rem", borderTop: "1px solid var(--border)" }}>
          <span className={active ? "terminal-status active" : "terminal-status"}>
            {active ? LABELS.SCANNING : LABELS.COMPLETED}
          </span>
        </div>
      </div>
    </div>
  );
}
