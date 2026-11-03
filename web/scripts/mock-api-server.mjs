import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "yaml";

const port = Number(process.env.MOCK_API_PORT ?? 4010);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");
const spec = yaml.parse(fs.readFileSync(path.join(root, "api/openapi.yaml"), "utf8"));

const systems = [
  {
    id: "11111111-1111-7111-8111-111111111201",
    key: "SYS-01",
    name_en: "Alpha assistant",
    name_fr: "Assistant Alpha",
    category: 3,
    status_en: "In production",
    status_fr: "En production",
  },
  {
    id: "11111111-1111-7111-8111-111111111202",
    key: "SYS-02",
    name_en: "Fraud detection model",
    name_fr: "Modèle de détection de fraude",
    category: 5,
    status_en: "Pilot",
    status_fr: "Pilote",
  },
];

const findings = [
  {
    id: "f-001",
    system_id: systems[0].id,
    control_id: "DADM-2.1",
    outcome: "fail",
    explanation_en: "Missing human oversight evidence.",
    explanation_fr: "Preuve de supervision humaine manquante.",
    certainty: 0.82,
  },
  {
    id: "f-002",
    system_id: systems[0].id,
    control_id: "AIA-4.2",
    outcome: "partial",
    explanation_en: "Impact assessment draft not verified.",
    explanation_fr: "Ébauche d'évaluation d'impact non vérifiée.",
    certainty: 0.61,
  },
  {
    id: "f-003",
    system_id: systems[1].id,
    control_id: "PSD-1.3",
    outcome: "pass",
    explanation_en: "Controls satisfied with current evidence.",
    explanation_fr: "Contrôles satisfaits avec les preuves actuelles.",
    certainty: 0.94,
  },
];

const reviewQueue = findings.filter((f) => f.outcome !== "pass");
const auditEvents = [
  { id: "ae-1", action: "finding.reviewed", hash: "abc123" },
  { id: "ae-2", action: "evidence.uploaded", hash: "def456" },
];

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${port}`);
  const lang = req.headers["accept-language"]?.startsWith("fr") ? "fr" : "en";

  if (url.pathname === "/api/v1/health") {
    return json(res, 200, { status: "ok" });
  }
  if (url.pathname === "/api/v1/systems" && req.method === "GET") {
    return json(res, 200, {
      items: systems.map((s) => ({
        id: s.id,
        key: s.key,
        name: lang === "fr" ? s.name_fr : s.name_en,
        category: s.category,
        status: lang === "fr" ? s.status_fr : s.status_en,
      })),
    });
  }
  const systemMatch = url.pathname.match(/^\/api\/v1\/systems\/([^/]+)$/);
  if (systemMatch && req.method === "GET") {
    const system = systems.find((s) => s.id === systemMatch[1]);
    if (!system) return json(res, 404, { title: "Not found", status: 404 });
    return json(res, 200, {
      ...system,
      name: lang === "fr" ? system.name_fr : system.name_en,
      status: lang === "fr" ? system.status_fr : system.status_en,
      description:
        lang === "fr"
          ? "Système d'IA enregistré dans ClearTrace."
          : "AI system registered in ClearTrace.",
    });
  }
  if (url.pathname === "/api/v1/frameworks" && req.method === "GET") {
    return json(res, 200, {
      items: [
        { id: "fw-dadm", code: "DADM", version: "2024.1", coverage: 0.86 },
        { id: "fw-aia", code: "AIA", version: "2024.1", coverage: 0.74 },
      ],
    });
  }
  if (url.pathname === "/api/v1/findings" && req.method === "GET") {
    return json(res, 200, {
      items: findings.map((f) => ({
        ...f,
        explanation: lang === "fr" ? f.explanation_fr : f.explanation_en,
      })),
    });
  }
  if (url.pathname === "/api/v1/review-queue" && req.method === "GET") {
    return json(res, 200, { items: reviewQueue });
  }
  if (url.pathname.startsWith("/api/v1/findings/") && url.pathname.endsWith("/actions") && req.method === "POST") {
    return json(res, 200, { status: "recorded" });
  }
  if (url.pathname === "/api/v1/evidence" && req.method === "POST") {
    return json(res, 201, { id: "ev-001", status: "quarantined_scan_pending" });
  }
  if (url.pathname === "/api/v1/metrics/summary" && req.method === "GET") {
    return json(res, 200, {
      binding_breaches: 1,
      advisory_flags: 2,
      last_observation: "2026-11-03T12:00:00Z",
    });
  }
  if (url.pathname === "/api/v1/audit/events" && req.method === "GET") {
    return json(res, 200, { items: auditEvents });
  }
  if (url.pathname === "/api/v1/audit/verify" && req.method === "POST") {
    return json(res, 200, { valid: true, checked: auditEvents.length });
  }
  if (url.pathname === "/api/v1/admin/settings" && req.method === "GET") {
    return json(res, 200, { webhooks: 2, connectors: 4, locale_default: "en-CA" });
  }
  if (url.pathname.startsWith("/api/v1/")) {
    return json(res, 404, { title: "Not found", status: 404 });
  }
  return json(res, 404, { title: "Not found", status: 404 });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`ClearTrace mock API (OpenAPI ${spec.info?.version}) on http://127.0.0.1:${port}/api/v1`);
});

function json(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}
