"""Seeded output-monitoring cases for T-18, each labelled with where its data comes from.

Accuracy seeds use the real Statlog German Credit ``class`` labels and fairness seeds use
the real UCI Adult ``sex`` column (hashed, unmodified copies, see tests/fixtures/LICENSES.md).
The predictions in both are seeded here. PII, EN/FR and safety seeds are hand-written.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from cleartrace_risk.datasets import load_reference_frames

GERMAN_LABELS = (
    "statlog-german-credit@archive-ics-uci (CC BY 4.0): class labels; predictions seeded"
)
ADULT_SEX = "uci-adult@archive-ics-uci (CC BY 4.0): sex column; predictions seeded"
SYNTHETIC = "synthetic (hand-written, tests/trl5/t18_seeds.py)"
EXPECTED_LABELS = {
    "accuracy": GERMAN_LABELS,
    "fairness_gap": ADULT_SEX,
    "pii_leak": SYNTHETIC,
    "en_fr": SYNTHETIC,
    "safety": SYNTHETIC,
}


@dataclass(frozen=True)
class OutputSeed:
    dimension: str
    seed_id: int
    source_label: str
    synthetic_reason: str | None = None


def _german_rows(count: int) -> pd.DataFrame:
    _adult, german = load_reference_frames()
    return german.head(count).reset_index(drop=True)


def _adult_rows(count: int) -> pd.DataFrame:
    adult, _german = load_reference_frames()
    return adult.head(count).reset_index(drop=True)


def accuracy_failure(seed_id: int) -> tuple[list[int], list[int], float, OutputSeed]:
    rows = _german_rows(8)
    labels = [int(v) for v in rows["class"].tolist()]
    preds = labels.copy()
    idx = seed_id % len(preds)
    preds[idx] = 2 if labels[idx] == 1 else 1
    meta = OutputSeed(
        dimension="accuracy",
        seed_id=seed_id,
        source_label=GERMAN_LABELS,
    )
    return preds, labels, 0.95, meta


def accuracy_clean(seed_id: int) -> tuple[list[int], list[int], float, OutputSeed]:
    rows = _german_rows(8)
    labels = [int(v) for v in rows["class"].tolist()]
    meta = OutputSeed(
        dimension="accuracy",
        seed_id=seed_id,
        source_label=GERMAN_LABELS,
    )
    return labels.copy(), labels, 0.9, meta


def _balanced_adult_sample(size: int) -> tuple[list[int], list[str]]:
    adult, _german = load_reference_frames()
    half = max(4, size // 2)
    males = adult[adult["sex"] == "Male"].head(half)
    females = adult[adult["sex"] == "Female"].head(half)
    sample = pd.concat([males, females], ignore_index=True).reset_index(drop=True)
    sensitive = sample["sex"].astype(str).tolist()
    preds: list[int] = []
    group_counts: dict[str, int] = {}
    for idx, sex in enumerate(sensitive):
        count = group_counts.get(sex, 0)
        preds.append(count % 2)
        group_counts[sex] = count + 1
    return preds, sensitive


def fairness_failure(seed_id: int) -> tuple[list[int], list[str], OutputSeed]:
    rows = _adult_rows(40)
    sensitive = rows["sex"].astype(str).tolist()
    majority = sensitive[seed_id % len(sensitive)]
    preds = [1 if value == majority else 0 for value in sensitive]
    meta = OutputSeed(
        dimension="fairness_gap",
        seed_id=seed_id,
        source_label=ADULT_SEX,
    )
    return preds, sensitive, meta


def fairness_clean(seed_id: int) -> tuple[list[int], list[str], OutputSeed]:
    preds, sensitive = _balanced_adult_sample(20 + (seed_id % 4))
    meta = OutputSeed(
        dimension="fairness_gap",
        seed_id=seed_id,
        source_label=ADULT_SEX,
    )
    return preds, sensitive, meta


def pii_failure(seed_id: int) -> tuple[list[str], OutputSeed]:
    texts = ["clean output"] * 5 + [f"reach me at user{seed_id}@example.com"]
    meta = OutputSeed(
        dimension="pii_leak",
        seed_id=seed_id,
        source_label=SYNTHETIC,
        synthetic_reason="No public corpus maps model outputs to PII spans for this detector.",
    )
    return texts, meta


def pii_clean(seed_id: int) -> tuple[list[str], OutputSeed]:
    _ = seed_id
    meta = OutputSeed(
        dimension="pii_leak",
        seed_id=seed_id,
        source_label=SYNTHETIC,
        synthetic_reason="Clean control strings (no public PII output set in repo).",
    )
    return ["no sensitive content"] * 4, meta


def enfr_failure(seed_id: int) -> tuple[list[str], list[str], OutputSeed]:
    en = ["yes", "no", "approved", f"item-{seed_id}"]
    fr = ["yes", "non", "approved", f"item-{seed_id}"]
    meta = OutputSeed(
        dimension="en_fr",
        seed_id=seed_id,
        source_label=SYNTHETIC,
        synthetic_reason="No public paired EN/FR model-output set is vendored; the pairs are hand-written.",
    )
    return en, fr, meta


def enfr_clean(seed_id: int) -> tuple[list[str], list[str], OutputSeed]:
    answers = [f"same-{seed_id}", "answer"]
    meta = OutputSeed(
        dimension="en_fr",
        seed_id=seed_id,
        source_label=SYNTHETIC,
        synthetic_reason="Matched EN/FR control pairs.",
    )
    return answers, answers, meta


def safety_failure(seed_id: int) -> tuple[list[bool], OutputSeed]:
    flags = [False, False, True, False, bool(seed_id % 3)]
    meta = OutputSeed(
        dimension="safety",
        seed_id=seed_id,
        source_label=SYNTHETIC,
        synthetic_reason="No public harm or jailbreak set is vendored; the flags are hand-written.",
    )
    return flags, meta


def safety_clean(seed_id: int) -> tuple[list[bool], OutputSeed]:
    _ = seed_id
    meta = OutputSeed(
        dimension="safety",
        seed_id=seed_id,
        source_label=SYNTHETIC,
        synthetic_reason="All-safe control flags.",
    )
    return [False, False, False], meta
