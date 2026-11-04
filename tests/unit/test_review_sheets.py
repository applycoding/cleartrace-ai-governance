from __future__ import annotations

import csv
from pathlib import Path

from tools import review_sheets


def _write(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


T08_HEADER = [
    "case_id",
    "reviewer_1_correct_yes_no",
    "reviewer_1_notes",
    "reviewer_2_correct_yes_no",
    "reviewer_2_notes",
]
T20_HEADER = [
    "category",
    "item_id",
    "EN text",
    "FR text",
    "reviewer name",
    "title",
    "date",
    "verdict",
]


def test_t20_threshold_is_95_percent_of_the_sheet() -> None:
    assert review_sheets.t20_pass_threshold(40) == 38
    assert review_sheets.t20_pass_threshold(20) == 19


def test_blank_sheets_are_blank(tmp_path: Path) -> None:
    t08 = _write(tmp_path / "t08.csv", T08_HEADER, [[f"c{i}", "", "", "", ""] for i in range(140)])
    t20 = _write(
        tmp_path / "t20.csv",
        T20_HEADER,
        [["screen", f"s{i}", "a", "b", "", "", "", ""] for i in range(40)],
    )
    assert review_sheets.t08_summary(t08)["state"] == "blank"
    assert review_sheets.t20_summary(t20)["state"] == "blank"


def test_one_reviewer_only_is_partial(tmp_path: Path) -> None:
    rows = [[f"c{i}", "yes", "", "", ""] for i in range(140)]
    summary = review_sheets.t08_summary(_write(tmp_path / "t08.csv", T08_HEADER, rows))
    assert summary["state"] == "partial"
    assert summary["passes_threshold"] is False


def test_complete_sheets_pass_only_at_the_bar(tmp_path: Path) -> None:
    t08_rows = [[f"c{i}", "yes", "", "yes" if i < 133 else "no", ""] for i in range(140)]
    assert (
        review_sheets.t08_summary(_write(tmp_path / "a.csv", T08_HEADER, t08_rows))[
            "passes_threshold"
        ]
        is True
    )
    t08_rows[0][3] = "no"
    assert (
        review_sheets.t08_summary(_write(tmp_path / "b.csv", T08_HEADER, t08_rows))[
            "passes_threshold"
        ]
        is False
    )
    t20_rows = [
        ["screen", f"s{i}", "a", "b", "R", "T", "2026-11-03", "accept" if i < 38 else "reject"]
        for i in range(40)
    ]
    assert (
        review_sheets.t20_summary(_write(tmp_path / "c.csv", T20_HEADER, t20_rows))[
            "passes_threshold"
        ]
        is True
    )
    t20_rows[0][7] = "reject"
    assert (
        review_sheets.t20_summary(_write(tmp_path / "d.csv", T20_HEADER, t20_rows))[
            "passes_threshold"
        ]
        is False
    )
