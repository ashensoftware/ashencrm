import type { ProspectFilters } from "../types";
import { LABELS } from "../constants";

export function createDefaultFilters(): ProspectFilters {
  return {
    status: "",
    contacted: "",
    has_instagram: "",
    category: "",
    name: "",
  };
}

export function createStatCardsConfig(stats: Record<string, number>, total: number) {
  return [
    { id: "total", filter: "", label: LABELS.TOTAL, value: total },
    { id: "ready", filter: "ready", label: LABELS.READY, value: stats.ready ?? 0, highlight: true },
    { id: "demo", filter: "demo_created", label: LABELS.DEMO, value: stats.demo_created ?? 0 },
    { id: "contacted", filter: "contacted", label: LABELS.CONTACTED_STAT, value: stats.contacted ?? 0, success: true },
  ];
}
