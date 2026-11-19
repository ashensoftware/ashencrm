import { useEffect, useState } from "react";
import { createPipelineRun, fetchPipelineRun, pipelineAction } from "../api";

type Step = { stage: string; status: string; attempt: number };
type RunView = {
  run: { id: string; status: string; campaign_id: string };
  steps: Step[];
  events: { event_type: string }[];
};

export function PipelineRunsPage() {
  const [campaign, setCampaign] = useState("campana-local");
  const [segment, setSegment] = useState("cafeterias");
  const [limit, setLimit] = useState(10);
  const [run, setRun] = useState<RunView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!run?.run.id) return;
    const timer = window.setInterval(async () => {
      try {
        setRun(await fetchPipelineRun(run.run.id));
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo actualizar");
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [run?.run.id]);

  async function start() {
    setError("");
    try {
      const created = await createPipelineRun(
        {
          campaign_id: campaign,
          segment,
          max_results: limit,
          discovery_provider: "simulated",
          outreach: "prepare_only",
        },
        `run-${campaign}-${Date.now()}`
      );
      setRun(await fetchPipelineRun(created.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar");
    }
  }

  async function act(action: "pause" | "resume" | "cancel" | "retry-failed") {
    if (!run) return;
    await pipelineAction(run.run.id, action);
    setRun(await fetchPipelineRun(run.run.id));
  }

  return (
    <section style={{ padding: "1.5rem", display: "grid", gap: "1rem" }}>
      <h1>Ejecuciones</h1>
      <p>El avance sale de los pasos guardados. No hay un porcentaje inventado.</p>
      <label>
        Campaña
        <input aria-label="Campaña" value={campaign} onChange={(e) => setCampaign(e.target.value)} />
      </label>
      <label>
        Segmento
        <input aria-label="Segmento" value={segment} onChange={(e) => setSegment(e.target.value)} />
      </label>
      <label>
        Máximo
        <input aria-label="Máximo" type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
      </label>
      <button type="button" onClick={start}>Ejecutar pipeline</button>
      {error && <p role="alert">{error}</p>}
      {run && (
        <div>
          <p>Estado: {run.run.status}</p>
          <p>Campaña: {run.run.campaign_id}</p>
          <ul>
            {run.steps.map((step) => (
              <li key={step.stage}>{step.stage}: {step.status} (intentos {step.attempt})</li>
            ))}
          </ul>
          <p>Eventos: {run.events.length}</p>
          <button type="button" onClick={() => act("pause")}>Pausar</button>
          <button type="button" onClick={() => act("resume")}>Reanudar</button>
          <button type="button" onClick={() => act("cancel")}>Cancelar</button>
          <button type="button" onClick={() => act("retry-failed")}>Reintentar fallos</button>
        </div>
      )}
    </section>
  );
}
