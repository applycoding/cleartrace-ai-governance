"""Tier-2 sandboxed plug-in runner: no network, no file access, time limit.

Plug-ins are interpreted from their AST by an allow-listed evaluator in a
separate process; nothing is passed to exec or eval.
"""

from __future__ import annotations

import ast
import multiprocessing as mp
import operator
from dataclasses import dataclass
from typing import Any


class SandboxViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxResult:
    value: float | bool | None
    error: str | None = None
    escaped: bool = False


_SAFE_BUILTINS: dict[str, Any] = {
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
    "round": round,
    "sorted": sorted,
    "list": list,
}

MAX_STEPS = 200_000
MAX_SEQUENCE = 10_000
MAX_EXPONENT = 64

_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_CMP_OPS: dict[type[ast.cmpop], Any] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


class _Return(Exception):  # noqa: N818 - control flow signal, not an error
    def __init__(self, value: Any) -> None:
        self.value = value


class _Break(Exception):  # noqa: N818
    pass


class _Continue(Exception):  # noqa: N818
    pass


class _Interpreter:
    """Evaluate a small, attribute-free subset of Python without exec or eval.

    Plug-ins may define ``evaluate(data)`` using assignments, loops, ``if``,
    arithmetic, comparisons, subscripts and a fixed set of builtins. Attribute
    access, imports, lambdas, comprehensions, classes and any call to a name
    outside the allow-list are rejected, so object internals are unreachable.
    """

    def __init__(self) -> None:
        self._steps = 0

    def _tick(self) -> None:
        self._steps += 1
        if self._steps > MAX_STEPS:
            raise TimeoutError("time limit")

    def load(self, source: str) -> ast.FunctionDef:
        tree = ast.parse(source, mode="exec")
        evaluate: ast.FunctionDef | None = None
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue
            if isinstance(node, ast.FunctionDef) and node.name == "evaluate":
                evaluate = node
                continue
            if isinstance(node, ast.Import | ast.ImportFrom):
                raise SandboxViolation("Imports are not allowed in plug-ins")
            raise SandboxViolation(f"Top-level statement not allowed: {type(node).__name__}")
        if evaluate is None:
            raise SandboxViolation("Missing evaluate(data) function")
        args = evaluate.args
        if (
            len(args.args) != 1
            or args.vararg
            or args.kwarg
            or args.kwonlyargs
            or args.posonlyargs
            or evaluate.decorator_list
        ):
            raise SandboxViolation("evaluate must take exactly one argument: data")
        return evaluate

    def call(self, func: ast.FunctionDef, payload: dict[str, Any]) -> Any:
        scope: dict[str, Any] = {func.args.args[0].arg: payload}
        try:
            self._block(func.body, scope)
        except _Return as ret:
            return ret.value
        return None

    def _block(self, body: list[ast.stmt], scope: dict[str, Any]) -> None:
        for stmt in body:
            self._stmt(stmt, scope)

    def _assign(self, target: ast.expr, value: Any, scope: dict[str, Any]) -> None:
        if isinstance(target, ast.Name):
            scope[target.id] = value
            return
        if isinstance(target, ast.Tuple | ast.List):
            values = list(value)
            if len(values) != len(target.elts):
                raise ValueError("unpacking length mismatch")
            for elt, item in zip(target.elts, values, strict=True):
                self._assign(elt, item, scope)
            return
        raise SandboxViolation(f"Assignment target not allowed: {type(target).__name__}")

    def _stmt(self, node: ast.stmt, scope: dict[str, Any]) -> None:
        self._tick()
        if isinstance(node, ast.Return):
            raise _Return(self._expr(node.value, scope) if node.value else None)
        if isinstance(node, ast.Assign):
            value = self._expr(node.value, scope)
            for target in node.targets:
                self._assign(target, value, scope)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            current = self._name(node.target.id, scope)
            scope[node.target.id] = self._binop(node.op, current, self._expr(node.value, scope))
        elif isinstance(node, ast.If):
            branch = node.body if self._expr(node.test, scope) else node.orelse
            self._block(branch, scope)
        elif isinstance(node, ast.For) and not node.orelse:
            for item in self._expr(node.iter, scope):
                self._tick()
                self._assign(node.target, item, scope)
                try:
                    self._block(node.body, scope)
                except _Break:
                    break
                except _Continue:
                    continue
        elif isinstance(node, ast.While) and not node.orelse:
            while self._expr(node.test, scope):
                self._tick()
                try:
                    self._block(node.body, scope)
                except _Break:
                    break
                except _Continue:
                    continue
        elif isinstance(node, ast.Break):
            raise _Break
        elif isinstance(node, ast.Continue):
            raise _Continue
        elif isinstance(node, ast.Pass):
            return
        elif isinstance(node, ast.Expr):
            self._expr(node.value, scope)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            raise SandboxViolation("Imports are not allowed in plug-ins")
        else:
            raise SandboxViolation(f"Statement not allowed: {type(node).__name__}")

    def _name(self, name: str, scope: dict[str, Any]) -> Any:
        if name in scope:
            return scope[name]
        if name in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[name]
        raise SandboxViolation(f"Name not allowed: {name}")

    def _binop(self, op: ast.operator, left: Any, right: Any) -> Any:
        fn = _BIN_OPS.get(type(op))
        if fn is None:
            raise SandboxViolation(f"Operator not allowed: {type(op).__name__}")
        if isinstance(op, ast.Pow) and (
            not isinstance(right, int | float) or abs(right) > MAX_EXPONENT
        ):
            raise SandboxViolation("Exponent too large")
        if isinstance(op, ast.Mult) and (
            (
                isinstance(left, str | list | tuple)
                and isinstance(right, int)
                and right > MAX_SEQUENCE
            )
            or (
                isinstance(right, str | list | tuple)
                and isinstance(left, int)
                and left > MAX_SEQUENCE
            )
        ):
            raise SandboxViolation("Sequence too large")
        return fn(left, right)

    def _expr(self, node: ast.expr, scope: dict[str, Any]) -> Any:
        self._tick()
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool | int | float | str) or node.value is None:
                return node.value
            raise SandboxViolation("Constant type not allowed")
        if isinstance(node, ast.Name):
            return self._name(node.id, scope)
        if isinstance(node, ast.BinOp):
            return self._binop(node.op, self._expr(node.left, scope), self._expr(node.right, scope))
        if isinstance(node, ast.UnaryOp):
            operand = self._expr(node.operand, scope)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.Not):
                return not operand
            raise SandboxViolation("Unary operator not allowed")
        if isinstance(node, ast.BoolOp):
            result: Any = isinstance(node.op, ast.And)
            for value in node.values:
                result = self._expr(value, scope)
                if isinstance(node.op, ast.And) and not result:
                    return result
                if isinstance(node.op, ast.Or) and result:
                    return result
            return result
        if isinstance(node, ast.Compare):
            left = self._expr(node.left, scope)
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                right = self._expr(comparator, scope)
                fn = _CMP_OPS.get(type(op))
                if fn is None:
                    raise SandboxViolation(f"Comparison not allowed: {type(op).__name__}")
                if not fn(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            branch = node.body if self._expr(node.test, scope) else node.orelse
            return self._expr(branch, scope)
        if isinstance(node, ast.Subscript):
            container = self._expr(node.value, scope)
            if not isinstance(container, dict | list | tuple | str):
                raise SandboxViolation("Subscript target not allowed")
            if isinstance(node.slice, ast.Slice):
                parts = [
                    self._expr(part, scope) if part is not None else None
                    for part in (node.slice.lower, node.slice.upper, node.slice.step)
                ]
                return container[slice(*parts)]
            return container[self._expr(node.slice, scope)]
        if isinstance(node, ast.List | ast.Tuple):
            items = [self._expr(elt, scope) for elt in node.elts]
            return items if isinstance(node, ast.List) else tuple(items)
        if isinstance(node, ast.Dict):
            out: dict[Any, Any] = {}
            for key, value in zip(node.keys, node.values, strict=True):
                if key is None:
                    raise SandboxViolation("Dict unpacking not allowed")
                out[self._expr(key, scope)] = self._expr(value, scope)
            return out
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_BUILTINS:
                name = node.func.id if isinstance(node.func, ast.Name) else type(node.func).__name__
                raise SandboxViolation(f"Call blocked: {name}")
            if node.keywords:
                raise SandboxViolation("Keyword arguments not allowed")
            call_args = [self._expr(arg, scope) for arg in node.args]
            if node.func.id == "range" and len(range(*call_args)) > MAX_SEQUENCE * 10:
                raise SandboxViolation("Range too large")
            return _SAFE_BUILTINS[node.func.id](*call_args)
        raise SandboxViolation(f"Expression not allowed: {type(node).__name__}")


def _run_plugin_worker(
    source: str,
    payload: dict[str, Any],
    queue: mp.Queue[SandboxResult],
) -> None:
    try:
        interpreter = _Interpreter()
        evaluate = interpreter.load(source)
        result = interpreter.call(evaluate, payload)
        if not isinstance(result, bool | int | float):
            queue.put(
                SandboxResult(value=None, error="evaluate(data) must return a number or bool")
            )
            return
        queue.put(SandboxResult(value=result))
    except SandboxViolation as exc:
        queue.put(SandboxResult(value=None, error=str(exc), escaped=True))
    except TimeoutError as exc:
        queue.put(SandboxResult(value=None, error=str(exc), escaped=True))
    except Exception as exc:  # noqa: BLE001
        queue.put(SandboxResult(value=None, error=str(exc)))


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
