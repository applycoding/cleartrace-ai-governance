#!/usr/bin/env node
/**
 * Test-only official AIA scoring (MIT).
 * Algorithm aligned to canada-ca/aia-eia-js src/store.ts at commit b625733.
 * Not shipped in product images.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseEmbeddedValue(val) {
  if (!val) return 0;
  const idx = val.lastIndexOf("-");
  if (idx === -1) return 0;
  const tail = val.slice(idx + 1);
  const n = Number(tail);
  return Number.isNaN(n) ? 0 : n;
}

function getValue(raw) {
  if (raw === undefined || raw === null) return 0;
  if (Array.isArray(raw)) return raw.reduce((t, item) => t + getValue(item), 0);
  if (typeof raw === "string") return parseEmbeddedValue(raw);
  if (typeof raw === "number") return raw;
  return 0;
}

function scoreType(name, parent) {
  for (const candidate of [name, parent || ""]) {
    if (candidate.endsWith("-RS")) return 2;
    if (candidate.endsWith("-MS")) return 3;
    if (candidate.endsWith("-NS")) return 1;
  }
  return 1;
}

function maxForChoices(choices, qtype) {
  const values = choices.map((c) => getValue(c.value ?? c));
  if (qtype === "checkbox") return values.reduce((a, b) => a + b, 0);
  return values.length ? Math.max(...values) : 0;
}

function collectQuestions(element, parent, out) {
  if (element.type === "panel") {
    const panelName = element.name || "";
    for (const child of element.elements || []) collectQuestions(child, panelName, out);
    return;
  }
  if (element.name) out.push({ ...element, _parent: parent });
}

function iterQuestions(survey) {
  const questions = [];
  for (const page of survey.pages || []) {
    for (const element of page.elements || []) collectQuestions(element, null, questions);
  }
  return questions;
}

export function scoreAnswers(answers, survey) {
  let rawScore = 0;
  let maxRaw = 0;
  let mitigation = 0;
  let maxMitigation = 0;
  for (const question of iterQuestions(survey)) {
    const qtype = question.type || "";
    if (!["radiogroup", "checkbox", "dropdown"].includes(qtype)) continue;
    const stype = scoreType(question.name, question._parent);
    if (stype === 1) continue;
    const value = getValue(answers[question.name]);
    const maxVal = maxForChoices(question.choices || [], qtype);
    if (stype === 2) {
      rawScore += value;
      maxRaw += maxVal;
    } else if (stype === 3) {
      mitigation += value;
      maxMitigation += maxVal;
    }
  }
  const percentage = 0.8;
  const deduction = 0.15;
  let finalScore;
  if (mitigation >= percentage * (maxMitigation / 2)) {
    finalScore = Math.round((1 - deduction) * rawScore);
  } else {
    finalScore = rawScore;
  }
  const threshold1 = 0.25;
  const threshold2 = 0.5;
  const threshold3 = 0.75;
  let level;
  if (maxRaw === 0 || finalScore <= maxRaw * threshold1) level = 1;
  else if (finalScore <= maxRaw * threshold2) level = 2;
  else if (finalScore <= maxRaw * threshold3) level = 3;
  else level = 4;
  return {
    raw_score: rawScore,
    mitigation_score: mitigation,
    max_raw_score: maxRaw,
    max_mitigation_score: maxMitigation,
    final_score: finalScore,
    impact_level: level,
  };
}

if (process.argv[1] && process.argv[1].endsWith("official_score_b625733.mjs")) {
  const surveyPath =
    process.env.AIA_SURVEY_PATH ||
    path.resolve(__dirname, "survey-enfr.b625733.json");
  const survey = JSON.parse(fs.readFileSync(surveyPath, "utf8"));
  const chunks = [];
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (c) => chunks.push(c));
  process.stdin.on("end", () => {
    const answers = JSON.parse(chunks.join("") || "{}");
    process.stdout.write(JSON.stringify(scoreAnswers(answers, survey)));
  });
}
