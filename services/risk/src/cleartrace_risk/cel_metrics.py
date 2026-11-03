"""Tier-1 custom metrics via a constrained CEL-like expression language."""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from typing import Any

_ALLOWED_BINOPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_CMPOPS: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_ALLOWED_UNARY: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class CelEvaluationError(ValueError):
    pass


def evaluate_cel(expression: str, context: dict[str, Any]) -> Any:
    """Evaluate a safe subset of CEL over the provided context mapping."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CelEvaluationError(str(exc)) from exc
    return _eval_node(tree.body, context)


def _eval_node(node: ast.AST, context: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise CelEvaluationError("Only numeric and boolean literals are allowed")
    if isinstance(node, ast.Name):
        if node.id not in context:
            raise CelEvaluationError(f"Unknown identifier: {node.id}")
        return context[node.id]
    if isinstance(node, ast.Subscript):
        base = _eval_node(node.value, context)
        if isinstance(node.slice, ast.Constant):
            key: Any = node.slice.value
        else:
            key = _eval_node(node.slice, context)
        try:
            return base[key]
        except (TypeError, KeyError) as exc:
            raise CelEvaluationError("Invalid subscript") from exc
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise CelEvaluationError("Operator not allowed")
        op = _ALLOWED_BINOPS[op_type]
        return op(_eval_node(node.left, context), _eval_node(node.right, context))
    if isinstance(node, ast.UnaryOp):
        unary_type = type(node.op)
        if unary_type not in _ALLOWED_UNARY:
            raise CelEvaluationError("Unary operator not allowed")
        unary_op = _ALLOWED_UNARY[unary_type]
        return unary_op(_eval_node(node.operand, context))
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        for cmp_op, comparator in zip(node.ops, node.comparators, strict=True):
            cmp_type = type(cmp_op)
            if cmp_type not in _ALLOWED_CMPOPS:
                raise CelEvaluationError("Comparison not allowed")
            fn = _ALLOWED_CMPOPS[cmp_type]
            right = _eval_node(comparator, context)
            if not fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval_node(value, context) for value in node.values)
        if isinstance(node.op, ast.Or):
            return any(_eval_node(value, context) for value in node.values)
    raise CelEvaluationError(f"Unsupported expression node: {type(node).__name__}")
