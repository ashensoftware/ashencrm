/** Etapas del pipeline de clientes (Kanban + etiquetas en tablas). */
export const STAGE_COLUMNS = [
  { stage: "quote_sent", label: "Cotización", color: "#a78bfa" },
  { stage: "meetings", label: "Reuniones", color: "#58a6ff" },
  { stage: "payment_received", label: "Pago", color: "#f59e0b" },
  { stage: "contract", label: "Contrato", color: "#ec4899" },
  { stage: "in_development", label: "En desarrollo", color: "#f97316" },
  { stage: "qa_staging", label: "QA / Staging", color: "#eab308" },
  { stage: "delivered", label: "Entregado", color: "#10b981" },
  { stage: "on_hold", label: "En pausa", color: "#6b7280" },
  { stage: "closed_lost", label: "Cerrado", color: "#ef4444" },
] as const;

export function clientStageLabel(stage: string): string {
  const row = STAGE_COLUMNS.find((c) => c.stage === stage);
  return row?.label ?? stage;
}
