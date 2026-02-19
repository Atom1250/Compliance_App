"""Sandboxed expression evaluation for regulatory compiler context."""

from __future__ import annotations

import ast
from typing import Any

_ALLOWED_COMPARE_OPS = (ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE)
_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)


def _safe_eval(node: ast.AST, *, context: dict[str, Any], allowed_symbols: set[str]) -> Any:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, context=context, allowed_symbols=allowed_symbols)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in allowed_symbols:
            raise ValueError(f"Unknown symbol: {node.id}")
        if node.id not in context:
            raise ValueError(f"Missing symbol in context: {node.id}")
        return context[node.id]

    if isinstance(node, ast.Attribute):
        value = _safe_eval(node.value, context=context, allowed_symbols=allowed_symbols)
        if isinstance(value, dict):
            if node.attr not in value:
                raise ValueError(f"Unknown attribute: {node.attr}")
            return value[node.attr]
        raise ValueError(f"Unsupported attribute base: {type(value).__name__}")

    if isinstance(node, ast.BoolOp) and isinstance(node.op, _ALLOWED_BOOL_OPS):
        values = [_safe_eval(v, context=context, allowed_symbols=allowed_symbols) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, context=context, allowed_symbols=allowed_symbols)

    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BIN_OPS):
        left = _safe_eval(node.left, context=context, allowed_symbols=allowed_symbols)
        right = _safe_eval(node.right, context=context, allowed_symbols=allowed_symbols)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right

    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, context=context, allowed_symbols=allowed_symbols)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = _safe_eval(comparator, context=context, allowed_symbols=allowed_symbols)
            if not isinstance(op, _ALLOWED_COMPARE_OPS):
                raise ValueError("Unsupported comparison operator")
            if isinstance(op, ast.Eq) and not (left == right):
                return False
            if isinstance(op, ast.NotEq) and not (left != right):
                return False
            if isinstance(op, ast.Gt) and not (left > right):
                return False
            if isinstance(op, ast.GtE) and not (left >= right):
                return False
            if isinstance(op, ast.Lt) and not (left < right):
                return False
            if isinstance(op, ast.LtE) and not (left <= right):
                return False
            left = right
        return True

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_expression(
    expression: str,
    *,
    context: dict[str, Any],
    allowed_symbols: set[str],
) -> bool:
    """Evaluate expression using strict symbol whitelist and structured context."""
    parsed = ast.parse(expression, mode="eval")
    return bool(_safe_eval(parsed, context=context, allowed_symbols=allowed_symbols))

