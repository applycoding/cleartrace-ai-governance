from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChangeKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


@dataclass(frozen=True, slots=True)
class ClauseChange:
    clause_id: str
    kind: ChangeKind
    before: str | None
    after: str | None
    substantive: bool


@dataclass(frozen=True, slots=True)
class DiffResult:
    changes: tuple[ClauseChange, ...]
    substantive_count: int
    formatting_only_count: int

    @property
    def has_substantive(self) -> bool:
        return self.substantive_count > 0


def diff_clause_trees(
    before: dict[str, str],
    after: dict[str, str],
    *,
    raw_before: dict[str, str],
    raw_after: dict[str, str],
) -> DiffResult:
    changes: list[ClauseChange] = []
    substantive = 0
    formatting_only = 0
    all_ids = set(before) | set(after)
    for clause_id in sorted(all_ids):
        b_norm = before.get(clause_id)
        a_norm = after.get(clause_id)
        b_raw = raw_before.get(clause_id, "")
        a_raw = raw_after.get(clause_id, "")
        if b_norm is None and a_norm is not None:
            changes.append(
                ClauseChange(clause_id, ChangeKind.ADDED, None, a_norm, substantive=True)
            )
            substantive += 1
            continue
        if a_norm is None and b_norm is not None:
            changes.append(
                ClauseChange(clause_id, ChangeKind.REMOVED, b_norm, None, substantive=True)
            )
            substantive += 1
            continue
        if b_norm == a_norm:
            if b_raw != a_raw:
                changes.append(
                    ClauseChange(
                        clause_id,
                        ChangeKind.CHANGED,
                        b_norm,
                        a_norm,
                        substantive=False,
                    )
                )
                formatting_only += 1
            continue
        changes.append(
            ClauseChange(clause_id, ChangeKind.CHANGED, b_norm, a_norm, substantive=True)
        )
        substantive += 1
    return DiffResult(tuple(changes), substantive, formatting_only)
