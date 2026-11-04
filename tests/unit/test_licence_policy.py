"""Licence policy (docs/LICENSE_POLICY.md) as applied by tools/licence_gate.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import licence_gate  # noqa: E402
import third_party_licences as tpl  # noqa: E402


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("MIT", "permissive"),
        ("Apache-2.0 OR BSD-3-Clause", "permissive"),
        ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", "permissive"),
        ("MPL-2.0 AND (Apache-2.0 OR MIT)", "weak-copyleft"),
        ("LGPL-3.0-only", "weak-copyleft"),
        ("GPL-3.0-only OR MIT", "permissive"),
        ("GPL-2.0-only", "strong-copyleft"),
        ("AGPL-3.0-or-later", "strong-copyleft"),
        ("MIT AND GPL-3.0-only", "strong-copyleft"),
        ("SSPL-1.0", "source-available"),
        ("BUSL-1.1", "source-available"),
        ("UNKNOWN", "unknown"),
        ("Some-Custom-Licence", "unknown"),
        ("NOT INSTALLED", "not-shipped"),
    ],
)
def test_classify(expr: str, expected: str) -> None:
    assert tpl.classify(expr) == expected


def _dep(name: str, licence: str) -> tpl.Dep:
    return tpl.Dep("python", name, "1.0", licence, "test", "https://example.invalid/src.tar.gz")


def test_policy_rejects_strong_copyleft_and_unknown() -> None:
    problems = licence_gate.dependency_policy(
        [_dep("gplpkg", "GPL-3.0-only"), _dep("mystery", "UNKNOWN")]
    )
    assert len(problems) == 2
    assert "strong-copyleft" in problems[0]
    assert "unknown" in problems[1]


def test_policy_requires_weak_copyleft_listed_unmodified() -> None:
    problems = licence_gate.dependency_policy([_dep("not-a-real-lgpl-package", "LGPL-3.0-only")])
    assert problems and "not listed as used unmodified" in problems[0]


def test_policy_allows_listed_weak_copyleft_and_permissive() -> None:
    assert (
        licence_gate.dependency_policy([_dep("psycopg", "LGPL-3.0-only"), _dep("fastapi", "MIT")])
        == []
    )


def test_own_source_token_scan_ignores_lgpl(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("uses LGPL-3.0-only and MPL-2.0 libraries unmodified", encoding="utf-8")
    assert licence_gate.scan_file(f) == []
    f.write_text("licensed GPL-3.0", encoding="utf-8")
    assert licence_gate.scan_file(f)


def test_own_manifests_carry_cleartrace_licence() -> None:
    assert licence_gate.own_manifests() == []
