"""Symbolic algebra operations."""

from __future__ import annotations

from typing import Any

import sympy as sp

from app.core.exceptions import DomainError, InvalidExpressionError
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)


def simplify_expr(
    expression: str,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Simplify a mathematical expression."""
    parsed = parse_math_expression(expression, assumptions=assumptions)
    simplified = sp.simplify(parsed)
    return {
        "result": format_sympy_expr(simplified),
        "latex": sp.latex(simplified),
        "details": {"method": "symbolic_simplification"},
    }


def expand_expr(
    expression: str,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Expand a mathematical expression."""
    parsed = parse_math_expression(expression, assumptions=assumptions)
    expanded = sp.expand(parsed)
    return {
        "result": format_sympy_expr(expanded),
        "latex": sp.latex(expanded),
        "details": {"method": "symbolic_expansion"},
    }


def factor_expr(
    expression: str,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Factor a mathematical expression."""
    parsed = parse_math_expression(expression, assumptions=assumptions)
    factored = sp.factor(parsed)
    return {
        "result": format_sympy_expr(factored),
        "latex": sp.latex(factored),
        "details": {"method": "symbolic_factorization"},
    }


def solve_equation(
    expression: str,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Solve an equation `lhs = rhs` or expression `expr = 0` for the target variable."""
    parsed = parse_math_input(expression, assumptions=assumptions)
    equation = parsed if isinstance(parsed, sp.Eq) else sp.Eq(parsed, 0)

    if variable:
        target = parse_symbol(variable, assumptions=assumptions)
    else:
        free_syms = sorted(equation.free_symbols, key=lambda sym: sym.name)
        if not free_syms:
            raise InvalidExpressionError("No variable found to solve for.")
        if len(free_syms) > 1:
            raise InvalidExpressionError(
                "Multiple variables found; please specify 'variable' explicitly.",
                details={"variables": [sym.name for sym in free_syms]},
            )
        target = free_syms[0]

    try:
        solutions = sp.solve(equation, target)
    except NotImplementedError as exc:
        raise DomainError("Equation could not be solved symbolically.") from exc

    if isinstance(solutions, dict):
        sol_list = [solutions[target]] if target in solutions else []
    elif isinstance(solutions, list):
        sol_list = solutions
    else:
        sol_list = [solutions]

    if not sol_list:
        return {
            "result": "No solution",
            "latex": r"\emptyset",
            "details": {
                "method": "symbolic_solve",
                "variable": target.name,
                "solutions": [],
            },
        }

    formatted_items = [format_sympy_expr(sol) for sol in sol_list]
    latex_items = [sp.latex(sol) for sol in sol_list]
    return {
        "result": f"{target.name} = {', '.join(formatted_items)}",
        "latex": f"{sp.latex(target)} = {', '.join(latex_items)}",
        "details": {
            "method": "symbolic_solve",
            "variable": target.name,
            "solutions": formatted_items,
            "solutions_latex": latex_items,
        },
    }
