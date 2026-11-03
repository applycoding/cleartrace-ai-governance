from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from uuid6 import uuid7

from cleartrace_policy_watch.diff import DiffResult, diff_clause_trees
from cleartrace_policy_watch.normalizer import clause_tree_from_html, snapshot_sha256


@dataclass(frozen=True, slots=True)
class ImpactLink:
    clause_id: str
    control_id: str
    system_id: UUID


@dataclass
class PolicyDiffRecord:
    diff_id: UUID
    policy_slug: str
    result: DiffResult
    steward_approved: bool = False
    activated: bool = False
    impact_system_ids: list[UUID] = field(default_factory=list)
    impact_control_ids: list[str] = field(default_factory=list)


class PolicyWatcherService:
    """Snapshot, diff, steward approval gate, and impact set computation."""

    def __init__(self, impact_links: list[ImpactLink] | None = None) -> None:
        self._snapshots: dict[tuple[str, str, str], str] = {}
        self._active_digest: dict[tuple[str, str], str] = {}
        self._diffs: dict[UUID, PolicyDiffRecord] = {}
        self._impact_links = impact_links or []

    def capture_snapshot(
        self, policy_slug: str, locale: str, html: str, *, make_active: bool = False
    ) -> str:
        digest = snapshot_sha256(html)
        self._snapshots[(policy_slug, locale, digest)] = html
        if make_active:
            self._active_digest[(policy_slug, locale)] = digest
        return digest

    def diff_against_active(self, policy_slug: str, locale: str, html: str) -> PolicyDiffRecord:
        active_digest = self._active_digest.get((policy_slug, locale))
        if active_digest is None:
            digest = self.capture_snapshot(policy_slug, locale, html, make_active=True)
            empty = PolicyDiffRecord(
                diff_id=uuid7(),
                policy_slug=policy_slug,
                result=DiffResult((), 0, 0),
            )
            self._diffs[empty.diff_id] = empty
            _ = digest
            return empty
        prior_html = self._snapshots.get((policy_slug, locale, active_digest), "")

        before_raw = clause_tree_from_html(prior_html, normalize=False)
        after_raw = clause_tree_from_html(html, normalize=False)
        before_norm = clause_tree_from_html(prior_html, normalize=True)
        after_norm = clause_tree_from_html(html, normalize=True)
        result = diff_clause_trees(
            before_norm, after_norm, raw_before=before_raw, raw_after=after_raw
        )
        record = PolicyDiffRecord(diff_id=uuid7(), policy_slug=policy_slug, result=result)
        if result.has_substantive:
            record.impact_system_ids, record.impact_control_ids = self._compute_impact(result)
        self._diffs[record.diff_id] = record
        return record

    def approve_by_steward(self, diff_id: UUID) -> PolicyDiffRecord:
        record = self._require_diff(diff_id)
        record.steward_approved = True
        return record

    def activate(self, diff_id: UUID) -> PolicyDiffRecord:
        record = self._require_diff(diff_id)
        if not record.steward_approved:
            msg = "Steward approval required before activation"
            raise PermissionError(msg)
        if record.result.formatting_only_count > 0 and record.result.substantive_count == 0:
            msg = "Formatting-only diffs cannot be activated"
            raise ValueError(msg)
        record.activated = True
        return record

    def try_activate_without_approval(self, diff_id: UUID) -> None:
        record = self._require_diff(diff_id)
        if not record.steward_approved:
            raise PermissionError("blocked")

    def _compute_impact(self, result: DiffResult) -> tuple[list[UUID], list[str]]:
        changed_clauses = {
            c.clause_id for c in result.changes if c.substantive and c.kind.value != "removed"
        }
        systems: set[UUID] = set()
        controls: set[str] = set()
        for link in self._impact_links:
            if link.clause_id in changed_clauses:
                systems.add(link.system_id)
                controls.add(link.control_id)
        return sorted(systems, key=str), sorted(controls)

    def _require_diff(self, diff_id: UUID) -> PolicyDiffRecord:
        record = self._diffs.get(diff_id)
        if record is None:
            msg = f"Unknown diff {diff_id}"
            raise KeyError(msg)
        return record

    async def compute_impact_set(self, policy_diff_id: UUID) -> UUID:
        record = self._require_diff(policy_diff_id)
        if not record.impact_system_ids and record.result.has_substantive:
            record.impact_system_ids, record.impact_control_ids = self._compute_impact(
                record.result
            )
        return policy_diff_id
