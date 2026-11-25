"""Symbolic calculus operations."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from app.core.exceptions import DomainError, InvalidExpressionError
from app.core.security import validate_expression_bounds
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_math_input,
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


def partial_derivative_expr(
    expression: str,
    variable: str | None = None,
    variables: list[str] | None = None,
    order: int = 1,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute first-order, higher-order, or mixed partial derivatives."""
    if not isinstance(order, int) or order < 1 or order > 10:
        raise InvalidExpressionError("Derivative 'order' must be an integer between 1 and 10.")

    parsed = parse_math_expression(expression, assumptions=assumptions)

    if variables:
        if not isinstance(variables, list) or not all(isinstance(v, str) and v.strip() for v in variables):
            raise InvalidExpressionError("Field 'options.variables' must be a non-empty list of variable names.")
        diff_syms = [parse_symbol(v, assumptions=assumptions) for v in variables]
        result_expr = sp.diff(parsed, *diff_syms)
        diff_vars = [s.name for s in diff_syms]
    else:
        if not variable or not variable.strip():
            free_syms = sorted(parsed.free_symbols, key=lambda sym: sym.name)
            if len(free_syms) != 1:
                raise InvalidExpressionError(
                    "Specify 'variable' (or 'options.variables') for multivariable partial differentiation.",
                    details={"variables": [s.name for s in free_syms]},
                )
            var_sym = free_syms[0]
        else:
            var_sym = parse_symbol(variable, assumptions=assumptions)
        result_expr = sp.diff(parsed, var_sym, order)
        diff_vars = [var_sym.name] * order

    return {
        "result": format_sympy_expr(result_expr),
        "latex": sp.latex(result_expr),
        "details": {
            "method": "symbolic_partial_differentiation",
            "differentiated_with_respect_to": diff_vars,
        },
    }


def taylor_series_expr(
    expression: str,
    variable: str | None = None,
    point: str | float | int = "0",
    order: int = 5,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute a Taylor polynomial expansion of an expression around `point` up to `order`."""
    if not isinstance(order, int) or order < 1 or order > 12:
        raise InvalidExpressionError("Taylor series 'order' must be an integer between 1 and 12.")

    parsed = parse_math_expression(expression, assumptions=assumptions)
    var_sym = _resolve_variable(parsed, variable, assumptions)
    point_expr = parse_math_expression(str(point), assumptions=assumptions)

    try:
        series_expr = sp.series(parsed, var_sym, point_expr, order + 1).removeO()
    except (ValueError, NotImplementedError, sp.PoleError) as exc:
        raise DomainError(f"Taylor expansion failed around {var_sym.name}={point_expr}: {exc}") from exc

    return {
        "result": format_sympy_expr(series_expr),
        "latex": sp.latex(series_expr),
        "details": {
            "method": "symbolic_taylor_series",
            "variable": var_sym.name,
            "point": format_sympy_expr(point_expr),
            "order": order,
        },
    }


def parse_ode_equation(
    expression: str,
    variable: str = "x",
    dependent: str = "y",
    assumptions: dict[str, str] | None = None,
) -> tuple[sp.Eq, sp.Symbol, sp.Basic]:
    """Safely parse a 1st or 2nd order ODE string into a SymPy Eq(lhs, rhs)."""
    cleaned = validate_expression_bounds(expression)
    x_sym = parse_symbol(variable, assumptions=assumptions)
    dep_sym = parse_symbol(dependent, assumptions=assumptions)
    dep = dep_sym.name
    indep = x_sym.name
    if dep == indep:
        raise InvalidExpressionError("Dependent and independent variables in an ODE must differ.")

    rewritten = re.sub(rf"\b{re.escape(dep)}''", "odeD2y", cleaned)
    rewritten = re.sub(rf"\b{re.escape(dep)}'", "odeD1y", rewritten)
    rewritten = re.sub(rf"\bd\^?2{re.escape(dep)}\s*/\s*d{re.escape(indep)}\^?2\b", "odeD2y", rewritten)
    rewritten = re.sub(rf"\bd{re.escape(dep)}\s*/\s*d{re.escape(indep)}\b", "odeD1y", rewritten)
    if "'" in rewritten or '"' in rewritten:
        raise InvalidExpressionError("Unsupported prime or quote syntax in ODE expression.")

    parsed = parse_math_input(rewritten, assumptions=assumptions)
    eq = parsed if isinstance(parsed, sp.Eq) else sp.Eq(parsed, 0)

    y_func = sp.Function(dep)(x_sym)
    subs_map = {
        sp.Symbol("odeD2y"): sp.Derivative(y_func, x_sym, 2),
        sp.Symbol("odeD1y"): sp.Derivative(y_func, x_sym),
        sp.Symbol(dep): y_func,
    }
    ode_eq = sp.Eq(eq.lhs.subs(subs_map), eq.rhs.subs(subs_map))
    if not ode_eq.has(sp.Derivative):
        raise InvalidExpressionError(
            f"ODE must contain a derivative term such as {dep}', {dep}'', or d{dep}/d{indep}."
        )
    return ode_eq, x_sym, y_func


def solve_ode_expr(
    expression: str,
    variable: str | None = None,
    dependent: str | None = None,
    ics: dict[str, str | float | int] | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Solve a 1st or 2nd order ordinary differential equation symbolically."""
    indep_name = (variable or "x").strip()
    dep_name = (dependent or "y").strip()
    ode_eq, x_sym, y_func = parse_ode_equation(
        expression,
        variable=indep_name,
        dependent=dep_name,
        assumptions=assumptions,
    )

    parsed_ics: dict[sp.Basic, sp.Basic] | None = None
    if ics:
        parsed_ics = {}
        ic_first_re = re.compile(rf"^{re.escape(dep_name)}'\(\s*([^)]+)\s*\)$")
        ic_val_re = re.compile(rf"^{re.escape(dep_name)}\(\s*([^)]+)\s*\)$")
        for key, raw_val in ics.items():
            val_expr = parse_math_expression(str(raw_val), assumptions=assumptions)
            k_clean = key.strip()
            m_first = ic_first_re.match(k_clean)
            m_val = ic_val_re.match(k_clean)
            if m_first:
                pt = parse_math_expression(m_first.group(1), assumptions=assumptions)
                parsed_ics[sp.Derivative(y_func, x_sym).subs(x_sym, pt)] = val_expr
            elif m_val:
                pt = parse_math_expression(m_val.group(1), assumptions=assumptions)
                parsed_ics[y_func.subs(x_sym, pt)] = val_expr
            else:
                raise InvalidExpressionError(
                    f"Invalid initial condition key '{key}'. Use '{dep_name}(0)' or '{dep_name}'(0)'."
                )

    try:
        solution = sp.dsolve(ode_eq, y_func, ics=parsed_ics)
    except (NotImplementedError, ValueError) as exc:
        raise DomainError(f"ODE could not be solved symbolically: {exc}") from exc

    if isinstance(solution, list):
        solution = solution[0]

    rhs_str = format_sympy_expr(solution.rhs)
    return {
        "result": f"{dep_name}({x_sym.name}) = {rhs_str}",
        "latex": sp.latex(solution),
        "details": {
            "method": "symbolic_ode_dsolve",
            "variable": x_sym.name,
            "dependent": dep_name,
            "rhs": rhs_str,
        },
    }
