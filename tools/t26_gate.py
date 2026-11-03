#!/usr/bin/env python3
"""T-26 gate: read raw scanner outputs and fail on open critical/high findings.

Inputs (all under ``--artifacts``, written by ``scripts/ci_security_suite.sh`` and
the Trivy CI step):

* ``semgrep.json``      Semgrep OSS ``p/ci``; every result counts (ERROR = high).
* ``bandit.json``       Bandit; HIGH severity = high, MEDIUM/LOW counted.
* ``schemathesis.xml``  Schemathesis JUnit; a failing case that includes the
                        server-error check (ST101, any 5xx) = high, any other
                        failed check (schema or status conformance) = medium.
* ``zap-report.json``   OWASP ZAP; riskcode 3 = high, 2 = medium, 1 = low.
* ``trivy.json``        Trivy filesystem scan; CRITICAL/HIGH = critical/high.

A finding is open unless ``docs/security/FINDINGS_TRIAGE.md`` has a row naming the
same tool and rule id with a disposition of ``false positive`` and a written
justification. Severities are never lowered here. Every output must exist and be
non-empty; a missing tool output fails the gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("semgrep.json", "bandit.json", "schemathesis.xml", "zap-report.json", "trivy.json")
BLOCKING = {"critical", "high"}


@dataclass(frozen=True)
class Finding:
    tool: str
    rule: str
    severity: str
    location: str
    message: str


def _semgrep(path: Path) -> list[Finding]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sev = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
    return [
        Finding(
            "semgrep",
            r["check_id"],
            sev.get(r["extra"].get("severity", ""), "medium"),
            f"{r['path']}:{r['start']['line']}",
            r["extra"].get("message", "")[:200],
        )
        for r in data.get("results", [])
    ]


def _bandit(path: Path) -> list[Finding]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Finding(
            "bandit",
            r["test_id"],
            r["issue_severity"].lower(),
            f"{r['filename']}:{r['line_number']}",
            r["issue_text"][:200],
        )
        for r in data.get("results", [])
    ]


def _schemathesis(path: Path) -> tuple[list[Finding], int]:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    out: list[Finding] = []
    for case in cases:
        for node in [*case.findall("failure"), *case.findall("error")]:
            text = f"{node.get('message', '')}\n{node.text or ''}"
            server_error = bool(re.search(r"\bST101\b|Server error", text))
            out.append(
                Finding(
                    "schemathesis",
                    case.get("name", "?"),
                    "high" if server_error else "medium",
                    case.get("name", "?"),
                    " ".join(text.split())[:300],
                )
            )
    return out, len(cases)


def _zap(path: Path) -> list[Finding]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sev = {"3": "high", "2": "medium", "1": "low", "0": "info"}
    out: list[Finding] = []
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            out.append(
                Finding(
                    "zap",
                    str(alert.get("pluginid", "?")),
                    sev.get(str(alert.get("riskcode", "")), "info"),
                    f"{alert.get('count', '?')} instance(s)",
                    alert.get("name", alert.get("alert", ""))[:200],
                )
            )
    return out


def _trivy(path: Path) -> list[Finding]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[Finding] = []
    for result in data.get("Results", []) or []:
        for vuln in result.get("Vulnerabilities", []) or []:
            out.append(
                Finding(
                    "trivy",
                    vuln.get("VulnerabilityID", "?"),
                    vuln.get("Severity", "UNKNOWN").lower(),
                    f"{result.get('Target', '?')}:{vuln.get('PkgName', '?')}",
                    vuln.get("Title", "")[:200],
                )
            )
        for mis in result.get("Misconfigurations", []) or []:
            out.append(
                Finding(
                    "trivy",
                    mis.get("ID", "?"),
                    mis.get("Severity", "UNKNOWN").lower(),
                    result.get("Target", "?"),
                    mis.get("Title", "")[:200],
                )
            )
        for sec in result.get("Secrets", []) or []:
            out.append(
                Finding(
                    "trivy",
                    sec.get("RuleID", "?"),
                    sec.get("Severity", "UNKNOWN").lower(),
                    result.get("Target", "?"),
                    sec.get("Title", "")[:200],
                )
            )
    return out


def load_triage(path: Path) -> set[tuple[str, str]]:
    """Return (tool, rule) pairs recorded as justified false positives."""
    accepted: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0].lower() in {"scanner", "---"} or cells[0].startswith("_"):
            continue
        tool, rule, _sev, disposition, justification = cells
        if disposition.lower() == "false positive" and len(justification) >= 40:
            accepted.add((tool.lower(), rule))
    return accepted


def evaluate(artifacts: Path, triage: Path) -> dict[str, object]:
    problems: list[str] = []
    for name in REQUIRED:
        p = artifacts / name
        if not p.is_file() or p.stat().st_size == 0:
            problems.append(f"missing or empty tool output: {name}")
    findings: list[Finding] = []
    schemathesis_cases = 0
    loaders = {
        "semgrep.json": _semgrep,
        "bandit.json": _bandit,
        "zap-report.json": _zap,
        "trivy.json": _trivy,
    }
    for name, loader in loaders.items():
        p = artifacts / name
        if p.is_file() and p.stat().st_size:
            findings.extend(loader(p))
    st = artifacts / "schemathesis.xml"
    if st.is_file() and st.stat().st_size:
        st_findings, schemathesis_cases = _schemathesis(st)
        findings.extend(st_findings)
        if schemathesis_cases == 0:
            problems.append("schemathesis.xml has no test cases")
    accepted = load_triage(triage)
    open_blocking = [
        f for f in findings if f.severity in BLOCKING and (f.tool, f.rule) not in accepted
    ]
    by_tool: dict[str, dict[str, int]] = {}
    for f in findings:
        by_tool.setdefault(f.tool, {}).setdefault(f.severity, 0)
        by_tool[f.tool][f.severity] += 1
    return {
        "gate_passed": not problems and not open_blocking,
        "problems": problems,
        "findings_total": len(findings),
        "open_critical_high": len(open_blocking),
        # Only triage rows that match a finding in this run are reported as applied.
        "triaged_false_positives": sorted(
            {f"{f.tool}:{f.rule}" for f in findings if (f.tool, f.rule) in accepted}
        ),
        "by_tool": by_tool,
        "schemathesis_cases": schemathesis_cases,
        "findings": [asdict(f) for f in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts" / "t26")
    parser.add_argument("--triage", type=Path, default=ROOT / "docs" / "security" / "FINDINGS_TRIAGE.md")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = evaluate(args.artifacts, args.triage)
    if args.summary:
        args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "findings"}, indent=2))
    listed = result["findings"]
    for f in listed if isinstance(listed, list) else []:
        print(f"  [{f['severity']}] {f['tool']} {f['rule']} {f['location']} {f['message'][:120]}")
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
