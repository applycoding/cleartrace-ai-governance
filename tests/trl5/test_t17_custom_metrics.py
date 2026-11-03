from __future__ import annotations

import pytest
from cleartrace_engine.cel_evaluator import CELEvaluationError, evaluate_cel
from cleartrace_risk.plugin_sandbox import run_sandboxed_plugin

CEL_FIXTURES: list[tuple[str, dict[str, object], bool]] = [
    ("value > warn", {"value": 0.9, "warn": 0.5}, True),
    ("value <= breach", {"value": 0.01, "breach": 0.05}, True),
    ("observations.rate * 100.0 > 5.0", {"observations": {"rate": 0.08}}, True),
    ("observations.rate * 100.0 > 5.0", {"observations": {"rate": 0.01}}, False),
    ("a >= b && b >= c", {"a": 3, "b": 2, "c": 1}, True),
    ("a >= b && b >= c", {"a": 1, "b": 2, "c": 3}, False),
]

PLUGIN_FIXTURES: list[tuple[str, dict[str, object], float]] = [
    (
        "def evaluate(data):\n    return float(data['x']) + float(data['y'])\n",
        {"x": 1, "y": 2},
        3.0,
    ),
    (
        "def evaluate(data):\n    return len(data['items'])\n",
        {"items": [1, 2, 3, 4]},
        4.0,
    ),
    (
        (
            "def evaluate(data):\n"
            "    total = 0.0\n"
            "    for item in data['values']:\n"
            "        total += item\n"
            "    return total\n"
        ),
        {"values": [0.5, 0.25, 0.25]},
        1.0,
    ),
]

HOSTILE_PLUGINS = [
    "def evaluate(data):\n    import socket\n    return 1\n",
    "def evaluate(data):\n    return open('/etc/passwd').read()\n",
    "def evaluate(data):\n    while True:\n        pass\n",
]


@pytest.mark.trl5
@pytest.mark.parametrize(("expr", "ctx", "expected"), CEL_FIXTURES)
def test_t17_cel_custom_metrics(expr: str, ctx: dict[str, object], expected: bool) -> None:
    assert evaluate_cel(expr, ctx) is expected


@pytest.mark.trl5
def test_t17_cel_rejects_unknown_identifier() -> None:
    with pytest.raises(CELEvaluationError):
        evaluate_cel("missing > 1", {})


@pytest.mark.trl5
@pytest.mark.parametrize(("source", "payload", "expected"), PLUGIN_FIXTURES)
def test_t17_sandbox_plugins(source: str, payload: dict[str, object], expected: float) -> None:
    result = run_sandboxed_plugin(source, payload)
    assert result.error is None
    assert result.escaped is False
    assert result.value == expected


@pytest.mark.trl5
@pytest.mark.parametrize("hostile", HOSTILE_PLUGINS)
def test_t17_hostile_plugins_blocked(hostile: str) -> None:
    result = run_sandboxed_plugin(hostile, {"x": 1})
    assert result.escaped or result.error is not None
    assert result.value is None


@pytest.mark.trl5
def test_t17_fixture_count() -> None:
    total = len(CEL_FIXTURES) + len(PLUGIN_FIXTURES) + len(HOSTILE_PLUGINS)
    assert total == 12
