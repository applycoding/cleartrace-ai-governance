const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:4010/api/v1";

function headers(locale: "en" | "fr") {
  return {
    Accept: "application/json",
    "Accept-Language": locale === "fr" ? "fr-CA" : "en-CA",
  };
}

export type SystemRow = {
  id: string;
  key: string;
  name: string;
  category: number;
  status: string;
};

export async function fetchSystems(locale: "en" | "fr"): Promise<SystemRow[]> {
  const resp = await fetch(`${API_BASE}/systems`, { headers: headers(locale), cache: "no-store" });
  if (!resp.ok) return [];
  const data = (await resp.json()) as { items?: SystemRow[] };
  return data.items ?? [];
}

export async function fetchSystem(locale: "en" | "fr", id: string) {
  const resp = await fetch(`${API_BASE}/systems/${id}`, {
    headers: headers(locale),
    cache: "no-store",
  });
  if (!resp.ok) return null;
  return resp.json();
}

export async function fetchFrameworks() {
  const resp = await fetch(`${API_BASE}/frameworks`, { cache: "no-store" });
  if (!resp.ok) return [];
  const data = (await resp.json()) as { items?: unknown[] };
  return data.items ?? [];
}

export async function fetchFindings(locale: "en" | "fr") {
  const resp = await fetch(`${API_BASE}/findings`, { headers: headers(locale), cache: "no-store" });
  if (!resp.ok) return [];
  const data = (await resp.json()) as { items?: unknown[] };
  return data.items ?? [];
}

export async function fetchReviewQueue() {
  const resp = await fetch(`${API_BASE}/review-queue`, { cache: "no-store" });
  if (!resp.ok) return [];
  const data = (await resp.json()) as { items?: unknown[] };
  return data.items ?? [];
}

export async function postReviewAction(findingId: string, action: string) {
  await fetch(`${API_BASE}/findings/${findingId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
}

export async function uploadEvidence(file: File) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API_BASE}/evidence`, { method: "POST", body: form });
  return resp.ok;
}

export async function fetchRiskSummary() {
  const resp = await fetch(`${API_BASE}/metrics/summary`, { cache: "no-store" });
  if (!resp.ok) return null;
  return resp.json();
}

export async function fetchAuditEvents() {
  const resp = await fetch(`${API_BASE}/audit/events`, { cache: "no-store" });
  if (!resp.ok) return [];
  const data = (await resp.json()) as { items?: unknown[] };
  return data.items ?? [];
}

export async function verifyAuditLedger() {
  const resp = await fetch(`${API_BASE}/audit/verify`, { method: "POST" });
  if (!resp.ok) return null;
  return resp.json();
}

export async function fetchAdminSettings() {
  const resp = await fetch(`${API_BASE}/admin/settings`, { cache: "no-store" });
  if (!resp.ok) return null;
  return resp.json();
}

export async function fetchHealth(): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return resp.ok;
}
