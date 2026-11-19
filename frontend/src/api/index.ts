import type {
  Prospect,
  ProspectFilters,
  AppSettings,
  CatalogItem,
  Client,
  ClientMeeting,
  ClientMapMarker,
  ParsedMapsUrl,
} from "../types";

const BASE = "/api";
const ACCESS_TOKEN_KEY = "ashencrm.accessToken";

export function accessToken(): string {
  const fromEnv = import.meta.env.VITE_LOCAL_ACCESS_TOKEN;
  if (typeof fromEnv === "string" && fromEnv.trim()) return fromEnv.trim();
  try {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY)?.trim() || "";
  } catch {
    return "";
  }
}

export function storeAccessToken(token: string): void {
  const value = token.trim();
  if (!value) {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    return;
  }
  sessionStorage.setItem(ACCESS_TOKEN_KEY, value);
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

export async function signInWithPassword(email: string, password: string): Promise<void> {
  const url = String(import.meta.env.VITE_SUPABASE_URL || "").replace(/\/$/, "");
  const key = String(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "");
  if (!url || !key) {
    throw new Error("Supabase no está configurado en el .env de la raíz.");
  }
  const response = await fetch(`${url}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: key, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const payload = (await response.json().catch(() => ({}))) as {
    access_token?: unknown;
    error_description?: unknown;
    msg?: unknown;
  };
  if (!response.ok || typeof payload.access_token !== "string" || !payload.access_token) {
    const detail =
      typeof payload.error_description === "string"
        ? payload.error_description
        : typeof payload.msg === "string"
          ? payload.msg
          : "No se pudo iniciar sesión.";
    throw new Error(detail);
  }
  storeAccessToken(payload.access_token);
}

function applyHeaders(opts: RequestInit): Headers {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  const token = accessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (opts.headers) {
    new Headers(opts.headers).forEach((value, key) => headers.set(key, value));
  }
  return headers;
}

export function createRequest() {
  return async (path: string, opts: RequestInit = {}) =>
    fetch(`${BASE}${path}`, {
      ...opts,
      headers: applyHeaders(opts),
    });
}

const request = createRequest();

export async function fetchCatalog(): Promise<CatalogItem[]> {
  const res = await request("/catalog/categories");
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudo cargar el catálogo");
  return res.json();
}

export async function fetchProspects(filters: ProspectFilters = {}): Promise<Prospect[]> {
  const params = new URLSearchParams();
  if (filters.status) params.append("status", filters.status);
  if (filters.category) params.append("category", filters.category);
  if (filters.city) params.append("city", filters.city);
  if (filters.contacted) params.append("contacted", filters.contacted);
  if (filters.has_instagram) params.append("has_instagram", filters.has_instagram);
  if (filters.name) params.append("name", filters.name);
  const res = await request(`/prospects?${params}`);
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudieron cargar los prospectos");
  return res.json();
}

export async function fetchStats(): Promise<Record<string, number>> {
  const res = await request("/stats");
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudieron cargar las estadísticas");
  return res.json();
}

export async function fetchHexagons() {
  const res = await request("/hexagons");
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudieron cargar los hexágonos");
  return res.json();
}

export function startScrape(body: object) {
  return request("/scrape-interactive", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchScrapeLogs(): Promise<string[]> {
  return (await request("/scrape-logs")).json();
}

export function reviewProspect(name: string, action: string) {
  return request(`/prospects/${encodeURIComponent(name)}/review?action=${action}`, { method: "POST" });
}

export function updateProspect(name: string, data: Record<string, string | number | boolean | null>) {
  return request(`/prospects/${encodeURIComponent(name)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function normalizeCategories() {
  return request("/prospects/normalize-categories", { method: "POST" });
}

export async function createProspect(data: Partial<Prospect>) {
  return request("/prospects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteProspectById(prospectId: number): Promise<Response> {
  return request(`/prospects/${prospectId}`, { method: "DELETE" });
}

export async function fetchRandomProspect(status = "scraped"): Promise<Prospect | { message: string }> {
  try {
    const res = await request(`/prospects/random?status=${status}`);
    if (!res.ok) return { message: "Error al obtener prospecto" };
    return await res.json();
  } catch {
    return { message: "Error de conexion con el servidor" };
  }
}

export async function automateProspect(name: string) {
  return (await request(`/prospects/${encodeURIComponent(name)}/automate`, { method: "POST" })).json();
}

export async function sendWhatsApp(name: string) {
  return (await request(`/prospects/${encodeURIComponent(name)}/send-whatsapp`, { method: "POST" })).json();
}

function throwIfAuth(res: Response): void {
  if (res.status === 401 || res.status === 403) {
    throw new Error(`AUTH_${res.status}`);
  }
}

export async function fetchAdminSettings(): Promise<AppSettings> {
  const res = await request("/admin/settings");
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudieron cargar los ajustes");
  return res.json();
}

export async function patchAdminSettings(partial: Partial<AppSettings>): Promise<AppSettings> {
  const res = await request("/admin/settings", { method: "PATCH", body: JSON.stringify(partial) });
  throwIfAuth(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Error al guardar");
  }
  return res.json();
}

export type SqlConsoleResult =
  | {
      kind: "select";
      columns: string[];
      rows: Record<string, unknown>[];
      rowcount: number;
      truncated: boolean;
    }
  | { kind: "mutate"; rowcount: number };

export async function fetchSqlConsoleStatus(): Promise<{ enabled: boolean }> {
  const res = await request("/admin/sql/status");
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudo cargar el estado de la consola SQL");
  return res.json();
}

export async function executeAdminSql(sql: string): Promise<SqlConsoleResult> {
  const res = await request("/admin/sql", {
    method: "POST",
    body: JSON.stringify({ sql }),
  });
  throwIfAuth(res);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = data as { detail?: string | string[] };
    const d = err.detail;
    const msg = Array.isArray(d) ? d.join(", ") : d || "Error al ejecutar SQL";
    throw new Error(msg);
  }
  return data as SqlConsoleResult;
}

export function patchCatalogCategory(name: string, body: { label?: string; icon?: string }) {
  return request(`/catalog/categories/${encodeURIComponent(name)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function renameCatalogCategory(oldName: string, newName: string) {
  return request("/catalog/categories/rename", {
    method: "PUT",
    body: JSON.stringify({ old_name: oldName, new_name: newName }),
  });
}

export function resetCategoryAssignments(category: string) {
  return request("/prospects/categories/reset-assignment", {
    method: "POST",
    body: JSON.stringify({ category }),
  });
}

export function getScreenshotUrl(path?: string): string | null {
  if (!path) return null;
  const name = path.replace(/^.*[\\/]/, "");
  return name ? `/api/screenshots/${encodeURIComponent(name)}` : null;
}

const rawFetch = (path: string, opts: RequestInit = {}) => {
  const headers = new Headers(opts.headers);
  const token = accessToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${BASE}${path}`, { ...opts, headers });
};

export async function fetchClients(): Promise<Client[]> {
  const res = await rawFetch("/clients");
  if (!res.ok) throw new Error("No se pudieron cargar los clientes");
  return res.json();
}

export async function fetchClientMapMarkers(): Promise<ClientMapMarker[]> {
  const res = await rawFetch("/clients/map-markers");
  if (!res.ok) throw new Error("No se pudieron cargar los marcadores del mapa");
  return res.json();
}

export async function parseClientMapsUrl(url: string): Promise<ParsedMapsUrl> {
  const res = await request("/clients/parse-maps-url", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "No se pudo leer el enlace");
  }
  return res.json();
}

export async function fetchClient(id: number): Promise<Client & { meetings: ClientMeeting[] }> {
  const res = await rawFetch(`/clients/${id}`);
  if (!res.ok) throw new Error("Cliente no encontrado");
  return res.json();
}

export async function createClient(body: Partial<Client>): Promise<Client & { meetings: ClientMeeting[] }> {
  const res = await request("/clients", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Error al crear");
  }
  return res.json();
}

export async function patchClient(
  id: number,
  body: Partial<Client>
): Promise<Client & { meetings: ClientMeeting[] }> {
  const res = await request(`/clients/${id}`, { method: "PATCH", body: JSON.stringify(body) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Error al guardar");
  }
  return res.json();
}

export async function deleteClient(id: number): Promise<void> {
  const res = await request(`/clients/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("No se pudo eliminar");
}

export async function createClientFromProspect(
  prospectName: string
): Promise<Client & { meetings: ClientMeeting[] }> {
  const res = await rawFetch(
    `/clients/from-prospect/${encodeURIComponent(prospectName)}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Error al importar");
  }
  return res.json();
}

export function clientQuotePdfUrl(clientId: number): string {
  return `${BASE}/clients/${clientId}/quote-pdf`;
}

export async function uploadClientQuote(
  clientId: number,
  file: File,
  opts?: { quote_amount?: number; quote_currency?: string; estimated_delivery_at?: string }
): Promise<Client & { meetings: ClientMeeting[] }> {
  const fd = new FormData();
  fd.append("file", file);
  if (opts?.quote_amount != null) fd.append("quote_amount", String(opts.quote_amount));
  if (opts?.quote_currency) fd.append("quote_currency", opts.quote_currency);
  if (opts?.estimated_delivery_at) fd.append("estimated_delivery_at", opts.estimated_delivery_at);
  const res = await rawFetch(`/clients/${clientId}/quote`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Error al subir PDF");
  }
  return res.json();
}

export async function addClientMeeting(
  clientId: number,
  body: Partial<ClientMeeting>
): Promise<ClientMeeting> {
  const res = await request(`/clients/${clientId}/meetings`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Error al crear reunión");
  return res.json();
}

export async function patchClientMeeting(
  meetingId: number,
  body: Partial<ClientMeeting>
): Promise<ClientMeeting> {
  const res = await request(`/clients/meetings/${meetingId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Error al actualizar reunión");
  return res.json();
}

export async function deleteClientMeeting(meetingId: number): Promise<void> {
  const res = await request(`/clients/meetings/${meetingId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Error al eliminar reunión");
}

export async function validateDemoUrl(url: string): Promise<{ success: boolean; verified: boolean; status: string; detail: string }> {
  const res = await request("/demos/validate", { method: "POST", body: JSON.stringify({ url }) });
  throwIfAuth(res);
  return res.json();
}

export async function createPipelineRun(body: Record<string, unknown>, idempotencyKey: string) {
  const res = await request("/v1/pipeline-runs", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(body),
  });
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudo crear la ejecución");
  return res.json();
}

export async function fetchPipelineRun(id: string) {
  const res = await request(`/v1/pipeline-runs/${id}`);
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudo leer la ejecución");
  return res.json();
}

export async function pipelineAction(id: string, action: "pause" | "resume" | "cancel" | "retry-failed") {
  const res = await request(`/v1/pipeline-runs/${id}/${action}`, { method: "POST" });
  throwIfAuth(res);
  if (!res.ok) throw new Error("No se pudo actualizar la ejecución");
  return res.json();
}
