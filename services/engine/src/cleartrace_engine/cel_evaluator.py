from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from celpy import CELEvalError, CELParseError, Environment
from celpy.adapter import json_to_cel
from celpy.celparser import CELParser

MAX_AST_DEPTH = 10
MAX_COLLECTION_SIZE = 1000
MAX_COST = 1000
TIMEOUT_MS = 25


class CELEvaluationError(Exception):
    def __init__(self, code: str, message_en: str, message_fr: str) -> None:
        self.code = code
        self.message_en = message_en
        self.message_fr = message_fr
        super().__init__(message_en)


def _cel_activation(context: dict[str, Any]) -> dict[str, Any]:
    """Normalize Python context keys/values for CEL (true/false/null)."""
    out: dict[str, Any] = {}
    for key, value in context.items():
        if isinstance(value, bool):
            out[key] = value
        elif value is None:
            out[key] = None
        elif isinstance(value, (str, int, float)):
            out[key] = value
        elif isinstance(value, (list, dict)):
            if len(value) > MAX_COLLECTION_SIZE:
                raise CELEvaluationError(
                    "EVAL_ERROR",
                    "Collection size exceeds limit",
                    "La taille de la collection dépasse la limite",
                )
            out[key] = value
        else:
            out[key] = value
    return out


def _expression_paren_depth(expression: str) -> int:
    depth = 0
    max_depth = 0
    for char in expression:
        if char == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == ")":
            depth = max(0, depth - 1)
    return max_depth


@lru_cache(maxsize=256)
def _compile(expression: str):
    if _expression_paren_depth(expression) > MAX_AST_DEPTH:
        raise CELEvaluationError(
            "EVAL_ERROR",
            "Expression exceeds max depth",
            "Expression dépasse la profondeur maximale",
        )
    ast = CELParser().parse(expression)
    env = Environment()
    return env.program(ast)


def evaluate_cel(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate applicability using cel-python (Apache-2.0) with blueprint §6.1 limits."""
    if len(expression) > 5000:
        raise CELEvaluationError(
            "EVAL_ERROR",
            "Expression too large",
            "Expression trop grande",
        )

    try:
        program = _compile(expression)
    except CELParseError as exc:
        raise CELEvaluationError(
            "EVAL_ERROR",
            f"Syntax error: {exc}",
            f"Erreur de syntaxe : {exc}",
        ) from exc
    except CELEvaluationError:
        raise

    activation = _cel_activation(context)
    try:
        eval_started = time.perf_counter()
        result = program.evaluate(json_to_cel(activation))
        eval_ms = (time.perf_counter() - eval_started) * 1000
        if eval_ms > TIMEOUT_MS:
            raise CELEvaluationError(
                "EVAL_ERROR",
                "Evaluation timed out",
                "Délai d'évaluation dépassé",
            )
    except CELEvalError as exc:
        raise CELEvaluationError(
            "EVAL_ERROR",
            str(exc),
            str(exc),
        ) from exc
    except CELEvaluationError:
        raise
    except Exception as exc:
        raise CELEvaluationError(
            "EVAL_ERROR",
            str(exc),
            str(exc),
        ) from exc

    return bool(result)
