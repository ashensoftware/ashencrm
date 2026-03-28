import type { Prospect, ProspectFilters } from "../types";

const BASE = "/api";

export function createRequest() {
  return async (path: string, opts: RequestInit = {}) =>
    fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...opts.headers } as HeadersInit,
      ...opts,
    });
}

const request = createRequest();

export async function fetchCatalog(): Promise<{ name: string; label: string }[]> {
  return (await request("/catalog/categories")).json();
}

export async function fetchProspects(filters: ProspectFilters = {}): Promise<Prospect[]> {
  const params = new URLSearchParams();
  if (filters.status) params.append("status", filters.status);
  if (filters.category) params.append("category", filters.category);
  if (filters.city) params.append("city", filters.city);
  if (filters.contacted) params.append("contacted", filters.contacted);
  if (filters.has_instagram) params.append("has_instagram", filters.has_instagram);
  if (filters.name) params.append("name", filters.name);
  return (await request(`/prospects?${params}`)).json();
}

export async function fetchStats(): Promise<Record<string, number>> {
  return (await request("/stats")).json();
}

export async function fetchHexagons() {
  return (await request("/hexagons")).json();
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

export function updateProspect(name: string, data: Record<string, string>) {
  return request(`/prospects/${encodeURIComponent(name)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function normalizeCategories() {
  return request("/prospects/normalize-categories", { method: "POST" });
}

export async function fetchRandomProspect(status = "scraped"): Promise<Prospect | { message: string }> {
  return (await request(`/prospects/random?status=${status}`)).json();
}

export async function automateProspect(name: string) {
  return (await request(`/prospects/${encodeURIComponent(name)}/automate`, { method: "POST" })).json();
}

export async function sendWhatsApp(name: string) {
  return (await request(`/prospects/${encodeURIComponent(name)}/send-whatsapp`, { method: "POST" })).json();
}

export function getScreenshotUrl(path?: string): string | null {
  if (!path) return null;
  const name = path.replace(/^.*[\\/]/, "");
  return name ? `/api/screenshots/${encodeURIComponent(name)}` : null;
}
