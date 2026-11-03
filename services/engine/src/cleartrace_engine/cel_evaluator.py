from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from typing import Any

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


@dataclass
class _Limits:
    depth: int = 0
    cost: int = 0


def _depth(node: ast.AST, current: int = 0) -> int:
    child_depth = current
    for child in ast.iter_child_nodes(node):
        child_depth = max(child_depth, _depth(child, current + 1))
    return child_depth


def _check_collection(value: Any, limits: _Limits) -> None:
    if isinstance(value, (list, tuple, set, dict)):
        size = len(value)
        limits.cost += size
        if size > MAX_COLLECTION_SIZE:
            raise CELEvaluationError(
                "EVAL_ERROR",
                "Collection size exceeds limit",
                "La taille de la collection dépasse la limite",
            )


_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.UnaryOp,
    ast.Not,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
)


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self, context: dict[str, Any], limits: _Limits) -> None:
        self.context = context
        self.limits = limits

    def visit(self, node: ast.AST) -> Any:
        self.limits.cost += 1
        if self.limits.cost > MAX_COST:
            raise CELEvaluationError(
                "EVAL_ERROR",
                "CEL cost budget exceeded",
                "Budget de coût CEL dépassé",
            )
        if not isinstance(node, _ALLOWED_NODES):
            raise CELEvaluationError(
                "EVAL_ERROR",
                f"Unsupported expression node: {type(node).__name__}",
                f"Nœud d'expression non pris en charge : {type(node).__name__}",
            )
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id not in self.context:
            raise CELEvaluationError(
                "EVAL_ERROR",
                f"Unknown identifier: {node.id}",
                f"Identifiant inconnu : {node.id}",
            )
        value = self.context[node.id]
        _check_collection(value, self.limits)
        return value

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        base = self.visit(node.value)
        if not isinstance(base, dict):
            raise CELEvaluationError(
                "EVAL_ERROR",
                "Attribute access only supported on maps",
                "L'accès aux attributs n'est pris en charge que sur les cartes",
            )
        if node.attr not in base:
            raise CELEvaluationError(
                "EVAL_ERROR",
                f"Missing field: {node.attr}",
                f"Champ manquant : {node.attr}",
            )
        value = base[node.attr]
        _check_collection(value, self.limits)
        return value

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        base = self.visit(node.value)
        key = self.visit(node.slice)
        if isinstance(base, dict):
            if key not in base:
                raise CELEvaluationError(
                    "EVAL_ERROR",
                    f"Missing key: {key}",
                    f"Clé manquante : {key}",
                )
            return base[key]
        if isinstance(base, (list, tuple)) and isinstance(key, int):
            return base[key]
        raise CELEvaluationError(
            "EVAL_ERROR",
            "Invalid subscript",
            "Indice non valide",
        )

    def visit_List(self, node: ast.List) -> list[Any]:
        if len(node.elts) > MAX_COLLECTION_SIZE:
            raise CELEvaluationError(
                "EVAL_ERROR",
                "List literal too large",
                "Littéral de liste trop grand",
            )
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            result = True
            for value in node.values:
                result = result and bool(self.visit(value))
                if not result:
                    return False
            return result
        result = False
        for value in node.values:
            result = result or bool(self.visit(value))
            if result:
                return True
        return result

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if isinstance(node.op, ast.Not):
            return not bool(self.visit(node.operand))
        raise CELEvaluationError(
            "EVAL_ERROR",
            "Unary operator not allowed",
            "Opérateur unaire interdit",
        )

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = self.visit(comparator)
            if isinstance(op, ast.Eq) and left != right:
                return False
            if isinstance(op, ast.NotEq) and left == right:
                return False
            if isinstance(op, ast.Lt) and not (left < right):
                return False
            if isinstance(op, ast.LtE) and not (left <= right):
                return False
            if isinstance(op, ast.Gt) and not (left > right):
                return False
            if isinstance(op, ast.GtE) and not (left >= right):
                return False
            if isinstance(op, ast.In) and left not in right:
                return False
            if isinstance(op, ast.NotIn) and left in right:
                return False
            left = right
        return True


def evaluate_cel(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a bounded applicability predicate (CEL-like subset)."""
    started = time.perf_counter()
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CELEvaluationError(
            "EVAL_ERROR",
            f"Syntax error: {exc.msg}",
            f"Erreur de syntaxe : {exc.msg}",
        ) from exc
    if _depth(tree) > MAX_AST_DEPTH:
        raise CELEvaluationError(
            "EVAL_ERROR",
            "AST depth exceeds limit",
            "La profondeur de l'AST dépasse la limite",
        )
    limits = _Limits()
    evaluator = _SafeEvaluator(context, limits)
    result = evaluator.visit(tree)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if elapsed_ms > TIMEOUT_MS:
        raise CELEvaluationError(
            "EVAL_ERROR",
            "Evaluation timed out",
            "Délai d'évaluation dépassé",
        )
    return bool(result)
