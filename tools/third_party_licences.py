#!/usr/bin/env python3
"""Generate THIRD_PARTY_LICENSES.md from the lock files and installed package metadata.

Python: every non-dev package that `uv export --no-dev --all-packages` resolves from
uv.lock, with the licence read from the installed distribution's metadata
(License-Expression, then License, then the licence files, then classifiers) and the
source location taken from uv.lock (sdist URL) and the project URLs.
npm: every non-dev package in web/package-lock.json, with its lock-file licence.
Also listed: vendored files, public datasets and container base images.

Run `uv run python tools/third_party_licences.py` to rewrite the file, or
`--check` to fail when it is out of date. tools/licence_gate.py applies the policy
in docs/LICENSE_POLICY.md to the same records.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "THIRD_PARTY_LICENSES.md"
NPM_LOCK = ROOT / "web" / "package-lock.json"
UV_LOCK = ROOT / "uv.lock"

PERMISSIVE = {
    "MIT",
    "MIT-0",
    "MIT-CMU",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "0BSD",
    "Apache-2.0",
    "ISC",
    "PSF-2.0",
    "Python-2.0",
    "CNRI-Python",
    "Unlicense",
    "Zlib",
    "CC0-1.0",
    "TCL",
    "PostgreSQL",
    "CC-BY-4.0",
}
WEAK_COPYLEFT_PREFIXES = ("LGPL-", "MPL-")
STRONG_COPYLEFT_PREFIXES = ("GPL-", "AGPL-")
SOURCE_AVAILABLE = ("SSPL", "BUSL", "BSL-1.1", "Elastic")

# Free-text licence fields and trove classifiers mapped to SPDX ids.
TEXT_TO_SPDX = {
    "mit": "MIT",
    "mit license": "MIT",
    "mit licence": "MIT",
    "apache-2.0": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "bsd-3-clause": "BSD-3-Clause",
    "3-clause bsd license": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "2-clause bsd": "BSD-2-Clause",
    "isc": "ISC",
    "isc license": "ISC",
    "isc license (iscl)": "ISC",
    "unlicense": "Unlicense",
    "the unlicense (unlicense)": "Unlicense",
    "psfl": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "mpl-2.0": "MPL-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "mpl-2.0 and mit": "MPL-2.0 AND MIT",
    "mit or apache-2.0": "MIT OR Apache-2.0",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0-only",
}


@dataclass(frozen=True)
class Dep:
    ecosystem: str
    name: str
    version: str
    licence: str
    licence_source: str
    source_url: str
    note: str = ""


_SNIFF_MARKERS = (
    ("gnu lesser general public license", "LGPL"),
    ("gnu affero general public license", "AGPL-3.0-only"),
    ("gnu general public license", "GPL"),
    ("mozilla public license", "MPL-2.0"),
    ("apache license", "Apache-2.0"),
    ("permission is hereby granted, free of charge", "MIT"),
    ("redistribution and use in source and binary forms", "BSD"),
    ("this is free and unencumbered software released into the public domain", "Unlicense"),
    ("permission to use, copy, modify, and/or distribute this software", "ISC"),
)


def _sniff_licence_text(text: str) -> str | None:
    """SPDX id of the licence that a licence file states first.

    Only the opening of the file is read, and the earliest marker wins, so bundled
    third-party notices further down (as in scipy's LICENSE.txt) do not decide it.
    """
    low = " ".join(text.split()).lower()[:4000]
    hits = [(low.find(m), spdx) for m, spdx in _SNIFF_MARKERS if m in low]
    if not hits:
        return None
    _, spdx = min(hits)
    if spdx == "LGPL":
        return "LGPL-3.0-only" if "version 3" in low else "LGPL-2.1-only"
    if spdx == "GPL":
        return "GPL-3.0-only" if "version 3" in low else "GPL-2.0-only"
    if spdx == "BSD":
        return (
            "BSD-3-Clause"
            if ("neither the name" in low or "the names of" in low)
            else "BSD-2-Clause"
        )
    return spdx


def _licence_files(dist: md.Distribution) -> list[str]:
    texts: list[str] = []
    for f in dist.files or []:
        name = f.name.upper()
        if name.startswith(("LICENSE", "LICENCE", "COPYING")) and "dist-info" in str(f.parent):
            try:
                texts.append(
                    Path(str(dist.locate_file(f))).read_text(encoding="utf-8", errors="ignore")
                )
            except (OSError, ValueError):
                continue
    return texts


def python_licence(dist: md.Distribution) -> tuple[str, str]:
    meta = dist.metadata
    expr = (meta.get("License-Expression") or "").strip()
    if expr:
        return expr, "License-Expression"
    raw = (meta.get("License") or "").strip()
    first = raw.splitlines()[0].strip() if raw else ""
    if first and first.lower() in TEXT_TO_SPDX:
        return TEXT_TO_SPDX[first.lower()], "License field"
    for text in _licence_files(dist):
        sniffed = _sniff_licence_text(text)
        if sniffed:
            return sniffed, "licence file text"
    if raw:
        sniffed = _sniff_licence_text(raw)
        if sniffed:
            return sniffed, "License field text"
    classifiers = [
        c.split("::")[-1].strip()
        for c in meta.get_all("Classifier") or []
        if c.startswith("License ::")
    ]
    mapped = sorted({TEXT_TO_SPDX[c.lower()] for c in classifiers if c.lower() in TEXT_TO_SPDX})
    if mapped:
        return " OR ".join(mapped), "classifier"
    if classifiers:
        return "UNKNOWN (" + "; ".join(classifiers) + ")", "classifier (variant not stated)"
    return "UNKNOWN", "none"


def _lock_sources() -> dict[str, str]:
    data = tomllib.loads(UV_LOCK.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for pkg in data.get("package", []):
        sdist = pkg.get("sdist", {}) or {}
        if sdist.get("url"):
            out[str(pkg["name"])] = str(sdist["url"])
    return out


def _project_url(dist: md.Distribution) -> str:
    meta = dist.metadata
    urls: dict[str, str] = {}
    for entry in meta.get_all("Project-URL") or []:
        if "," in entry:
            label, url = entry.split(",", 1)
            urls[label.strip().lower()] = url.strip()
    for key in ("source", "source code", "repository", "code", "github", "homepage", "home"):
        if key in urls:
            return urls[key]
    return (meta.get("Home-page") or "").strip()


def shipped_python() -> list[tuple[str, str, str]]:
    """(name, version, marker) for every non-dev package resolved from uv.lock."""
    proc = subprocess.run(
        [
            "uv",
            "export",
            "--no-dev",
            "--all-packages",
            "--no-hashes",
            "--format",
            "requirements-txt",
            "-q",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out: list[tuple[str, str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-e", "./")):
            continue
        spec, _, marker = line.partition(";")
        name, _, version = spec.strip().partition("==")
        out.append((name.strip(), version.strip(), marker.strip()))
    return sorted(out)


def python_deps() -> list[Dep]:
    sources = _lock_sources()
    deps: list[Dep] = []
    for name, version, marker in shipped_python():
        sdist = sources.get(name, "")
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            deps.append(
                Dep(
                    "python",
                    name,
                    version,
                    "NOT INSTALLED",
                    "none",
                    sdist or f"https://pypi.org/project/{name}/{version}/",
                    f"not installed on this platform (marker: {marker or 'none'}); not shipped in the Linux images",
                ),
            )
            continue
        licence, how = python_licence(dist)
        url = _project_url(dist)
        source = sdist or f"https://pypi.org/project/{name}/{version}/"
        if url and url != source:
            source = f"{source} ; {url}"
        note = (
            ""
            if dist.version == version
            else f"installed {dist.version} differs from lock {version}"
        )
        deps.append(Dep("python", name, version, licence, how, source, note))
    return deps


def npm_deps() -> list[Dep]:
    data = json.loads(NPM_LOCK.read_text(encoding="utf-8"))
    deps: list[Dep] = []
    for path, pkg in sorted(data.get("packages", {}).items()):
        if not path or pkg.get("dev") or pkg.get("devOptional"):
            continue
        name = path.split("node_modules/")[-1]
        note = ""
        if pkg.get("optional"):
            plat = "/".join(pkg.get("os", []) or []) or "any OS"
            cpu = "/".join(pkg.get("cpu", []) or []) or "any CPU"
            note = f"optional; installed only on {plat} {cpu}"
        deps.append(
            Dep(
                "npm",
                name,
                str(pkg.get("version", "")),
                str(pkg.get("license") or "UNKNOWN"),
                "package-lock.json",
                str(pkg.get("resolved", "")),
                note,
            )
        )
    return deps


_TOKEN = re.compile(r"\(|\)|\bAND\b|\bOR\b|\bWITH\b|[^\s()]+")


def classify_id(spdx: str) -> str:
    if spdx in PERMISSIVE:
        return "permissive"
    if spdx.startswith(WEAK_COPYLEFT_PREFIXES):
        return "weak-copyleft"
    if spdx.startswith(STRONG_COPYLEFT_PREFIXES):
        return "strong-copyleft"
    if any(s.lower() in spdx.lower() for s in SOURCE_AVAILABLE):
        return "source-available"
    return "unknown"


_RANK = {
    "not-shipped": -1,
    "permissive": 0,
    "weak-copyleft": 1,
    "unknown": 2,
    "strong-copyleft": 3,
    "source-available": 4,
}


def classify(expression: str) -> str:
    """Category of an SPDX expression: AND takes the worst term, OR the best choice."""
    if expression == "NOT INSTALLED":
        return "not-shipped"
    if expression.startswith("UNKNOWN"):
        return "unknown"
    tokens = _TOKEN.findall(expression)
    pos = 0

    def parse_or() -> str:
        nonlocal pos
        best = parse_and()
        while pos < len(tokens) and tokens[pos] == "OR":
            pos += 1
            other = parse_and()
            best = min(best, other, key=_RANK.__getitem__)
        return best

    def parse_and() -> str:
        nonlocal pos
        worst = parse_atom()
        while pos < len(tokens) and tokens[pos] == "AND":
            pos += 1
            other = parse_atom()
            worst = max(worst, other, key=_RANK.__getitem__)
        return worst

    def parse_atom() -> str:
        nonlocal pos
        if pos >= len(tokens):
            return "unknown"
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            inner = parse_or()
            if pos < len(tokens) and tokens[pos] == ")":
                pos += 1
            return inner
        cat = classify_id(tok)
        if pos < len(tokens) and tokens[pos] == "WITH":
            pos += 2
        return cat

    result = parse_or()
    return result if pos == len(tokens) else "unknown"


def collect() -> list[Dep]:
    return python_deps() + npm_deps()


VENDORED = """\
## Vendored source files

| Component | Version | Path | Licence | Copyright | Source |
| --- | --- | --- | --- | --- | --- |
| swagger-ui-dist | 5.17.14 | `services/core-api/static/swagger-ui/` | Apache-2.0 | 2020-2021 SmartBear Software Inc. | https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-5.17.14.tgz |

The swagger-ui-dist files are unmodified copies (SHA-256 values in `LICENSES.md`). Its
licence text is `services/core-api/static/swagger-ui/LICENSE`. Its NOTICE file
(`services/core-api/static/swagger-ui/NOTICE`) reads, in full:

> swagger-ui
> Copyright 2020-2021 SmartBear Software Inc.
"""

DATASETS = """\
## Public datasets (test fixtures)

| Dataset | Path | Licence | Attribution |
| --- | --- | --- | --- |
| UCI Adult | `services/risk/fixtures/uci/adult.data` | CC BY 4.0 | Becker, B. and Kohavi, R. (1996). Adult. UCI Machine Learning Repository. https://doi.org/10.24432/C5XW20 |
| UCI Statlog (German Credit Data) | `services/risk/fixtures/uci/german.data` | CC BY 4.0 | Hofmann, H. (1994). Statlog (German Credit Data). UCI Machine Learning Repository. https://doi.org/10.24432/C5NC77 |

Both files are unmodified copies, used only by the risk tests (T-15, T-16, T-18); licence
terms: https://creativecommons.org/licenses/by/4.0/. Other fixtures (canada-ca/aia-eia-js
under MIT, Government of Canada data under the Open Government Licence – Canada) are
registered with source, licence and SHA-256 in `tests/fixtures/LICENSES.md`.
"""

IMAGES = """\
## Container base images and their OS packages

The deployed images (`deploy/compose/docker-compose.yml`, `deploy/offline-bundle/images.manifest.json`)
contain operating-system packages from their upstream base images, each under its own
licence (many Debian and Alpine packages are GPL or LGPL). These packages are not listed
here one by one. CI builds a Syft SBOM per image and a licence report on every run; download
the `image-sbom` artifact of the CI run (`artifacts/image-sbom/*.cdx.json` and
`licence_report.json`, made by `scripts/ci_image_sbom.sh` and `tools/image_licence_report.py`).
Their source is available from the upstream distributions (https://sources.debian.org/,
https://gitlab.alpinelinux.org/alpine/aports). Under `docs/LICENSE_POLICY.md` these packages
are reported, not gated.
"""


def _weak_section(deps: list[Dep]) -> str:
    weak = [d for d in deps if classify(d.licence) == "weak-copyleft"]
    lines = [
        "## LGPL and MPL components (used unmodified)",
        "",
        "These components are weak-copyleft. ClearTrace uses each of them unmodified, as",
        "published, through its normal public interface (Python import or the npm package",
        "as installed); no file of theirs is changed or copied into ClearTrace source.",
        "",
        "- **LGPL**: you may replace each LGPL library with your own modified or newer",
        "  version. In a Python environment, install the replacement with",
        "  `pip install <your build>` or `uv pip install <path>` over the listed version; the",
        "  ClearTrace licence does not restrict this right (see LICENSE). The complete",
        "  corresponding source of each listed version is at the source location given.",
        "- **MPL-2.0**: the source code of each covered file is available at the source",
        "  location given; ClearTrace does not modify any MPL-covered file.",
        "",
        "| Ecosystem | Package | Version | Licence | Used | Source location |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for d in weak:
        lines.append(
            f"| {d.ecosystem} | {d.name} | {d.version} | {d.licence} | unmodified | {d.source_url} |"
        )
    return "\n".join(lines) + "\n"


def _table(deps: list[Dep], ecosystem: str) -> str:
    rows = [d for d in deps if d.ecosystem == ecosystem]
    lines = [
        "| Package | Version | Licence | Policy class | Licence read from | Source | Note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for d in rows:
        lines.append(
            f"| {d.name} | {d.version} | {d.licence} | {classify(d.licence)} | {d.licence_source} | {d.source_url} | {d.note} |"
        )
    return "\n".join(lines) + "\n"


def counts(deps: list[Dep]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for d in deps:
        bucket = out.setdefault(d.ecosystem, {})
        bucket[d.licence] = bucket.get(d.licence, 0) + 1
    return {k: dict(sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))) for k, v in out.items()}


def render(deps: list[Dep]) -> str:
    py = [d for d in deps if d.ecosystem == "python"]
    npm = [d for d in deps if d.ecosystem == "npm"]
    parts = [
        "# Third-party licences",
        "",
        "ClearTrace itself is Copyright (c) 2026 Arpan Bom, all rights reserved, under the",
        "evaluation-only permission in `LICENSE`. The third-party components, data and files",
        "below keep their own licences; that permission does not restrict the rights those",
        "licences give. Policy: `docs/LICENSE_POLICY.md`.",
        "",
        "This file is generated by `uv run python tools/third_party_licences.py` from `uv.lock`,",
        "the installed package metadata and `web/package-lock.json`. Do not edit it by hand;",
        "`tools/licence_gate.py` fails when it is out of date.",
        "",
        "## Summary by licence",
        "",
        f"Python packages shipped (non-dev, from uv.lock): {len(py)}. npm packages in the web build (non-dev, from package-lock.json): {len(npm)}.",
        "",
        "| Ecosystem | Licence | Packages |",
        "| --- | --- | --- |",
    ]
    for eco, bucket in counts(deps).items():
        for lic, n in bucket.items():
            parts.append(f"| {eco} | {lic} | {n} |")
    parts += [
        "",
        _weak_section(deps),
        "## Python packages",
        "",
        _table(deps, "python"),
        "## npm packages (web build)",
        "",
        "Platform-specific optional packages are listed for every platform the lock file names;",
        "only the one matching the build host is installed.",
        "",
        _table(deps, "npm"),
        VENDORED,
        DATASETS,
        IMAGES,
    ]
    return "\n".join(parts).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail when THIRD_PARTY_LICENSES.md is out of date"
    )
    args = parser.parse_args(argv)
    text = render(collect())
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(
                "THIRD_PARTY_LICENSES.md is out of date; run uv run python tools/third_party_licences.py"
            )
            return 1
        print("THIRD_PARTY_LICENSES.md is up to date")
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
