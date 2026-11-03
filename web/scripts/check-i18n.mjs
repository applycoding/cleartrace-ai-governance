#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function flattenKeys(obj, prefix = "") {
  const keys = [];
  for (const [k, v] of Object.entries(obj)) {
    const next = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      keys.push(...flattenKeys(v, next));
    } else {
      keys.push(next);
    }
  }
  return keys;
}

function loadJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(root, rel), "utf8"));
}

const en = loadJson("locales/en/common.json");
const fr = loadJson("locales/fr/common.json");
const enKeys = new Set(flattenKeys(en));
const frKeys = new Set(flattenKeys(fr));
const missingInFr = [...enKeys].filter((k) => !frKeys.has(k));
const missingInEn = [...frKeys].filter((k) => !enKeys.has(k));

const scanDirs = ["app", "components", "lib"];
const hardcoded = [];

for (const dir of scanDirs) {
  const base = path.join(root, dir);
  if (!fs.existsSync(base)) continue;
  for (const file of walk(base)) {
    if (!file.endsWith(".tsx")) continue;
    const text = fs.readFileSync(file, "utf8");
    const jsxTextMatches = text.match(/>([^<\n]+)</g) ?? [];
    for (const match of jsxTextMatches) {
      const inner = match.slice(1, -1).trim();
      if (!inner || inner.includes("{") || inner.includes("(")) continue;
      if (!/[A-Za-zÀ-ÿ]/.test(inner)) continue;
      if (inner === "children") continue;
      hardcoded.push({ file: path.relative(root, file), snippet: inner.slice(0, 80) });
    }
  }
}

let failed = false;
if (missingInFr.length || missingInEn.length) {
  failed = true;
  console.error("Missing locale keys:");
  missingInFr.forEach((k) => console.error(`  fr missing: ${k}`));
  missingInEn.forEach((k) => console.error(`  en missing: ${k}`));
}
if (hardcoded.length) {
  failed = true;
  console.error("Hard-coded UI strings:");
  hardcoded.forEach((h) => console.error(`  ${h.file}: "${h.snippet}"`));
}
if (failed) {
  process.exit(1);
}
console.log(
  JSON.stringify({
    missing_keys: 0,
    hard_coded_strings: 0,
    en_keys: enKeys.size,
    fr_keys: frKeys.size,
  }),
);

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else yield full;
  }
}
