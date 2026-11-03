"""Shared test fixtures.

``opa_server`` starts a real OPA policy server on a free local port with the
Rego packs under ``policies/rego`` and points the engine at it through
``CLEARTRACE_OPA_URL``. When ``CLEARTRACE_OPA_URL`` is already set (for example
an OPA sidecar), that server is used instead. A missing OPA binary is an error,
not a skip.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
REGO_ROOT = ROOT / "policies" / "rego"


def _opa_binary() -> str:
    env = os.environ.get("OPA_BIN")
    if env and Path(env).is_file():
        return env
    found = shutil.which("opa")
    if found:
        return found
    raise RuntimeError(
        "OPA binary not found: run scripts/install_opa.sh and set OPA_BIN or add opa to PATH"
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def opa_server() -> Iterator[str]:
    existing = os.environ.get("CLEARTRACE_OPA_URL")
    if existing:
        yield existing
        return

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    # OPA writes its log to stderr; send it to a file so a full pipe never blocks it.
    with tempfile.TemporaryFile(mode="w+") as log:
        proc = subprocess.Popen(
            [
                _opa_binary(),
                "run",
                "--server",
                "--disable-telemetry",
                "--log-level",
                "error",
                "--addr",
                f"127.0.0.1:{port}",
                str(REGO_ROOT),
            ],
            stdout=subprocess.DEVNULL,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                if proc.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(f"OPA server exited early: {log.read()}")
                try:
                    if httpx.get(f"{url}/health", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError("OPA server did not become healthy within 30 s")
                time.sleep(0.1)
            os.environ["CLEARTRACE_OPA_URL"] = url
            yield url
        finally:
            os.environ.pop("CLEARTRACE_OPA_URL", None)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
