const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:4010/api/v1";

export type SystemSummary = { id: string; name: string };

export async function fetchSystems(): Promise<SystemSummary[]> {
  const resp = await fetch(`${API_BASE}/systems`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!resp.ok) {
    return [];
  }
  const data = (await resp.json()) as { items?: SystemSummary[] };
  return data.items ?? [];
}

export async function fetchHealth(): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return resp.ok;
}
