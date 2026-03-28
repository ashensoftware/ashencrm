import { createStatCardsConfig } from "../utils";
import type { ProspectFilters } from "../types";

interface Props {
  stats: Record<string, number>;
  filters: ProspectFilters;
  onFilterChange: (status: string) => void;
}

export function StatsPanel({ stats, filters, onFilterChange }: Props) {
  const total = Object.values(stats).reduce((a, b) => a + b, 0);
  const cards = createStatCardsConfig(stats, total);

  return (
    <section className="stats-panel">
      {cards.map((s) => (
        <div
          key={s.id}
          className={`stat-card stat-clickable ${s.highlight ? "highlight" : ""} ${s.success ? "success" : ""} ${filters.status === s.filter ? "active" : ""}`}
          onClick={() => onFilterChange(s.filter)}
        >
          <span className="label">{s.label}</span>
          <span className="value">{s.value}</span>
        </div>
      ))}
    </section>
  );
}
