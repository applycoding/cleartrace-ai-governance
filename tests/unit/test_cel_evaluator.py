from __future__ import annotations

import pytest
from cleartrace_engine.cel_evaluator import CELEvaluationError, evaluate_cel


def test_simple_applicability() -> None:
    assert evaluate_cel("planned_production_use == True", {"planned_production_use": True}) is True


def test_unknown_identifier_is_eval_error() -> None:
    with pytest.raises(CELEvaluationError) as exc:
        evaluate_cel("missing_field == True", {})
    assert exc.value.code == "EVAL_ERROR"


def test_collection_size_limit() -> None:
    big_list = list(range(1001))
    with pytest.raises(CELEvaluationError):
        evaluate_cel("values == True", {"values": big_list})
