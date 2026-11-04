#!/usr/bin/env python3
"""Generate docs/trl5/t20_language_review_sheet.csv from shipped UI, notification and report strings."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "notifier" / "src"))
sys.path.insert(0, str(ROOT / "services" / "reports" / "src"))

from cleartrace_notifier.user_strings import notification_template_rows  # noqa: E402
from cleartrace_reports.user_strings import report_template_rows  # noqa: E402

OUT = ROOT / "docs" / "trl5" / "t20_language_review_sheet.csv"
LOCALE_EN = ROOT / "web" / "locales" / "en" / "common.json"
LOCALE_FR = ROOT / "web" / "locales" / "fr" / "common.json"

SCREEN_KEYS = (
    ("screen:home", "home.welcome", "home.cta"),
    ("screen:register", "register.heading", "register.description"),
    ("screen:register_detail", "register.detailHeading", "register.detailDescription"),
    ("screen:frameworks", "frameworks.heading", "frameworks.description"),
    ("screen:findings", "findings.heading", "findings.description"),
    ("screen:review", "review.heading", "review.description"),
    ("screen:evidence", "evidence.heading", "evidence.description"),
    ("screen:risk", "risk.heading", "risk.description"),
    ("screen:audit", "audit.heading", "audit.description"),
    ("screen:admin", "admin.heading", "admin.description"),
)


def _lookup(locale: dict, key: str) -> str:
    node: object = locale
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(key)
        node = node[part]
    if not isinstance(node, str):
        raise TypeError(key)
    return node


def _screen_rows(en: dict, fr: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item_id, *keys in SCREEN_KEYS:
        en_text = " — ".join(_lookup(en, key) for key in keys)
        fr_text = " — ".join(_lookup(fr, key) for key in keys)
        rows.append(
            {
                "category": "screen",
                "item_id": item_id,
                "EN text": en_text,
                "FR text": fr_text,
                "reviewer name": "",
                "title": "",
                "date": "",
                "verdict": "",
            }
        )
    return rows


def _notification_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for template_id, title_en, title_fr, body_en, body_fr in notification_template_rows():
        en_text = title_en if not body_en else f"{title_en} — {body_en}"
        fr_text = title_fr if not body_fr else f"{title_fr} — {body_fr}"
        rows.append(
            {
                "category": "notification",
                "item_id": template_id,
                "EN text": en_text,
                "FR text": fr_text,
                "reviewer name": "",
                "title": "",
                "date": "",
                "verdict": "",
            }
        )
    return rows


def _report_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for template_id, text_en, text_fr in report_template_rows():
        rows.append(
            {
                "category": "report",
                "item_id": template_id,
                "EN text": text_en,
                "FR text": text_fr,
                "reviewer name": "",
                "title": "",
                "date": "",
                "verdict": "",
            }
        )
    return rows


def main() -> None:
    en = json.loads(LOCALE_EN.read_text(encoding="utf-8"))
    fr = json.loads(LOCALE_FR.read_text(encoding="utf-8"))
    rows = _screen_rows(en, fr) + _notification_rows() + _report_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} language review rows to {OUT}")


if __name__ == "__main__":
    main()
