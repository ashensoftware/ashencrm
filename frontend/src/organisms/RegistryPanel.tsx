import { LABELS } from "../constants";
import { mapStatusToInfo } from "../utils";
import type { Prospect } from "../types";
import { Globe, Phone, Camera } from "lucide-react";

interface Props {
  prospects: Prospect[];
  search: string;
  onSearchChange: (v: string) => void;
  selectedProspect: Prospect | null;
  onSelect: (p: Prospect) => void;
  open: boolean;
  onToggle: () => void;
}

export function RegistryPanel({
  prospects,
  search,
  onSearchChange,
  selectedProspect,
  onSelect,
  open,
  onToggle,
}: Props) {
  const filtered = search
    ? prospects.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    : prospects;

  return (
    <section className="registry-collapsible">
      <button className="collapsible-btn secondary" onClick={onToggle}>
        {LABELS.REGISTRY} ({prospects.length}) <span>{open ? "▲" : "▼"}</span>
      </button>
      <div className={`collapsible-content ${!open ? "collapsed" : ""}`}>
        <div style={{ padding: "0.5rem 1rem" }}>
          <input
            type="text"
            className="search-input"
            style={{ width: "100%" }}
            placeholder={LABELS.FILTER_LIST}
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
        <div className="prospects-list-container">
          <ul className="prospects-list">
            {filtered.length === 0 ? (
              <div className="empty-state">{LABELS.NO_LEADS_FILTER}</div>
            ) : (
              filtered.map((p) => {
                const si = mapStatusToInfo(p);
                const isSel = selectedProspect?.name === p.name && selectedProspect?.address === p.address;
                return (
                  <li
                    key={`${p.name}-${p.address}`}
                    className={isSel ? "selected" : ""}
                    onClick={() => onSelect(p)}
                  >
                    <div>
                      <strong className="p-name">{p.name}</strong>
                      <span className="p-meta">{p.category || LABELS.NO_CATEGORY}</span>
                      <div className="p-tags">
                        <span className={`p-status-tag ${si.class}`}>{si.label}</span>
                        <div className="p-contact-icons" style={{ display: 'inline-flex', gap: '4px', marginLeft: '8px', fontSize: '14px', alignItems: 'center' }}>
                          {p.website && <span title="Tiene sitio web"><Globe size={14} /></span>}
                          {p.phone && <span title="Tiene teléfono"><Phone size={14} /></span>}
                          {p.instagram_url && <span title="Tiene Instagram"><Camera size={14} /></span>}
                        </div>
                        {p.lead_score != null && (
                          <span className={`lead-score ${p.lead_score >= 60 ? "high" : ""}`}>
                            {p.lead_score} pts
                          </span>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
