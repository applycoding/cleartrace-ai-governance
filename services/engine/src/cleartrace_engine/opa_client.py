"""Client for the OPA policy server that evaluates ClearTrace Rego packs.

The engine does not start processes. OPA runs as a separate server
(``opa run --server policies/rego``) and the engine queries its Data API.
Set ``CLEARTRACE_OPA_URL`` to the server address; the default is the
usual local sidecar address.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from cleartrace_engine.evaluate import bundle_digest
from cleartrace_engine.pack_map import opa_package_for_slug

DEFAULT_OPA_URL = "http://127.0.0.1:8181"
OPA_TIMEOUT_SECONDS = 10.0


class OPAEvaluationError(Exception):
    pass


def default_rego_root() -> Path:
    return Path(__file__).resolve().parents[4] / "policies" / "rego"


def opa_url() -> str:
    return os.environ.get("CLEARTRACE_OPA_URL", DEFAULT_OPA_URL).rstrip("/")


def evaluate_pack_control(
    *,
    pack_slug: str,
    control_key: str,
    payload: dict[str, Any],
    base_url: str | None = None,
) -> dict[str, Any]:
    opa_pkg = opa_package_for_slug(pack_slug)
    path = "/v1/data/cleartrace/" + opa_pkg.replace(".", "/") + "/evaluation"
    body = {**payload, "control_key": control_key, "pack_slug": pack_slug}
    url = (base_url or opa_url()).rstrip("/") + path
    try:
        response = httpx.post(url, json={"input": body}, timeout=OPA_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise OPAEvaluationError(f"OPA server not reachable at {url}: {exc}") from exc
    if response.status_code != 200:
        raise OPAEvaluationError(
            f"OPA returned HTTP {response.status_code} for {pack_slug}/{control_key}: "
            f"{response.text}"
        )
    data = response.json()
    if not isinstance(data, dict) or "result" not in data:
        raise OPAEvaluationError(f"Undefined OPA evaluation for {pack_slug}/{control_key}")
    value = data["result"]
    if not isinstance(value, dict):
        raise OPAEvaluationError(
            f"OPA evaluation for {pack_slug}/{control_key} is not an object"
        )
    return value


def engine_bundle_digest(rego_root: Path | None = None) -> str:
    return bundle_digest(rego_root or default_rego_root())
