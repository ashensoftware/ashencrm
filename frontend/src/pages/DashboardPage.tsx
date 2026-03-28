import type { Prospect } from "../types";
import { Users, Target, CheckCircle, Clock, Activity, BarChart2, Trophy, Award, Tag, Star } from "lucide-react";

interface Props {
  prospects: Prospect[];
}

export function DashboardPage({ prospects }: Props) {
  const total = prospects.length;
  const inPipelineStatuses = ["waiting", "prompt_gpt", "demo_created", "contacted"];
  const inPipeline = prospects.filter(p => inPipelineStatuses.includes(p.status || "")).length;
  const clientsWon = prospects.filter(p => p.status === "client_won").length;
  const untouchable = prospects.filter(p => p.status === "scraped" || !p.status).length;

  const FUNNEL_STAGES = [
    { id: "scraped", label: "Potencial", color: "#8b5cf6" },
    { id: "waiting", label: "En Espera", color: "#58a6ff" },
    { id: "prompt_gpt", label: "Prompt GPT", color: "#f59e0b" },
    { id: "demo_created", label: "Demo Lista", color: "#a78bfa" },
    { id: "contacted", label: "Contactados", color: "#2ea043" },
    { id: "client_won", label: "Clientes", color: "#10b981" },
  ];

  const funnelData = FUNNEL_STAGES.map(stage => ({
    ...stage,
    count: prospects.filter(p => p.status === stage.id || (stage.id === "contacted" && p.is_contacted)).length
  }));

  const categoryCounts = prospects.reduce((acc, p) => {
    const cat = p.category ? p.category.trim() : "";
    if (!cat || cat === "*" || cat === "N/A" || cat === "Sin Categoría") return acc;
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const topCategories = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="overview-view" style={{ padding: "2.5rem", height: "100%", overflowY: "auto", color: "var(--text-primary)" }}>
      <header style={{ marginBottom: "2.5rem" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Activity size={28} color="var(--accent)" />
          Dashboard CRM
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem" }}>Resumen del rendimiento y estado del embudo de ventas.</p>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1.5rem", marginBottom: "3rem" }}>
        <MetricCard title="Total Leads" value={total.toString()} icon={<Users />} color="var(--accent)" />
        <MetricCard title="Leads Sin Tocar" value={untouchable.toString()} icon={<Clock />} color="#94a3b8" />
        <MetricCard title="En Pipeline" value={inPipeline.toString()} icon={<Target />} color="#58a6ff" />
        <MetricCard title="Clientes Ganados" value={clientsWon.toString()} icon={<CheckCircle />} color="#10b981" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "2rem" }}>
        <section style={{ background: "var(--bg-card)", padding: "1.5rem", borderRadius: "1rem", border: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <BarChart2 size={20} /> Embudo de Conversión
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {funnelData.map((stage) => {
              const maxCount = Math.max(...funnelData.map(d => d.count), 1);
              const widthPct = Math.max((stage.count / maxCount) * 100, 2);
              return (
                <div key={stage.id} style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                  <div style={{ width: "120px", fontSize: "0.85rem", color: "var(--text-secondary)", fontWeight: 600, textAlign: "right" }}>{stage.label}</div>
                  <div style={{ flex: 1, background: "rgba(255,255,255,0.05)", height: "28px", borderRadius: "99px", overflow: "hidden", display: "flex" }}>
                    <div style={{ width: `${widthPct}%`, background: stage.color, height: "100%", transition: "width 1s ease-out", display: "flex", alignItems: "center", paddingLeft: "0.75rem" }}>
                      {stage.count > 0 && <span style={{ fontSize: "0.75rem", fontWeight: "bold", color: "#fff", textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}>{stage.count}</span>}
                    </div>
                  </div>
                  <div style={{ width: "40px", fontSize: "0.85rem", fontWeight: "bold" }}>{stage.count}</div>
                </div>
              );
            })}
          </div>
        </section>

        <section style={{ background: "var(--bg-card)", padding: "1.5rem", borderRadius: "1rem", border: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Star size={20} color="var(--warning)" /> Top Categorías
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {topCategories.map(([category, count], idx) => (
              <div key={category} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0.8rem 1rem", background: "rgba(255,255,255,0.02)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", transition: "all 0.2s" }} className="table-row-hover">
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  {idx === 0 ? <Trophy size={18} color="#fbbf24" /> :
                   idx === 1 ? <Award size={18} color="#94a3b8" /> :
                   idx === 2 ? <Award size={18} color="#d97706" /> :
                               <Tag size={18} color="var(--text-muted)" />}
                  <span style={{ fontWeight: 600, fontSize: "0.95rem", textTransform: "capitalize", color: "var(--text-primary)" }}>{category.toLowerCase()}</span>
                </div>
                <span style={{ background: "var(--accent-muted)", color: "var(--text-primary)", padding: "0.2rem 0.6rem", borderRadius: "99px", fontSize: "0.75rem", fontWeight: "bold", border: "1px solid var(--accent)" }}>{count} leads</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon, color }: { title: string; value: string; icon: React.ReactNode; color: string }) {
  return (
    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "1rem", padding: "1.5rem", display: "flex", flexDirection: "column", gap: "0.75rem", boxShadow: "0 4px 6px rgba(0,0,0,0.1)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h3 style={{ fontSize: "0.9rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>{title}</h3>
        <div style={{ color }}>{icon}</div>
      </div>
      <div style={{ fontSize: "2.5rem", fontWeight: 700, lineHeight: 1, color: "var(--text-primary)" }}>{value}</div>
    </div>
  );
}
