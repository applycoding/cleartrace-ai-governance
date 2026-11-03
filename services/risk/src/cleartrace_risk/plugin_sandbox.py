"""Tier-2 sandboxed plug-in runner: no network, no file access, time limit."""

from __future__ import annotations

import ast
import multiprocessing as mp
import signal
from dataclasses import dataclass
from typing import Any


class SandboxViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxResult:
    value: float | bool | None
    error: str | None = None
    escaped: bool = False


def _safe_builtins() -> dict[str, Any]:
    return {
        "__build_class__": __build_class__,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "float": float,
        "int": int,
        "bool": bool,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
    }


def _validate_ast(source: str) -> None:
    tree = ast.parse(source, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            raise SandboxViolation("Imports are not allowed in plug-ins")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id
            in {
                "open",
                "exec",
                "eval",
                "__import__",
            }
        ):
            raise SandboxViolation(f"Call blocked: {node.func.id}")


def _run_plugin_worker(
    source: str,
    payload: dict[str, Any],
    queue: mp.Queue[SandboxResult],
) -> None:
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("time limit")))
    signal.alarm(2)
    try:
        _validate_ast(source)
        namespace: dict[str, Any] = {"__builtins__": _safe_builtins(), "data": payload}
        exec(compile(source, "<plugin>", "exec"), namespace, namespace)  # noqa: S102
        if "evaluate" not in namespace or not callable(namespace["evaluate"]):
            queue.put(SandboxResult(value=None, error="Missing evaluate(data) function"))
            return
        result = namespace["evaluate"](payload)
        queue.put(SandboxResult(value=result))
    except SandboxViolation as exc:
        queue.put(SandboxResult(value=None, error=str(exc), escaped=True))
    except TimeoutError as exc:
        queue.put(SandboxResult(value=None, error=str(exc), escaped=True))
    except Exception as exc:  # noqa: BLE001
        queue.put(SandboxResult(value=None, error=str(exc)))
    finally:
        signal.alarm(0)


def run_sandboxed_plugin(
    source: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: float = 2.0,
) -> SandboxResult:
    ctx = mp.get_context("spawn")
    queue: mp.Queue[SandboxResult] = ctx.Queue()
    process = ctx.Process(target=_run_plugin_worker, args=(source, payload, queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(0.5)
        return SandboxResult(value=None, error="time limit exceeded", escaped=True)
    if queue.empty():
        return SandboxResult(value=None, error="plug-in produced no result")
    result: SandboxResult = queue.get()
    return result


def probe_escape(source: str) -> SandboxResult:
    """Run a hostile plug-in and report whether it escaped the sandbox."""
    return run_sandboxed_plugin(source, {"probe": True}, timeout_seconds=2.0)
