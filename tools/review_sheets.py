"""Parse TRL 5 human review sheets (T-08, T-20)."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

T08_PATH = Path(__file__).resolve().parents[1] / "docs" / "trl5" / "t08_explanation_review.csv"
T20_PATH = Path(__file__).resolve().parents[1] / "docs" / "trl5" / "t20_language_review_sheet.csv"

T08_PASS_CORRECT = 133
T08_TOTAL_PAIRS = 140
T20_PASS_SHARE = 0.95  # ClearTrace bar for T-20 (section 18 asks only that the review is recorded)


@dataclass(frozen=True)
class SheetFillState:
    state: str  # blank | partial | complete
    filled_rows: int
    total_rows: int
    detail: str = ""


def _cell(value: str | None) -> str:
    return (value or "").strip()


def _parse_yes_no(value: str | None) -> bool | None:
    text = _cell(value).lower()
    if not text:
        return None
    if text in {"y", "yes", "true", "1", "correct", "ok"}:
        return True
    if text in {"n", "no", "false", "0", "incorrect"}:
        return False
    raise ValueError(f"review answer must be yes/no, got {value!r}")


def t08_load_rows(path: Path = T08_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def t08_fill_state(rows: list[dict[str, str]]) -> SheetFillState:
    if not rows:
        return SheetFillState("blank", 0, 0, "review sheet has no rows")
    filled = 0
    partial_rows: list[str] = []
    for row in rows:
        r1 = _cell(row.get("reviewer_1_correct_yes_no"))
        r2 = _cell(row.get("reviewer_2_correct_yes_no"))
        if r1 and r2:
            filled += 1
        elif r1 or r2:
            partial_rows.append(row.get("case_id", "?"))
    if filled == 0 and not partial_rows:
        return SheetFillState("blank", 0, len(rows))
    if filled < len(rows) or partial_rows:
        detail = (
            f"{len(rows) - filled} rows still missing a reviewer; "
            f"{len(partial_rows)} rows have only one reviewer filled "
            f"(examples: {', '.join(partial_rows[:5])})"
        )
        return SheetFillState("partial", filled, len(rows), detail)
    return SheetFillState("complete", filled, len(rows))


def t08_agreed_correct(rows: list[dict[str, str]]) -> int:
    count = 0
    for row in rows:
        first = _parse_yes_no(row.get("reviewer_1_correct_yes_no"))
        second = _parse_yes_no(row.get("reviewer_2_correct_yes_no"))
        if first is True and second is True:
            count += 1
    return count


def t08_summary(path: Path = T08_PATH) -> dict[str, object]:
    if not path.is_file():
        return {"present": False, "state": "missing", "agreed_correct": 0, "total": 0}
    rows = t08_load_rows(path)
    fill = t08_fill_state(rows)
    agreed = t08_agreed_correct(rows) if fill.state == "complete" else 0
    return {
        "present": True,
        "state": fill.state,
        "agreed_correct": agreed,
        "total": len(rows),
        "passes_threshold": agreed >= T08_PASS_CORRECT and len(rows) == T08_TOTAL_PAIRS,
        "detail": fill.detail,
    }


def t20_load_rows(path: Path = T20_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def t20_fill_state(rows: list[dict[str, str]]) -> SheetFillState:
    if not rows:
        return SheetFillState("blank", 0, 0, "language review sheet has no rows")
    filled = 0
    partial_rows: list[str] = []
    for row in rows:
        verdict = _cell(row.get("verdict"))
        reviewer = _cell(row.get("reviewer name"))
        date = _cell(row.get("date"))
        if verdict and reviewer and date:
            filled += 1
        elif verdict or reviewer or date:
            partial_rows.append(row.get("item_id") or row.get("screen") or "?")
    if filled == 0 and not partial_rows:
        return SheetFillState("blank", 0, len(rows))
    if filled < len(rows) or partial_rows:
        detail = (
            f"{len(rows) - filled} rows missing verdict/reviewer/date; "
            f"{len(partial_rows)} partly filled "
            f"(examples: {', '.join(partial_rows[:5])})"
        )
        return SheetFillState("partial", filled, len(rows), detail)
    return SheetFillState("complete", filled, len(rows))


def t20_acceptable_verdicts(rows: list[dict[str, str]]) -> int:
    count = 0
    for row in rows:
        verdict = _cell(row.get("verdict")).lower()
        if verdict in {"accept", "accepted", "ok", "yes", "pass"}:
            count += 1
    return count


def t20_pass_threshold(total_rows: int) -> int:
    if total_rows <= 0:
        return 0
    return math.ceil(total_rows * T20_PASS_SHARE)


def t20_summary(path: Path = T20_PATH) -> dict[str, object]:
    if not path.is_file():
        return {"present": False, "state": "missing", "acceptable": 0, "total": 0}
    rows = t20_load_rows(path)
    fill = t20_fill_state(rows)
    acceptable = t20_acceptable_verdicts(rows) if fill.state == "complete" else 0
    threshold = t20_pass_threshold(len(rows))
    return {
        "present": True,
        "state": fill.state,
        "acceptable": acceptable,
        "total": len(rows),
        "pass_threshold": threshold,
        "passes_threshold": acceptable >= threshold and fill.state == "complete",
        "detail": fill.detail,
    }
