import type { Prospect } from "../types";
import type { StatusInfo } from "../types";

const STATUS_MAP: Record<string, StatusInfo> = {
  scraped: { label: "POTENCIAL", class: "potential" },
  waiting: { label: "EN ESPERA", class: "waiting" },
  prompt_gpt: { label: "PROMPT GPT", class: "prompt_gpt" },
  demo_created: { label: "DEMO COMPLETA", class: "demo_created" },
  has_website: { label: "CON WEB", class: "has_website" },
  rejected: { label: "RECHAZADO", class: "rejected" },
  contacted: { label: "CONTACTADO", class: "contacted" },
  client_won: { label: "CLIENTE", class: "client_won" },
};

export function mapStatusToInfo(p: Prospect | null): StatusInfo {
  if (!p) return { label: "DESCONOCIDO", class: "unknown" };
  if (p.is_contacted || p.status === "contacted")
    return STATUS_MAP.contacted;
  return STATUS_MAP[p.status || ""] ?? {
    label: (p.status || "?").toUpperCase(),
    class: "unknown",
  };
}

const STATUS_COLORS: Record<string, string> = {
  scraped: "#8b5cf6",
  waiting: "#58a6ff",
  prompt_gpt: "#f59e0b",
  demo_created: "#a78bfa",
  has_website: "#22c55e",
  contacted: "#2ea043",
  client_won: "#10b981",
  rejected: "#64748b",
};

export function mapStatusToColor(status?: string): string {
  return STATUS_COLORS[status || ""] ?? "#94a3b8";
}

const STATUS_LABELS: Record<string, string> = {
  scraped: "Potencial",
  waiting: "En Espera",
  prompt_gpt: "Prompt GPT",
  demo_created: "Demo Lista",
  has_website: "Con Web",
  contacted: "Contactado",
  client_won: "Cliente Obtenido",
  rejected: "Rechazado",
};

export function mapStatusToLabel(status?: string): string {
  return STATUS_LABELS[status || ""] ?? status ?? "—";
}

const CLIENT_STAGE_COLORS: Record<string, string> = {
  quote_sent: "#8b5cf6",
  meetings: "#58a6ff",
  payment_received: "#22c55e",
  contract: "#f59e0b",
  in_development: "#a78bfa",
  qa_staging: "#06b6d4",
  delivered: "#10b981",
  on_hold: "#64748b",
  closed_lost: "#94a3b8",
};

const CLIENT_STAGE_LABELS: Record<string, string> = {
  quote_sent: "Cotización enviada",
  meetings: "Reuniones",
  payment_received: "Pago recibido",
  contract: "Contrato",
  in_development: "En desarrollo",
  qa_staging: "QA / staging",
  delivered: "Entregado",
  on_hold: "En pausa",
  closed_lost: "Cerrado perdido",
};

export function mapClientStageToColor(stage?: string): string {
  return CLIENT_STAGE_COLORS[stage || ""] ?? "#94a3b8";
}

export function mapClientStageToLabel(stage?: string): string {
  return CLIENT_STAGE_LABELS[stage || ""] ?? (stage || "").replace(/_/g, " ") || "—";
}
