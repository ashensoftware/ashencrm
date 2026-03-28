import { LABELS, STATUS_OPTIONS, IG_OPTIONS, CONTACT_OPTIONS } from "../constants";
import type { ProspectFilters } from "../types";
import type { CatalogItem } from "../types";

interface Props {
  filters: ProspectFilters;
  onFiltersChange: (f: ProspectFilters) => void;
  catalog: CatalogItem[];
  optionsOpen: boolean;
  onOptionsToggle: () => void;
  onCategoryManage: () => void;
}

export function OptionsPanel({
  filters,
  onFiltersChange,
  catalog,
  optionsOpen,
  onOptionsToggle,
  onCategoryManage,
}: Props) {
  return (
    <section className="options-panel">
      <button className="collapsible-btn options-btn" onClick={onOptionsToggle}>
        <span className="btn-icon-text">
          <svg className="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          {LABELS.FILTERS_ACTIONS}
        </span>
        <span className="arrow">{optionsOpen ? "▲" : "▼"}</span>
      </button>
      <div className={`collapsible-content ${!optionsOpen ? "collapsed" : ""}`}>
        <div className="options-section">
          <div className="options-label">{LABELS.FILTERS}</div>
          <div className="filter-group">
            <label>{LABELS.STATUS}</label>
            <select
              value={filters.status}
              onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value || "all"} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>{LABELS.INSTAGRAM}</label>
            <select
              value={filters.has_instagram}
              onChange={(e) => onFiltersChange({ ...filters, has_instagram: e.target.value })}
            >
              {IG_OPTIONS.map((o) => (
                <option key={o.value || "all"} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>{LABELS.CONTACTED}</label>
            <select
              value={filters.contacted}
              onChange={(e) => onFiltersChange({ ...filters, contacted: e.target.value })}
            >
              {CONTACT_OPTIONS.map((o) => (
                <option key={o.value || "any"} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>{LABELS.SEARCH}</label>
            <input
              type="text"
              className="search-input"
              placeholder={LABELS.SEARCH_PLACEHOLDER}
              value={filters.name}
              onChange={(e) => onFiltersChange({ ...filters, name: e.target.value })}
            />
          </div>
          <div className="filter-group">
            <label>{LABELS.CATEGORY}</label>
            <div className="select-with-action">
              <select
                value={filters.category}
                onChange={(e) => onFiltersChange({ ...filters, category: e.target.value })}
              >
                <option value="">{LABELS.ALL_CATEGORIES}</option>
                {catalog.map((c) => (
                  <option key={c.name} value={c.name}>{c.label}</option>
                ))}
              </select>
              <button className="btn-icon" onClick={onCategoryManage} title={LABELS.MANAGE_CATEGORIES}>
                ⚙
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
