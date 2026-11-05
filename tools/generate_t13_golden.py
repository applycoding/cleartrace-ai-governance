#!/usr/bin/env python3
"""Generate the T-13 five-state golden set from the shipped policy packs.

How the cases are built (read this before citing T-13):

* Inputs come from a full enumeration over every shipped control: production use
  on/off, impact levels 1-4, every subset of the control's evidence types (valid),
  one unauthorised and one expired item per type, and for multi-element DADM
  evidence types every subset of the required covers list.
* The expected state and reason code come from ``tools/t13_oracle.py``, which
  encodes the clause text of the shipped packs independently of OPA and the
  assessment engine. The generator keeps a case only when the engine agrees.
* Cases are selected for behavioural distinctness (control + relevant system
  fields + evidence). Unrelated evidence padding is used only if a state still
  has fewer than 50 distinct inputs after enumeration.
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "cleartrace-contracts" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from cleartrace_engine.framework_studio import list_packs, load_pack  # noqa: E402
from cleartrace_engine.pipeline import assess_pack_control  # noqa: E402

from t13_oracle import CONTROLS, multi_element_types, oracle_outcome  # noqa: E402

PACKS = ROOT / "policies" / "packs"
OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"
REPLAY_OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_rule_replay_snapshots.json"
PER_STATE = 50
STATES = ("not_applicable", "met", "partially_met", "not_met", "unable_to_determine")
MULTI = multi_element_types()


def _ev(kind: str, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"type": kind, "authorized_submitter": True, "valid_until": "2099-06-01"}
    item.update(extra)
    return item


def _inputs(control: dict[str, Any]) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    types = [str(e["type"]) for e in control.get("evidence_specs", [])]
    out: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for prod in (False, True):
        for level in (1, 2, 3, 4):
            system = {"planned_production_use": prod, "impact_level": level}
            for size in range(len(types) + 1):
                for subset in itertools.combinations(types, size):
                    out.append((system, [_ev(t) for t in subset]))
            for kind in types:
                out.append((system, [_ev(kind, authorized_submitter=False)]))
                out.append((system, [_ev(kind, valid_until="expired")]))
                if kind in MULTI:
                    elements = MULTI[kind]
                    for esize in range(len(elements) + 1):
                        for subset in itertools.combinations(elements, esize):
                            out.append((system, [_ev(kind, covers=list(subset))]))
    return out


def _assess(pack: dict[str, Any], control: dict[str, Any], system: dict[str, Any], evidence: list[dict[str, Any]]):
    output, _ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=system,
        evidence=evidence,
        pack_slug=str(pack["slug"]),
        cel_context=system,
    )
    return output


def _canonical(control_key: str, system: dict[str, Any], evidence: list[dict[str, Any]], state: str) -> str:
    """Behavioural identity used to prefer distinct cases."""
    sys_fields = {"planned_production_use": system.get("planned_production_use")}
    # Keep impact_level only when the oracle rule is level-sensitive.
    spec = CONTROLS.get(control_key)
    if spec is not None and (
        spec.apply != "production"
        or spec.elements_for_level is not None
    ):
        sys_fields["impact_level"] = system.get("impact_level")
    return json.dumps([control_key, sys_fields, evidence], sort_keys=True)


def _round_robin_distinct(
    groups: dict[str, list[dict[str, Any]]], limit: int
) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    queues = [list(v) for _k, v in sorted(groups.items())]
    while len(picked) < limit and any(queues):
        progressed = False
        for queue in queues:
            while queue and len(picked) < limit:
                item = queue.pop(0)
                key = _canonical(
                    item["control"]["control_key"],
                    item["system"],
                    item["evidence"],
                    item["expect_state"],
                )
                if key in seen:
                    continue
                seen.add(key)
                picked.append(item)
                progressed = True
                break
        if not progressed:
            break
    return picked


_ENUMERATION: tuple[dict[str, dict[str, list[dict[str, Any]]]], set[str]] | None = None


def _enumerate() -> tuple[dict[str, dict[str, list[dict[str, Any]]]], set[str]]:
    global _ENUMERATION
    if _ENUMERATION is not None:
        return _ENUMERATION
    controls: list[tuple[dict[str, Any], dict[str, Any]]] = []
    all_types: set[str] = set(MULTI)
    for path in list_packs(PACKS):
        pack = load_pack(path)
        for control in pack["controls"]:
            if control["control_key"] not in CONTROLS:
                raise RuntimeError(f"missing oracle rule for {control['control_key']}")
            controls.append((pack, control))
            all_types.update(str(e["type"]) for e in control.get("evidence_specs", []))
    by_state: dict[str, dict[str, list[dict[str, Any]]]] = {s: defaultdict(list) for s in STATES}
    mismatches = 0
    for pack, control in controls:
        for system, evidence in _inputs(control):
            expect_state, expect_reason = oracle_outcome(
                control["control_key"], system, evidence
            )
            output = _assess(pack, control, system, evidence)
            if output.outcome_state != expect_state or output.reason_code != expect_reason:
                mismatches += 1
                if mismatches <= 8:
                    print(
                        "MISMATCH",
                        control["control_key"],
                        system,
                        evidence,
                        "oracle",
                        expect_state,
                        expect_reason,
                        "engine",
                        output.outcome_state,
                        output.reason_code,
                    )
                continue
            by_state[expect_state][control["control_key"]].append(
                {
                    "pack": pack,
                    "control": control,
                    "system": system,
                    "evidence": evidence,
                    "variation": "enumerated",
                    "output": output,
                    "expect_state": expect_state,
                    "expect_reason": expect_reason,
                }
            )
    if mismatches:
        raise RuntimeError(f"oracle/engine mismatches: {mismatches}")
    _ENUMERATION = (by_state, all_types)
    return _ENUMERATION


def select_cases(state: str, count: int, *, skip: int = 0) -> list[dict[str, Any]]:
    by_state, all_types = _enumerate()
    ordered = _round_robin_distinct(by_state[state], 10_000)[skip:]
    chosen = ordered[:count]
    if len(chosen) < count:
        extra: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for base in [c for group in by_state[state].values() for c in group]:
            own = {str(e["type"]) for e in base["control"].get("evidence_specs", [])} | set(MULTI)
            for kind in sorted(all_types - own):
                evidence = [*base["evidence"], _ev(kind)]
                expect_state, expect_reason = oracle_outcome(
                    base["control"]["control_key"], base["system"], evidence
                )
                if expect_state != state:
                    continue
                output = _assess(base["pack"], base["control"], base["system"], evidence)
                if output.outcome_state != state or output.reason_code != expect_reason:
                    continue
                extra[base["control"]["control_key"]].append(
                    {
                        **base,
                        "evidence": evidence,
                        "variation": "unrelated_evidence_added",
                        "output": output,
                        "expect_state": expect_state,
                        "expect_reason": expect_reason,
                    }
                )
        chosen += _round_robin_distinct(extra, count - len(chosen))
    if len(chosen) != count:
        raise RuntimeError(f"{state}: only {len(chosen)} distinct cases")
    return chosen


def build() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for state in STATES:
        for idx, item in enumerate(select_cases(state, PER_STATE)):
            control = item["control"]
            cases.append(
                {
                    "id": f"{state}-{idx:02d}",
                    "pack_slug": item["pack"]["slug"],
                    "control_key": control["control_key"],
                    "clause_ref": control.get("clause_ref", ""),
                    "variation": item["variation"],
                    "system": item["system"],
                    "evidence": item["evidence"],
                    "expect": {
                        "outcome_state": item["expect_state"],
                        "reason_code": item["expect_reason"],
                    },
                    "_snapshot": asdict(item["output"]),
                }
            )
    return cases


def main() -> None:
    cases = build()
    OUT.write_text(
        json.dumps([{k: v for k, v in c.items() if k != "_snapshot"} for c in cases], indent=2) + "\n",
        encoding="utf-8",
    )
    replay = [
        {
            "id": c["id"],
            "pack_slug": c["pack_slug"],
            "control_key": c["control_key"],
            "system": c["system"],
            "evidence": c["evidence"],
            "snapshot": c["_snapshot"],
        }
        for c in cases
        if c["id"].endswith(("-00", "-01"))
    ]
    REPLAY_OUT.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
    unrelated = sum(1 for c in cases if c["variation"] == "unrelated_evidence_added")
    print(f"wrote {len(cases)} golden cases ({unrelated} unrelated-evidence) and {len(replay)} replay snapshots")


if __name__ == "__main__":
    main()
