"""Output monitoring: accuracy, fairness gap, PII, bilingual consistency, safety."""

from __future__ import annotations

import re

from cleartrace_risk.evaluators.model import disparate_impact_ratio


def output_accuracy_drop(baseline: float, predictions: list[int], labels: list[int]) -> float:
    if not labels:
        return 0.0
    current = sum(int(p == label) for p, label in zip(predictions, labels, strict=True)) / len(
        labels
    )
    return float(baseline - current)


def fairness_gap(y_pred: list[int], sensitive: list[str]) -> float:
    ratio = disparate_impact_ratio(y_pred, sensitive)
    return float(1.0 - ratio)


_PII_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SIN-like
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b\d{3}\s?\d{3}\s?\d{3}\b"),  # FR phone-ish
)


def pii_leak_rate(texts: list[str]) -> float:
    if not texts:
        return 0.0
    hits = 0
    for text in texts:
        if any(pattern.search(text) for pattern in _PII_PATTERNS):
            hits += 1
    presidio_hits = _presidio_hits(texts)
    hits = max(hits, presidio_hits)
    return hits / len(texts)


def _presidio_hits(texts: list[str]) -> int:
    try:
        from presidio_analyzer import AnalyzerEngine

        engine = AnalyzerEngine()
    except Exception:  # noqa: BLE001
        return 0
    count = 0
    for text in texts:
        results = engine.analyze(text=text, language="en")
        if results:
            count += 1
    return count


def en_fr_agreement(en_answers: list[str], fr_answers: list[str]) -> float:
    if not en_answers:
        return 1.0
    matches = sum(
        1
        for en, fr in zip(en_answers, fr_answers, strict=True)
        if en.strip().lower() == fr.strip().lower()
    )
    return matches / len(en_answers)


def safety_attack_success_rate(success_flags: list[bool]) -> float:
    if not success_flags:
        return 0.0
    return sum(1 for flag in success_flags if flag) / len(success_flags)
