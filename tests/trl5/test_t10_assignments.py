from __future__ import annotations

import uuid

from cleartrace_core_api.framework.lifecycle import (
    AssignmentRecord,
    FrameworkLifecycle,
    FrameworkVersionRecord,
)


def test_t10_group_assignment_threshold_override_and_version_flows() -> None:
    lifecycle = FrameworkLifecycle()
    framework_id = uuid.uuid4()
    fw_v1 = uuid.uuid4()
    fw_v2 = uuid.uuid4()
    group_id = uuid.uuid4()
    members = [uuid.uuid4() for _ in range(5)]

    lifecycle.register_version(
        FrameworkVersionRecord(
            id=fw_v1, framework_id=framework_id, semver="1.0.0", lifecycle="active"
        )
    )
    lifecycle.register_version(
        FrameworkVersionRecord(
            id=fw_v2, framework_id=framework_id, semver="1.1.0", lifecycle="approved"
        )
    )

    record = lifecycle.add_assignment(
        AssignmentRecord(
            id=uuid.uuid4(),
            framework_version_id=fw_v1,
            ai_system_id=None,
            group_id=group_id,
            criteria_overrides={"impact_level_threshold": 2, "binding_metric_ids": ["fairness_gap"]},
        )
    )

    assigned = lifecycle.assigned_systems(fw_v1, {group_id: members})
    assert assigned == set(members)
    assert record.criteria_overrides["impact_level_threshold"] == 2

    lifecycle.retire(fw_v1)
    retired_flags = [f for f in lifecycle.reassessment_flags() if f["reason"] == "FRAMEWORK_VERSION_RETIRED"]
    assert len(retired_flags) >= 1

    lifecycle.activate(fw_v2)
    lifecycle.replace_version(fw_v1, fw_v2)

    affected = lifecycle.assigned_systems(fw_v2, {group_id: members})
    assert affected == set(members)
    reasons = {f["reason"] for f in lifecycle.reassessment_flags()}
    assert "FRAMEWORK_VERSION_RETIRED" in reasons
    assert "FRAMEWORK_VERSION_ACTIVATED" in reasons
    assert len(lifecycle.reassessment_flags()) >= 2
