from __future__ import annotations

import uuid

from cleartrace_core_api.framework.lifecycle import (
    AssignmentRecord,
    FrameworkLifecycle,
    FrameworkVersionRecord,
)


def test_t10_group_assignment_and_reassessment_on_retire() -> None:
    lifecycle = FrameworkLifecycle()
    fw_old = uuid.uuid4()
    fw_new = uuid.uuid4()
    group_id = uuid.uuid4()
    members = [uuid.uuid4() for _ in range(5)]

    lifecycle.register_version(
        FrameworkVersionRecord(
            id=fw_old, framework_id=uuid.uuid4(), semver="1.0.0", lifecycle="active"
        )
    )
    lifecycle.register_version(
        FrameworkVersionRecord(
            id=fw_new, framework_id=uuid.uuid4(), semver="1.1.0", lifecycle="approved"
        )
    )
    lifecycle.add_assignment(
        AssignmentRecord(
            id=uuid.uuid4(),
            framework_version_id=fw_old,
            ai_system_id=None,
            group_id=group_id,
            criteria_overrides={"impact_level_threshold": 3},
        )
    )

    assigned = lifecycle.assigned_systems(fw_old, {group_id: members})
    assert assigned == set(members)

    lifecycle.replace_version(fw_old, fw_new)
    flags = lifecycle.reassessment_flags()
    assert len(flags) >= 2
    reasons = {f["reason"] for f in flags}
    assert "FRAMEWORK_VERSION_RETIRED" in reasons
    assert "FRAMEWORK_VERSION_ACTIVATED" in reasons
