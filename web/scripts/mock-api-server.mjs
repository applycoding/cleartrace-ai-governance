import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "yaml";

const port = Number(process.env.MOCK_API_PORT ?? 4010);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");
const openapiPath = path.join(root, "api/openapi.yaml");
const spec = yaml.parse(fs.readFileSync(openapiPath, "utf8"));

const systems = [
  { id: "11111111-1111-7111-8111-111111111201", name: "SYS-01 Alpha assistant" },
  { id: "11111111-1111-7111-8111-111111111202", name: "SYS-02 Fraud model" },
];

const server = http.createServer((req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${port}`);
  if (url.pathname === "/api/v1/health") {
    json(res, 200, { status: "ok" });
    return;
  }
  if (url.pathname === "/api/v1/systems" && req.method === "GET") {
    json(res, 200, { items: systems, next_cursor: null });
    return;
  }
  if (url.pathname === "/api/v1/frameworks" && req.method === "GET") {
    json(res, 200, { items: [{ id: "fw-dadm", name_en: "DADM", name_fr: "DADM" }] });
    return;
  }
  if (url.pathname.startsWith("/api/v1/")) {
    json(res, 404, { title: "Not found", status: 404 });
    return;
  }
  json(res, 404, { title: "Not found", status: 404 });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`ClearTrace mock API (OpenAPI ${spec.info?.version}) on http://127.0.0.1:${port}/api/v1`);
});

function json(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}
