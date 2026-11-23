"""Symbolic calculus operations."""

from __future__ import annotations

from typing import Any

import sympy as sp

from app.core.exceptions import DomainError, InvalidExpressionError
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_symbol,
)


def _resolve_variable(expr: sp.Basic, variable: str | None, assumptions: dict[str, str] | None) -> sp.Symbol:
    if variable:
        return parse_symbol(variable, assumptions=assumptions)
    free_syms = sorted(expr.free_symbols, key=lambda sym: sym.name)
    if not free_syms:
        return sp.Symbol("x")
    if len(free_syms) > 1:
        raise InvalidExpressionError(
            "Multiple variables found; please specify 'variable' explicitly.",
            details={"variables": [sym.name for sym in free_syms]},
        )
    return free_syms[0]


def differentiate_expr(
    expression: str,
    variable: str | None = None,
    order: int = 1,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute the symbolic derivative of an expression."""
    if not isinstance(order, int) or order < 1 or order > 10:
        raise InvalidExpressionError("Derivative 'order' must be an integer between 1 and 10.")

    parsed = parse_math_expression(expression, assumptions=assumptions)
    var_sym = _resolve_variable(parsed, variable, assumptions)
    derivative = sp.diff(parsed, var_sym, order)
    return {
        "result": format_sympy_expr(derivative),
        "latex": sp.latex(derivative),
        "details": {
            "method": "symbolic_differentiation",
            "variable": var_sym.name,
            "order": order,
        },
    }


def integrate_expr(
    expression: str,
    variable: str | None = None,
    lower: str | float | int | None = None,
    upper: str | float | int | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute an indefinite or definite symbolic integral."""
    parsed = parse_math_expression(expression, assumptions=assumptions)
    var_sym = _resolve_variable(parsed, variable, assumptions)

    if (lower is None) != (upper is None):
        raise InvalidExpressionError("Both 'lower' and 'upper' bounds are required for definite integration.")

    if lower is not None and upper is not None:
        lower_expr = parse_math_expression(str(lower), assumptions=assumptions)
        upper_expr = parse_math_expression(str(upper), assumptions=assumptions)
        integral = sp.integrate(parsed, (var_sym, lower_expr, upper_expr))
        if isinstance(integral, sp.Integral):
            raise DomainError("Definite integral could not be evaluated symbolically; try numerical_integrate.")
        return {
            "result": format_sympy_expr(integral),
            "latex": sp.latex(integral),
            "details": {
                "method": "symbolic_definite_integration",
                "variable": var_sym.name,
                "lower": format_sympy_expr(lower_expr),
                "upper": format_sympy_expr(upper_expr),
            },
        }

    antiderivative = sp.integrate(parsed, var_sym)
    if isinstance(antiderivative, sp.Integral):
        raise DomainError("Indefinite integral has no elementary closed-form antiderivative.")
    return {
        "result": f"{format_sympy_expr(antiderivative)} + C",
        "latex": f"{sp.latex(antiderivative)} + C",
        "details": {
            "method": "symbolic_indefinite_integration",
            "variable": var_sym.name,
            "constant_of_integration": "C",
        },
    }


def limit_expr(
    expression: str,
    variable: str | None = None,
    point: str | float | int = "0",
    direction: str = "+-",
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute the symbolic limit of an expression as `variable` approaches `point`."""
    if direction not in ("+", "-", "+-"):
        raise InvalidExpressionError("Limit 'direction' must be '+', '-', or '+-'.")

    parsed = parse_math_expression(expression, assumptions=assumptions)
    var_sym = _resolve_variable(parsed, variable, assumptions)
    point_expr = parse_math_expression(str(point), assumptions=assumptions)

    try:
        lim_val = sp.limit(parsed, var_sym, point_expr, dir=direction)
    except (ValueError, NotImplementedError) as exc:
        raise DomainError(f"Limit could not be determined: {exc}") from exc

    return {
        "result": format_sympy_expr(lim_val),
        "latex": sp.latex(lim_val),
        "details": {
            "method": "symbolic_limit",
            "variable": var_sym.name,
            "point": format_sympy_expr(point_expr),
            "direction": direction,
        },
    }
