"""Safe arithmetic for simple natural-language math requests."""

from __future__ import annotations

import ast
import math
import operator
import re
import unicodedata


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_MAGNITUDE = 1e100


def _evaluate(node: ast.AST, depth: int = 0) -> int | float:
    if depth > 24:
        raise ValueError("expressão muito complexa")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = node.value
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        value = _UNARY[type(node.op)](_evaluate(node.operand, depth + 1))
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _evaluate(node.left, depth + 1)
        right = _evaluate(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise ValueError("expoente limitado a 12")
        value = _BINARY[type(node.op)](left, right)
    else:
        raise ValueError("operação não permitida")
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or abs(value) > _MAX_MAGNITUDE:
        raise ValueError("resultado fora dos limites permitidos")
    return value


def answer_simple_math(text: str) -> str | None:
    """Calculate simple explicit arithmetic; return None for general questions."""
    normalized = "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(char) != "Mn"
    )
    match = re.match(r"^\s*(?:quanto\s+(?:e|é)|calcule|calcular|resolva|resolve)\s+(.+?)\s*[?!.]*\s*$", normalized)
    if not match:
        return None
    expression = match.group(1)
    expression = re.sub(r"\b(multiplicado|multiplicada)\s+por\b|\bvezes\b", "*", expression)
    expression = re.sub(r"\b(dividido|dividida)\s+por\b", "/", expression)
    expression = re.sub(r"\b(elevado|elevada)\s+a\b", "**", expression)
    expression = re.sub(r"\bmais\b", "+", expression)
    expression = re.sub(r"\bmenos\b", "-", expression)
    expression = re.sub(r"(?<=\d),(?=\d)", ".", expression)
    if not re.fullmatch(r"[\d\s.+*/()%\-]+", expression):
        return None
    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return f"Não consegui calcular essa expressão com segurança: {exc}"
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)
