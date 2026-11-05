#!/usr/bin/env python3
"""Per-image OS-package licence report for T-28 (reads artifacts/image-sbom).

Lists, for every shipped or deployed image, how many components Syft found, which
carry a licence the blueprint disallows inside shipped images, and which have no
licence data. Nothing is allow-listed. Images that could not be scanned are listed
as not scanned with the reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from licence_gate import DISALLOWED, licence_tokens  # noqa: E402

IMAGE_DIR = ROOT / "artifacts" / "image-sbom"
REPORT = IMAGE_DIR / "licence_report.json"


def shipped_images() -> list[str]:
    refs: set[str] = set()
    compose = ROOT / "deploy" / "compose" / "docker-compose.yml"
    for line in compose.read_text(encoding="utf-8").splitlines():
        if "image:" in line:
            refs.add(line.split("image:", 1)[1].strip())
    manifest = ROOT / "deploy" / "offline-bundle" / "images.manifest.json"
    if manifest.exists():
        for item in json.loads(manifest.read_text(encoding="utf-8")).get("images", []):
            refs.add(str(item["reference"]))
    return sorted(refs)


def _status() -> dict[str, tuple[str, str]]:
    path = IMAGE_DIR / "scan_status.tsv"
    rows: dict[str, tuple[str, str]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            ref, state, detail = (line.split("\t") + ["", ""])[:3]
            rows[ref] = (state, detail)
    return rows


def build_report() -> dict[str, object]:
    status = _status()
    images: list[dict[str, object]] = []
    for ref in shipped_images():
        state, detail = status.get(ref, ("not_scanned", "no scan recorded"))
        entry: dict[str, object] = {"image": ref, "status": state}
        if state != "scanned":
            entry["reason"] = detail
            images.append(entry)
            continue
        doc = json.loads((IMAGE_DIR / detail).read_text(encoding="utf-8"))
        components = [c for c in doc.get("components", []) or [] if isinstance(c, dict)]
        disallowed: list[dict[str, str]] = []
        missing = 0
        for comp in components:
            tokens = licence_tokens(comp)
            if not tokens:
                missing += 1
            hits = [t for t in tokens if any(b.upper() in t.upper() for b in DISALLOWED)]
            if hits:
                disallowed.append({"component": str(comp.get("name", "")), "licences": "; ".join(hits)})
        entry.update(
            components=len(components),
            disallowed_count=len(disallowed),
            no_licence_data=missing,
            disallowed=disallowed,
        )
        images.append(entry)
    scanned = [i for i in images if i["status"] == "scanned"]
    return {
        "images": images,
        "images_total": len(images),
        "images_scanned": len(scanned),
        "images_not_scanned": [i["image"] for i in images if i["status"] != "scanned"],
        "disallowed_total": sum(int(i["disallowed_count"]) for i in scanned),
        "no_licence_data_total": sum(int(i["no_licence_data"]) for i in scanned),
        "exception_file": "docs/licence_exceptions/SHIPPED_IMAGE_OS_PACKAGES.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-images", action="store_true")
    args = parser.parse_args()
    if args.list_images:
        print("\n".join(shipped_images()))
        return 0
    report = build_report()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for image in report["images"]:  # type: ignore[union-attr]
        if image["status"] == "scanned":
            print(
                f"{image['image']}: {image['components']} components, "
                f"{image['disallowed_count']} with a disallowed licence, "
                f"{image['no_licence_data']} without licence data"
            )
        else:
            print(f"{image['image']}: NOT SCANNED ({image.get('reason', '')})")
    print(
        f"images scanned {report['images_scanned']}/{report['images_total']}; "
        f"disallowed-licence components {report['disallowed_total']}; "
        f"exception file {report['exception_file']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
