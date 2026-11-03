from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cleartrace_engine.evaluate import bundle_digest
from cleartrace_engine.pack_map import opa_package_for_slug


class OPAEvaluationError(Exception):
    pass


def default_rego_root() -> Path:
    return Path(__file__).resolve().parents[4] / "policies" / "rego"


def default_opa_bin() -> str:
    env = os.environ.get("OPA_BIN")
    if env and Path(env).exists():
        return env
    for candidate in (
        Path("/tmp/opa-install/opa"),
        Path("/usr/local/bin/opa"),
        Path("/usr/bin/opa"),
    ):
        if candidate.exists():
            return str(candidate)
    found = shutil.which("opa")
    if found:
        return found
    raise OPAEvaluationError(
        "OPA binary not found; set OPA_BIN or install Open Policy Agent"
    )


def build_bundle(rego_root: Path, bundle_dir: Path) -> Path:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    opa = default_opa_bin()
    subprocess.run(
        [opa, "build", "-b", str(rego_root), "-o", str(bundle_dir / "bundle.tar.gz")],
        check=True,
        capture_output=True,
        text=True,
    )
    return bundle_dir / "bundle.tar.gz"


def evaluate_pack_control(
    *,
    pack_slug: str,
    control_key: str,
    payload: dict[str, Any],
    rego_root: Path | None = None,
) -> dict[str, Any]:
    root = rego_root or default_rego_root()
    opa = default_opa_bin()
    opa_pkg = opa_package_for_slug(pack_slug)
    query = f"data.cleartrace.{opa_pkg}.evaluation"
    body = {**payload, "control_key": control_key, "pack_slug": pack_slug}
    proc = subprocess.run(
        [
            opa,
            "eval",
            "-b",
            str(root),
            "-I",
            query,
            "--format",
            "json",
        ],
        input=json.dumps(body),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise OPAEvaluationError(proc.stderr or proc.stdout)
    data = json.loads(proc.stdout)
    result = data.get("result")
    if not result:
        raise OPAEvaluationError(f"No OPA result for {pack_slug}/{control_key}")
    value = result[0].get("expressions", [{}])[0].get("value")
    if value is None:
        raise OPAEvaluationError(f"Undefined OPA evaluation for {pack_slug}/{control_key}")
    return value


def engine_bundle_digest(rego_root: Path | None = None) -> str:
    return bundle_digest(rego_root or default_rego_root())
