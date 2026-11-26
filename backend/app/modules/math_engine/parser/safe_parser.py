"""Restricted AST-based mathematical expression parser."""

from __future__ import annotations

import ast
import io
import keyword
import re
import tokenize
from typing import Any

import sympy as sp

from app.core.exceptions import ComputationLimitError, InvalidExpressionError
from app.core.security import (
    MAX_AST_DEPTH,
    MAX_AST_NODES,
    MAX_EXPONENT_ABS,
    validate_expression_bounds,
)

SYMBOL_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,15}$")

ALLOWED_CONSTANTS: dict[str, sp.Basic] = {
    "pi": sp.pi,
    "e": sp.E,
    "E": sp.E,
    "i": sp.I,
    "I": sp.I,
    "oo": sp.oo,
    "inf": sp.oo,
}

# Maps approved function names to (sympy_callable, allowed_arities).
ALLOWED_FUNCTIONS: dict[str, tuple[Any, tuple[int, ...]]] = {
    "sin": (sp.sin, (1,)),
    "cos": (sp.cos, (1,)),
    "tan": (sp.tan, (1,)),
    "cot": (sp.cot, (1,)),
    "sec": (sp.sec, (1,)),
    "csc": (sp.csc, (1,)),
    "asin": (sp.asin, (1,)),
    "acos": (sp.acos, (1,)),
    "atan": (sp.atan, (1,)),
    "sinh": (sp.sinh, (1,)),
    "cosh": (sp.cosh, (1,)),
    "tanh": (sp.tanh, (1,)),
    "exp": (sp.exp, (1,)),
    "log": (sp.log, (1, 2)),
    "ln": (sp.log, (1,)),
    "sqrt": (sp.sqrt, (1,)),
    "abs": (sp.Abs, (1,)),
    "factorial": (sp.factorial, (1,)),
    "floor": (sp.floor, (1,)),
    "ceiling": (sp.ceiling, (1,)),
    "sign": (sp.sign, (1,)),
    "re": (sp.re, (1,)),
    "im": (sp.im, (1,)),
    "conjugate": (sp.conjugate, (1,)),
    "arg": (sp.arg, (1,)),
}

SUPPORTED_ASSUMPTIONS = {"real", "positive", "negative", "integer", "nonnegative", "complex"}


def format_sympy_expr(expr: sp.Basic) -> str:
    """Format a SymPy expression into readable math notation using `^` for powers."""
    return str(expr).replace("**", "^")


def _build_symbol_kwargs(name: str, assumptions: dict[str, str] | None) -> dict[str, bool]:
    if not assumptions or name not in assumptions:
        return {}
    raw = assumptions[name].strip().lower()
    if raw not in SUPPORTED_ASSUMPTIONS:
        raise InvalidExpressionError(
            f"Unsupported assumption '{raw}' for symbol '{name}'.",
            details={"supported_assumptions": sorted(SUPPORTED_ASSUMPTIONS)},
        )
    return {raw: True}


def parse_symbol(name: str, assumptions: dict[str, str] | None = None) -> sp.Symbol:
    """Validate and construct a SymPy Symbol."""
    cleaned = name.strip()
    if not SYMBOL_NAME_RE.match(cleaned):
        raise InvalidExpressionError(
            f"'{name}' isn't a valid symbol name. Start with a letter and use only letters, numbers, or '_'."
        )
    if keyword.iskeyword(cleaned) or cleaned in ALLOWED_CONSTANTS or cleaned in ALLOWED_FUNCTIONS:
        raise InvalidExpressionError(
            f"'{cleaned}' is a reserved constant or function name — please choose another symbol."
        )
    return sp.Symbol(cleaned, **_build_symbol_kwargs(cleaned, assumptions))


def _normalize_implicit_multiplication(expr: str) -> str:
    """Normalize `^` to `**` and insert `*` for safe implicit multiplication (e.g. `2x`, `2(x)`)."""
    prepared = expr.replace("^", "**")
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(prepared).readline))
    except (tokenize.TokenError, IndentationError) as exc:
        raise InvalidExpressionError(f"Malformed mathematical syntax: {exc}") from exc

    meaningful = [
        tok for tok in tokens if tok.type not in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE)
    ]
    parts: list[str] = []
    for idx, tok in enumerate(meaningful):
        if idx > 0:
            prev = meaningful[idx - 1]
            need_mul = False
            if prev.type == tokenize.NUMBER and (tok.type == tokenize.NAME or tok.string == "("):
                need_mul = True
            elif prev.string == ")" and (tok.type in (tokenize.NAME, tokenize.NUMBER) or tok.string == "("):
                need_mul = True
            elif prev.type == tokenize.NAME and tok.string == "(" and prev.string not in ALLOWED_FUNCTIONS:
                need_mul = True

            if need_mul:
                parts.append("*")
        parts.append(tok.string)

    return " ".join(parts)


class _AstCompiler:
    """Walks a restricted Python AST and compiles it directly into SymPy objects."""

    def __init__(self, assumptions: dict[str, str] | None = None) -> None:
        self.assumptions = assumptions
        self.node_count = 0

    def compile(self, tree: ast.Expression) -> sp.Basic:
        return self._visit(tree.body, depth=1)

    def _visit(self, node: ast.AST, depth: int) -> sp.Basic:
        self.node_count += 1
        if depth > MAX_AST_DEPTH:
            raise ComputationLimitError(f"Expression nesting exceeds maximum depth of {MAX_AST_DEPTH}.")
        if self.node_count > MAX_AST_NODES:
            raise ComputationLimitError(f"Expression complexity exceeds maximum of {MAX_AST_NODES} nodes.")

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                raise InvalidExpressionError("Boolean literals are not supported.")
            if isinstance(node.value, int):
                return sp.Integer(node.value)
            if isinstance(node.value, float):
                return sp.Float(str(node.value))
            raise InvalidExpressionError(f"Unsupported literal type: {type(node.value).__name__}.")

        if isinstance(node, ast.Name):
            if node.id in ALLOWED_CONSTANTS:
                return ALLOWED_CONSTANTS[node.id]
            return parse_symbol(node.id, self.assumptions)

        if isinstance(node, ast.UnaryOp):
            operand = self._visit(node.operand, depth + 1)
            if isinstance(node.op, ast.UAdd):
                return operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise InvalidExpressionError(f"Unsupported unary operator: {type(node.op).__name__}.")

        if isinstance(node, ast.BinOp):
            left = self._visit(node.left, depth + 1)
            right = self._visit(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise InvalidExpressionError("Division by zero isn't allowed.")
                return left / right
            if isinstance(node.op, ast.Pow):
                if isinstance(right, sp.Number) and abs(float(right)) > MAX_EXPONENT_ABS:
                    raise ComputationLimitError(
                        f"Exponent magnitude exceeds maximum allowed value of {MAX_EXPONENT_ABS}."
                    )
                return left ** right
            raise InvalidExpressionError(f"Unsupported binary operator: {type(node.op).__name__}.")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.keywords:
                raise InvalidExpressionError("Only direct whitelisted mathematical function calls are allowed.")
            fn_name = node.func.id
            if fn_name not in ALLOWED_FUNCTIONS:
                raise InvalidExpressionError(
                    f"Unknown math function '{fn_name}'. Try functions like sin, cos, exp, log, or sqrt.",
                    details={"function": fn_name},
                )
            fn_obj, allowed_arities = ALLOWED_FUNCTIONS[fn_name]
            if len(node.args) not in allowed_arities:
                raise InvalidExpressionError(
                    f"Function '{fn_name}' expects {allowed_arities} argument(s), got {len(node.args)}."
                )
            compiled_args = [self._visit(arg, depth + 1) for arg in node.args]
            return fn_obj(*compiled_args)

        raise InvalidExpressionError(
            f"Unsupported syntax element: {type(node).__name__}.",
            details={"ast_node": type(node).__name__},
        )


def parse_math_expression(expression: str, assumptions: dict[str, str] | None = None) -> sp.Basic:
    """Safely parse a single mathematical expression into a SymPy expression."""
    cleaned = validate_expression_bounds(expression)
    if "=" in cleaned:
        raise InvalidExpressionError(
            "Remove '=' here — enter an expression only (for example 'x^2 - 4' instead of 'y = x^2 - 4')."
        )

    normalized = _normalize_implicit_multiplication(cleaned)
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise InvalidExpressionError(
            "Check your expression syntax — make sure parentheses match and use '*' for multiplication (for example 'w*x')."
        ) from exc

    return _AstCompiler(assumptions=assumptions).compile(tree)


def parse_math_input(expression: str, assumptions: dict[str, str] | None = None) -> sp.Basic | sp.Eq:
    """Safely parse either a mathematical expression or an equation `lhs = rhs`."""
    cleaned = validate_expression_bounds(expression)
    if any(op in cleaned for op in ("==", "!=", "<=", ">=", "<", ">")):
        raise InvalidExpressionError("Only single '=' equations or algebraic expressions are supported.")

    if "=" in cleaned:
        parts = cleaned.split("=")
        if len(parts) != 2:
            raise InvalidExpressionError("Equations must contain exactly one '=' sign.")
        lhs = parse_math_expression(parts[0], assumptions=assumptions)
        rhs = parse_math_expression(parts[1], assumptions=assumptions)
        return sp.Eq(lhs, rhs)

    return parse_math_expression(cleaned, assumptions=assumptions)
