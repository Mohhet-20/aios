"""A deliberately small, safe expression evaluator for CONDITION/DECISION
routing, LOOP conditions, and PYTHON_EXECUTION nodes. Workflow authors
write ordinary-looking Python expressions (`status == "approved" and
retries < 3`), but nothing here calls `eval()` on untrusted code — the
AST is walked and only a small allow-listed set of node types and
functions is permitted. This buys real expressiveness without opening a
sandbox-escape hole; anything genuinely more complex belongs in a
PYTHON_EXECUTION node backed by a properly sandboxed worker (a future
seam noted in the platform's self-review), not this evaluator.
"""
from __future__ import annotations

import ast
import operator
from typing import Any

from workflow_platform.core.exceptions import ValidationError

_ALLOWED_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.Pow: operator.pow,
}
_ALLOWED_CMPOPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
}
_ALLOWED_UNARYOPS = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}

_ALLOWED_FUNCTIONS: dict[str, Any] = {
    "len": len, "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
    "str": str, "int": int, "float": float, "bool": bool, "sorted": sorted,
}


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self, variables: dict[str, Any]):
        self.variables = variables

    def visit(self, node: ast.AST) -> Any:  # noqa: C901
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self.variables:
                return self.variables[node.id]
            if node.id in _ALLOWED_FUNCTIONS:
                return _ALLOWED_FUNCTIONS[node.id]
            raise ValidationError(f"unknown variable '{node.id}' in expression")
        if isinstance(node, ast.BoolOp):
            values = [self.visit(v) for v in node.values]
            if isinstance(node.op, ast.And):
                result = True
                for v in values:
                    result = result and v
                return result
            result = False
            for v in values:
                result = result or v
            return result
        if isinstance(node, ast.BinOp):
            op_fn = _ALLOWED_BINOPS.get(type(node.op))
            if op_fn is None:
                raise ValidationError(f"operator {type(node.op).__name__} is not allowed in expressions")
            return op_fn(self.visit(node.left), self.visit(node.right))
        if isinstance(node, ast.UnaryOp):
            op_fn = _ALLOWED_UNARYOPS.get(type(node.op))
            if op_fn is None:
                raise ValidationError(f"unary operator {type(node.op).__name__} is not allowed in expressions")
            return op_fn(self.visit(node.operand))
        if isinstance(node, ast.Compare):
            left = self.visit(node.left)
            result = True
            for op_node, comparator in zip(node.ops, node.comparators):
                op_fn = _ALLOWED_CMPOPS.get(type(op_node))
                if op_fn is None:
                    raise ValidationError(f"comparison {type(op_node).__name__} is not allowed in expressions")
                right = self.visit(comparator)
                result = result and op_fn(left, right)
                left = right
            return result
        if isinstance(node, ast.List):
            return [self.visit(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.visit(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            value = self.visit(node.value)
            key = self.visit(node.slice)
            return value[key]
        if isinstance(node, ast.Attribute):
            raise ValidationError("attribute access is not allowed in expressions")
        if isinstance(node, ast.Call):
            func = self.visit(node.func)
            if func not in _ALLOWED_FUNCTIONS.values():
                raise ValidationError("only allow-listed functions may be called in expressions")
            args = [self.visit(a) for a in node.args]
            return func(*args)
        if isinstance(node, ast.IfExp):
            return self.visit(node.body) if self.visit(node.test) else self.visit(node.orelse)
        raise ValidationError(f"expression node type {type(node).__name__} is not allowed")


def evaluate_expression(expression: str, variables: dict[str, Any]) -> Any:
    """Safely evaluates a single Python-like expression against a flat
    variable namespace. Raises `ValidationError` for anything outside the
    allow-listed grammar — including any attempt at attribute access,
    imports, or comprehensions, none of which are supported."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValidationError(f"invalid expression syntax: {exc}") from exc
    return _SafeEvaluator(variables).visit(tree)
