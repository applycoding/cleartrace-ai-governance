#!/usr/bin/env python3
"""Generate the T-13 five-state golden set from the shipped policy packs.

How the cases are built (read this before citing T-13):

* Inputs come from a full enumeration over every shipped control: production use
  on/off, impact levels 1-4, every subset of the control's evidence types (valid),
  one unauthorised and one expired item per type, and for DADM 6.3.8 every subset
  of the three Appendix C GBA+ elements.
* The expected state and reason code are the assessment engine's output at
  generation time, checked against the state the case was selected for. They are
  not derived independently from the clause text.
* Where a state has fewer than 50 enumerated inputs, cases are added by attaching
  valid evidence of a type the control does not use (``variation`` is
  ``unrelated_evidence_added``). The engine must give the same state for them.
* Many enumerated inputs differ only in fields a control ignores (for example the
  impact level on a non-DADM control). ``tests/trl5/test_t13_five_states.py``
  counts the distinct inputs after removing those fields and records the counts,
  and the TRL 5 report keeps T-13 partial.
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
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))

from cleartrace_engine.framework_studio import list_packs, load_pack  # noqa: E402
from cleartrace_engine.pipeline import assess_pack_control  # noqa: E402

PACKS = ROOT / "policies" / "packs"
OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"
REPLAY_OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_rule_replay_snapshots.json"
PER_STATE = 50
STATES = ("not_applicable", "met", "partially_met", "not_met", "unable_to_determine")
GBA_ELEMENTS = ("population_impact_assessment", "di_experts_consulted", "mitigation_measures")


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
            if control["control_key"] == "CA-DADM-6-3-8":
                for size in range(len(GBA_ELEMENTS) + 1):
                    for subset in itertools.combinations(GBA_ELEMENTS, size):
                        out.append((system, [_ev("gba_plus_record", covers=list(subset))]))
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


def _round_robin(groups: dict[str, list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    queues = [list(v) for _k, v in sorted(groups.items())]
    while len(picked) < limit and any(queues):
        for queue in queues:
            if queue and len(picked) < limit:
                picked.append(queue.pop(0))
    return picked


_ENUMERATION: tuple[dict[str, dict[str, list[dict[str, Any]]]], set[str]] | None = None


def _enumerate() -> tuple[dict[str, dict[str, list[dict[str, Any]]]], set[str]]:
    global _ENUMERATION
    if _ENUMERATION is not None:
        return _ENUMERATION
    controls: list[tuple[dict[str, Any], dict[str, Any]]] = []
    all_types: set[str] = {"gba_plus_record"}
    for path in list_packs(PACKS):
        pack = load_pack(path)
        for control in pack["controls"]:
            controls.append((pack, control))
            all_types.update(str(e["type"]) for e in control.get("evidence_specs", []))
    by_state: dict[str, dict[str, list[dict[str, Any]]]] = {s: defaultdict(list) for s in STATES}
    for pack, control in controls:
        for system, evidence in _inputs(control):
            output = _assess(pack, control, system, evidence)
            by_state[output.outcome_state][control["control_key"]].append(
                {
                    "pack": pack,
                    "control": control,
                    "system": system,
                    "evidence": evidence,
                    "variation": "enumerated",
                    "output": output,
                }
            )
    _ENUMERATION = (by_state, all_types)
    return _ENUMERATION


def select_cases(state: str, count: int, *, skip: int = 0) -> list[dict[str, Any]]:
    """``count`` cases for ``state``: enumerated inputs spread across controls first,
    then inputs with unrelated valid evidence added. ``skip`` drops that many from the
    front of the enumerated round-robin (used to keep two selections apart)."""
    by_state, all_types = _enumerate()
    ordered = _round_robin(by_state[state], 10_000)[skip:]
    chosen = ordered[:count]
    if len(chosen) < count:
        extra: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for base in [c for group in by_state[state].values() for c in group]:
            own = {str(e["type"]) for e in base["control"].get("evidence_specs", [])} | {"gba_plus_record"}
            for kind in sorted(all_types - own):
                evidence = [*base["evidence"], _ev(kind)]
                output = _assess(base["pack"], base["control"], base["system"], evidence)
                if output.outcome_state != state:
                    raise RuntimeError(f"unrelated {kind} evidence changed {base['control']['control_key']}")
                extra[base["control"]["control_key"]].append(
                    {**base, "evidence": evidence, "variation": "unrelated_evidence_added", "output": output}
                )
        chosen += _round_robin(extra, count - len(chosen))
    if len(chosen) != count:
        raise RuntimeError(f"{state}: only {len(chosen)} cases")
    for item in chosen:
        if item["output"].outcome_state != state:
            raise RuntimeError(f"{state}: selected case gave {item['output'].outcome_state}")
    return chosen


def build() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for state in STATES:
        for idx, item in enumerate(select_cases(state, PER_STATE)):
            output = item["output"]
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
                    "expect": {"outcome_state": output.outcome_state, "reason_code": output.reason_code},
                    "_snapshot": asdict(output),
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
    print(f"wrote {len(cases)} golden cases and {len(replay)} replay snapshots")


if __name__ == "__main__":
    main()
