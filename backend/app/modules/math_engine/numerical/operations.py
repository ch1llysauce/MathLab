"""Numerical evaluation, root finding, and quadrature operations."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import integrate as scipy_integrate
from scipy import optimize as scipy_optimize
import sympy as sp

from app.core.exceptions import DomainError, InvalidExpressionError
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)


def numerical_eval(
    expression: str,
    precision: int = 15,
    substitutions: dict[str, str | float | int] | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Evaluate a mathematical expression numerically to the requested precision."""
    if not isinstance(precision, int) or precision < 1 or precision > 50:
        raise InvalidExpressionError("Precision must be an integer between 1 and 50.")

    parsed = parse_math_expression(expression, assumptions=assumptions)
    if substitutions:
        subs_map = {
            parse_symbol(name, assumptions=assumptions): parse_math_expression(str(val), assumptions=assumptions)
            for name, val in substitutions.items()
        }
        parsed = parsed.subs(subs_map)

    if parsed.free_symbols:
        remaining = sorted(sym.name for sym in parsed.free_symbols)
        raise InvalidExpressionError(
            "Cannot numerically evaluate expression with unbound variables.",
            details={"unbound_variables": remaining},
        )

    evaluated = sp.N(parsed, precision)
    return {
        "result": format_sympy_expr(evaluated),
        "latex": sp.latex(evaluated),
        "details": {
            "method": "numerical_evaluation",
            "precision": precision,
        },
    }


def _compile_real_callable(expr: sp.Basic, var_sym: sp.Symbol):
    func = sp.lambdify(var_sym, expr, modules=["numpy"])

    def wrapped(x_val: float) -> float:
        val = func(float(x_val))
        arr = np.asarray(val, dtype=np.complex128)
        if np.isnan(arr.real) or np.isinf(arr.real) or abs(arr.imag) > 1e-10:
            raise DomainError(f"Expression evaluated to non-real or undefined value at {var_sym.name}={x_val}.")
        return float(arr.real)

    return wrapped


def root_find(
    expression: str,
    variable: str | None = None,
    initial_guess: float | None = None,
    bracket: list[float] | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Find a numerical root using SciPy Brent's method (bracket) or SymPy nsolve (initial guess)."""
    parsed = parse_math_input(expression, assumptions=assumptions)
    target_expr = (parsed.lhs - parsed.rhs) if isinstance(parsed, sp.Eq) else parsed

    if variable:
        var_sym = parse_symbol(variable, assumptions=assumptions)
    else:
        free_syms = sorted(target_expr.free_symbols, key=lambda sym: sym.name)
        if len(free_syms) != 1:
            raise InvalidExpressionError("Root finding requires exactly one variable.")
        var_sym = free_syms[0]

    if bracket is not None:
        if not isinstance(bracket, list) or len(bracket) != 2:
            raise InvalidExpressionError("Bracket must be a list of two numbers [a, b].")
        a, b = float(bracket[0]), float(bracket[1])
        if a >= b:
            raise InvalidExpressionError("Bracket [a, b] must satisfy a < b.")
        fn = _compile_real_callable(target_expr, var_sym)
        try:
            root = float(scipy_optimize.brentq(fn, a, b))
        except ValueError as exc:
            raise DomainError(f"Root finding failed on bracket [{a}, {b}]: {exc}") from exc
        return {
            "result": f"{var_sym.name} = {root:.12g}",
            "latex": f"{sp.latex(var_sym)} \\approx {root:.12g}",
            "details": {
                "method": "scipy_brentq",
                "variable": var_sym.name,
                "root": root,
                "bracket": [a, b],
            },
        }

    guess = 1.0 if initial_guess is None else float(initial_guess)
    try:
        root_sym = sp.nsolve(target_expr, var_sym, guess)
    except Exception as exc:
        raise DomainError(f"Numerical root finding failed from initial guess {guess}: {exc}") from exc

    return {
        "result": f"{var_sym.name} = {format_sympy_expr(root_sym)}",
        "latex": f"{sp.latex(var_sym)} \\approx {sp.latex(root_sym)}",
        "details": {
            "method": "sympy_nsolve",
            "variable": var_sym.name,
            "root": float(sp.re(root_sym)) if sp.im(root_sym) == 0 else str(root_sym),
            "initial_guess": guess,
        },
    }


def numerical_integrate(
    expression: str,
    lower: float | int | str,
    upper: float | int | str,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute a definite numerical integral using SciPy adaptive quadrature."""
    parsed = parse_math_expression(expression, assumptions=assumptions)
    if variable:
        var_sym = parse_symbol(variable, assumptions=assumptions)
    else:
        free_syms = sorted(parsed.free_symbols, key=lambda sym: sym.name)
        if len(free_syms) > 1:
            raise InvalidExpressionError("Multiple variables found; please specify 'variable' explicitly.")
        var_sym = free_syms[0] if free_syms else sp.Symbol("x")

    if parsed.free_symbols - {var_sym}:
        raise InvalidExpressionError("Numerical integration does not allow unbound extra parameters.")

    a = float(sp.N(parse_math_expression(str(lower), assumptions=assumptions)))
    b = float(sp.N(parse_math_expression(str(upper), assumptions=assumptions)))
    fn = _compile_real_callable(parsed, var_sym)
    try:
        value, abs_error = scipy_integrate.quad(fn, a, b)
    except Exception as exc:
        raise DomainError(f"Numerical integration failed: {exc}") from exc

    return {
        "result": f"{value:.12g}",
        "latex": f"{value:.12g}",
        "details": {
            "method": "scipy_quad",
            "variable": var_sym.name,
            "lower": a,
            "upper": b,
            "value": float(value),
            "estimated_error": float(abs_error),
        },
    }
