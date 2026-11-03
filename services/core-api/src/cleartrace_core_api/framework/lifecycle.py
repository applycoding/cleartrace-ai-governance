"""Framework lifecycle, assignments, and reassessment helpers for the governance API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class FrameworkVersionRecord:
    id: uuid.UUID
    framework_id: uuid.UUID
    semver: str
    lifecycle: str
    effective_from: datetime | None = None


@dataclass
class AssignmentRecord:
    id: uuid.UUID
    framework_version_id: uuid.UUID
    ai_system_id: uuid.UUID | None
    group_id: uuid.UUID | None
    criteria_overrides: dict[str, Any]


class FrameworkLifecycle:
    """In-memory lifecycle state machine used by API routes and TRL 5 tests."""

    def __init__(self) -> None:
        self._versions: dict[uuid.UUID, FrameworkVersionRecord] = {}
        self._assignments: list[AssignmentRecord] = []
        self._reassessment: list[dict[str, Any]] = []

    def register_version(self, record: FrameworkVersionRecord) -> None:
        self._versions[record.id] = record

    def submit(self, version_id: uuid.UUID) -> FrameworkVersionRecord:
        record = self._require(version_id)
        record.lifecycle = "draft"
        return record

    def approve(self, version_id: uuid.UUID) -> FrameworkVersionRecord:
        record = self._require(version_id)
        record.lifecycle = "approved"
        return record

    def activate(self, version_id: uuid.UUID) -> FrameworkVersionRecord:
        record = self._require(version_id)
        record.lifecycle = "active"
        record.effective_from = datetime.now(tz=UTC)
        self.flag_reassessment(version_id, reason="FRAMEWORK_VERSION_ACTIVATED")
        return record

    def retire(self, version_id: uuid.UUID) -> FrameworkVersionRecord:
        record = self._require(version_id)
        record.lifecycle = "retired"
        self.flag_reassessment(version_id, reason="FRAMEWORK_VERSION_RETIRED")
        return record

    def rollback(self, version_id: uuid.UUID, target: uuid.UUID) -> FrameworkVersionRecord:
        current = self._require(version_id)
        current.lifecycle = "deprecated"
        restored = self._require(target)
        restored.lifecycle = "active"
        self.flag_reassessment(restored.id, reason="FRAMEWORK_VERSION_ROLLBACK")
        return restored

    def replace_version(self, old_id: uuid.UUID, new_id: uuid.UUID) -> None:
        self.retire(old_id)
        self.activate(new_id)

    def add_assignment(self, assignment: AssignmentRecord) -> AssignmentRecord:
        self._assignments.append(assignment)
        return assignment

    def members_for_group(
        self, group_id: uuid.UUID, member_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        return [
            assignment.ai_system_id
            for assignment in self._assignments
            if assignment.group_id == group_id and assignment.ai_system_id
        ] or member_ids

    def assigned_systems(
        self,
        framework_version_id: uuid.UUID,
        group_members: dict[uuid.UUID, list[uuid.UUID]],
    ) -> set[uuid.UUID]:
        systems: set[uuid.UUID] = set()
        for assignment in self._assignments:
            if assignment.framework_version_id != framework_version_id:
                continue
            if assignment.ai_system_id:
                systems.add(assignment.ai_system_id)
            if assignment.group_id and assignment.group_id in group_members:
                systems.update(group_members[assignment.group_id])
        return systems

    def flag_reassessment(self, framework_version_id: uuid.UUID, *, reason: str) -> None:
        self._reassessment.append(
            {
                "framework_version_id": str(framework_version_id),
                "reason": reason,
                "created_at": datetime.now(tz=UTC).isoformat(),
            }
        )

    def reassessment_flags(self) -> list[dict[str, Any]]:
        return list(self._reassessment)

    def _require(self, version_id: uuid.UUID) -> FrameworkVersionRecord:
        if version_id not in self._versions:
            raise KeyError(f"Unknown framework version {version_id}")
        return self._versions[version_id]
