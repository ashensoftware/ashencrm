import { LABELS } from "../../constants";

interface Props {
  title: string;
  message: string;
  defaultValue: string;
  options: { name: string; label: string }[] | null;
  onConfirm: (value: string | null) => void;
  onCancel: () => void;
}

export function PromptModal({ title, message, defaultValue, options, onConfirm, onCancel }: Props) {
  const handleConfirm = () => {
    const el = options
      ? document.getElementById("prompt-select") as HTMLSelectElement
      : document.getElementById("prompt-input") as HTMLInputElement;
    onConfirm(el?.value ?? null);
  };

  return (
    <div className="modal">
      <div className="modal-content small-modal">
        <header>
          <h2>{title}</h2>
        </header>
        <p style={{ marginBottom: "1rem", color: "var(--text-secondary)" }}>{message}</p>
        {options ? (
          <select
            id="prompt-select"
            className="search-input"
            style={{ width: "100%", marginTop: "1rem" }}
            defaultValue={defaultValue}
          >
            {options.map((o) => (
              <option key={o.name} value={o.name}>{o.label}</option>
            ))}
          </select>
        ) : (
          <input
            id="prompt-input"
            type="text"
            className="search-input"
            placeholder={LABELS.WRITE_HERE}
            defaultValue={defaultValue}
            style={{ marginTop: "1rem" }}
          />
        )}
        <div className="modal-actions" style={{ marginTop: "1.5rem" }}>
          <button className="btn-secondary" onClick={onCancel}>{LABELS.CANCEL}</button>
          <button className="btn-primary" onClick={handleConfirm}>{LABELS.ACCEPT}</button>
        </div>
      </div>
    </div>
  );
}
