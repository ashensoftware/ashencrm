import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchClients } from "../api";
import type { Client } from "../types";
import { BarChart2, ArrowRight, Briefcase } from "lucide-react";

/** Mismo orden y colores que el Kanban de clientes */
const CLIENT_FUNNEL_STAGES: { id: string; label: string; color: string }[] = [
  { id: "quote_sent", label: "Cotización", color: "#a78bfa" },
  { id: "meetings", label: "Reuniones", color: "#58a6ff" },
  { id: "payment_received", label: "Pago", color: "#f59e0b" },
  { id: "contract", label: "Contrato", color: "#ec4899" },
  { id: "in_development", label: "En desarrollo", color: "#f97316" },
  { id: "qa_staging", label: "QA / Staging", color: "#eab308" },
  { id: "delivered", label: "Entregado", color: "#10b981" },
  { id: "on_hold", label: "En pausa", color: "#6b7280" },
  { id: "closed_lost", label: "Cerrado", color: "#ef4444" },
];

export function ClientsDashboardPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setClients(await fetchClients());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const byStage = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of clients) {
      const s = c.stage || "quote_sent";
      m[s] = (m[s] || 0) + 1;
    }
    return m;
  }, [clients]);

  const funnelRows = useMemo(
    () =>
      CLIENT_FUNNEL_STAGES.map((stage) => ({
        ...stage,
        count: byStage[stage.id] ?? 0,
      })),
    [byStage]
  );

  const maxFunnel = Math.max(...funnelRows.map((r) => r.count), 1);

  const total = clients.length;
  const activePipeline = clients.filter((c) => c.stage !== "closed_lost" && c.stage !== "delivered").length;

  return (
    <div className="clients-dashboard overview-view">
      <header className="clients-page-header clients-dash-hero">
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "0.65rem", fontSize: "1.85rem", fontWeight: 700, margin: 0 }}>
            <Briefcase size={30} color="var(--accent)" aria-hidden />
            Resumen de clientes
          </h1>
          <p className="clients-page-sub">
            Vista general de cuentas y etapas del pipeline (independiente del dashboard de leads).
          </p>
        </div>
        <Link to="/clientes/pipeline" className="btn-primary" style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
          Ir al pipeline <ArrowRight size={18} />
        </Link>
      </header>

      {err && <p style={{ color: "var(--warning)" }}>{err}</p>}
      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Cargando…</p>
      ) : (
        <>
          <div className="clients-dash-kpis">
            <div className="clients-dash-kpi clients-dash-kpi-card">
              <span className="clients-dash-kpi-value">{total}</span>
              <span className="clients-dash-kpi-label">Cuentas totales</span>
            </div>
            <div className="clients-dash-kpi clients-dash-kpi-card">
              <span className="clients-dash-kpi-value">{activePipeline}</span>
              <span className="clients-dash-kpi-label">Activas (no cerradas / entregadas)</span>
            </div>
          </div>

          <section className="clients-funnel-panel">
            <h2 className="clients-funnel-title">
              <BarChart2 size={22} aria-hidden /> Pipeline por etapa
            </h2>
            <p className="clients-funnel-sub">Misma escala visual que el embudo de leads: barras proporcionales al máximo en una etapa.</p>
            <div className="clients-funnel-rows">
              {funnelRows.map((stage) => {
                const widthPct = Math.max((stage.count / maxFunnel) * 100, stage.count > 0 ? 8 : 2);
                return (
                  <div key={stage.id} className="clients-funnel-row">
                    <div className="clients-funnel-label">{stage.label}</div>
                    <div className="clients-funnel-track">
                      <div
                        className="clients-funnel-fill"
                        style={{ width: `${widthPct}%`, background: stage.color }}
                      >
                        {stage.count > 0 && <span className="clients-funnel-fill-text">{stage.count}</span>}
                      </div>
                    </div>
                    <div className="clients-funnel-num">{stage.count}</div>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
