import { LABELS } from "../../constants";

interface Props {
  title: string;
  message: string;
  onClose: () => void;
}

export function AlertModal({ title, message, onClose }: Props) {
  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content small-modal">
        <header>
          <h2>{title}</h2>
        </header>
        <p style={{ marginBottom: "1.5rem" }}>{message}</p>
        <div className="modal-actions">
          <button className="btn-primary" onClick={onClose}>{LABELS.UNDERSTOOD}</button>
        </div>
      </div>
    </div>
  );
}
