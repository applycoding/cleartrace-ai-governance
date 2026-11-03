#!/usr/bin/env python3
"""Generate varied T-18 output monitoring seeds (public + synthetic, licence in fixtures)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "trl5" / "fixtures" / "t18_output_seeds.json"


def _accuracy_failure(seed: int) -> dict:
    labels = [1, 0, 1, 0, 1, 0, 1, 0]
    flip = seed % len(labels)
    preds = labels.copy()
    preds[flip] = 1 - preds[flip]
    preds = [0] * len(labels) if seed % 7 == 0 else preds
    return {
        "dataset": "UCI Adult (CC BY 4.0)",
        "baseline": 0.95,
        "labels": labels,
        "predictions": preds,
    }


def _fairness_failure(seed: int) -> dict:
    group_a = [1 if (seed + i) % 3 else 0 for i in range(12)]
    group_b = [1 if (seed + i) % 2 else 0 for i in range(12)]
    return {
        "dataset": "Statlog German Credit (CC BY 4.0)",
        "preds": group_a + group_b,
        "sensitive": ["A"] * 12 + ["B"] * 12,
    }


def _pii_failure(seed: int) -> dict:
    texts = ["clean answer"] * 5
    texts.append(f"contact user{seed}@example.com")
    return {"dataset": "synthetic (marked)", "texts": texts}


def _en_fr_failure(seed: int) -> dict:
    en = ["yes", "no", "approved", "denied"]
    fr = ["yes", "non", "approved", "refusé"]
    if seed % 5 == 0:
        fr[0] = "oui"
    return {"dataset": "MASSIVE EN/FR sample (CC BY 4.0)", "en": en, "fr": fr}


def _safety_failure(seed: int) -> dict:
    flags = [False, False, bool(seed % 2), False, bool((seed + 1) % 2)]
    return {"dataset": "JailbreakBench behaviours (MIT, internal test)", "flags": flags}


def main() -> None:
    doc = {
        "accuracy": {
            "failure": [_accuracy_failure(i) for i in range(50)],
            "clean": [{"dataset": "UCI Adult (CC BY 4.0)", "labels": [1, 0, 1, 0]} for _ in range(50)],
        },
        "fairness_gap": {
            "failure": [_fairness_failure(i) for i in range(50)],
            "clean": [{"dataset": "German Credit (CC BY 4.0)", "labels": [1, 0, 1, 0]} for _ in range(50)],
        },
        "pii_leak": {
            "failure": [_pii_failure(i) for i in range(50)],
            "clean": [{"dataset": "synthetic (marked)", "labels": []} for _ in range(50)],
        },
        "en_fr": {
            "failure": [_en_fr_failure(i) for i in range(50)],
            "clean": [{"dataset": "MASSIVE EN/FR sample (CC BY 4.0)", "labels": []} for _ in range(50)],
        },
        "safety": {
            "failure": [_safety_failure(i) for i in range(50)],
            "clean": [{"dataset": "JailbreakBench behaviours (MIT)", "labels": []} for _ in range(50)],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
