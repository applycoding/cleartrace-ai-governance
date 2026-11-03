from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from cleartrace_policy_watch.service import ImpactLink, PolicyWatcherService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "t01"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _hand_compute_impact(
    changed_clause_ids: set[str], links: list[ImpactLink]
) -> tuple[set[UUID], set[str]]:
    systems: set[UUID] = set()
    controls: set[str] = set()
    for link in links:
        if link.clause_id in changed_clause_ids:
            systems.add(link.system_id)
            controls.add(link.control_id)
    return systems, controls


@pytest.mark.parametrize("case_id", [f"substantive-{i:02d}" for i in range(1, 11)])
def test_t01_substantive_policy_changes_detected(case_id: str) -> None:
    meta = json.loads(_load(f"{case_id}.meta.json"))
    links = [
        ImpactLink(
            clause_id=item["clause"], control_id=item["control"], system_id=UUID(item["system_id"])
        )
        for item in meta["impact_links"]
    ]
    watcher = PolicyWatcherService(impact_links=links)
    watcher.capture_snapshot("dadm", "en", _load(f"{case_id}.before.en.html"), make_active=True)
    watcher.capture_snapshot("dadm", "fr", _load(f"{case_id}.before.fr.html"), make_active=True)

    diff_en = watcher.diff_against_active("dadm", "en", _load(f"{case_id}.after.en.html"))
    diff_fr = watcher.diff_against_active("dadm", "fr", _load(f"{case_id}.after.fr.html"))

    assert diff_en.result.substantive_count >= 1
    assert diff_fr.result.substantive_count >= 1

    changed = {c.clause_id for c in diff_en.result.changes if c.substantive}
    expected_changed = set(meta["changed_clauses"])
    assert expected_changed.issubset(changed)

    hand_systems, hand_controls = _hand_compute_impact(changed, links)
    assert set(diff_en.impact_system_ids) == hand_systems
    assert set(diff_en.impact_control_ids) == hand_controls

    with pytest.raises(PermissionError):
        watcher.activate(diff_en.diff_id)
    watcher.approve_by_steward(diff_en.diff_id)
    activated = watcher.activate(diff_en.diff_id)
    assert activated.activated is True


@pytest.mark.parametrize("case_id", [f"formatting-{i:02d}" for i in range(1, 11)])
def test_t01_formatting_only_never_activates(case_id: str) -> None:
    watcher = PolicyWatcherService()
    watcher.capture_snapshot("dadm", "en", _load(f"{case_id}.before.en.html"), make_active=True)
    diff = watcher.diff_against_active("dadm", "en", _load(f"{case_id}.after.en.html"))
    assert diff.result.substantive_count == 0
    assert diff.result.formatting_only_count == 1
    watcher.approve_by_steward(diff.diff_id)
    with pytest.raises(ValueError):
        watcher.activate(diff.diff_id)
    assert diff.activated is False


def test_t01_zero_unapproved_activations() -> None:
    watcher = PolicyWatcherService()
    watcher.capture_snapshot("dadm", "en", _load("substantive-01.before.en.html"), make_active=True)
    diff = watcher.diff_against_active("dadm", "en", _load("substantive-01.after.en.html"))
    with pytest.raises(PermissionError):
        watcher.try_activate_without_approval(diff.diff_id)
