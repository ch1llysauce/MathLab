"""2D and 3D mathematical function sampler and Plotly trace generator."""

from __future__ import annotations

from typing import Any

import numpy as np
import sympy as sp

from app.core.exceptions import ComputationLimitError, InvalidExpressionError
from app.core.security import run_with_timeout
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_symbol,
)
from app.modules.visualization_engine.features import _finite_real, detect_key_points
from app.modules.visualization_engine.matrix_plotter import generate_matrix_visualization_data

MAX_2D_POINTS = 1000
MAX_3D_GRID = 80
MAX_EXPRESSIONS = 6
_Y_CLIP = 1e6


def _apply_parameters(
    expr: sp.Basic,
    parameters: dict[str, float] | None,
    assumptions: dict[str, str] | None,
) -> sp.Basic:
    if not parameters:
        return expr
    subs_map = {
        parse_symbol(name, assumptions=assumptions): sp.Float(str(val))
        for name, val in parameters.items()
    }
    return expr.subs(subs_map)


def _eval_grid_1d(expr: sp.Basic, var_sym: sp.Symbol, xs: np.ndarray) -> list[float | None]:
    fn = sp.lambdify(var_sym, expr, modules=["numpy"])
    ys: list[float | None] = []
    for x_val in xs:
        try:
            raw = fn(float(x_val))
            c = complex(raw)
            if abs(c.imag) > 1e-8 or np.isnan(c.real) or np.isinf(c.real) or abs(c.real) > _Y_CLIP:
                ys.append(None)
            else:
                ys.append(float(c.real))
        except Exception:
            ys.append(None)
    return ys


def _raise_unbound_symbol_error(
    names: list[str],
    *,
    is_3d: bool,
    expr_str: str,
    parameters: dict[str, float] | None,
) -> None:
    """Raise a user-friendly InvalidExpressionError for unknown symbols in plot expressions."""
    quoted = ", ".join(f"'{n}'" for n in names)
    param_keys = set(parameters or {})
    looks_like_implicit_mul = any(
        len(n) >= 2
        and (
            n.endswith(("x", "y"))
            or any(n.startswith(p) and len(n) > len(p) for p in param_keys)
        )
        for n in names
    )

    if not is_3d and "y" in names and len(names) == 1:
        msg = (
            "2D plots only use 'x' as the input variable (y is the vertical axis). "
            "Switch to the 3D tab to plot f(x, y), or replace 'y' with 'x'."
        )
    elif looks_like_implicit_mul:
        msg = (
            f"Unknown symbol {quoted} in '{expr_str}'. "
            "Put '*' between letters when multiplying (for example 'w*x' instead of 'wx'), "
            "or set the constant name in the Parameter field."
        )
    elif is_3d:
        msg = (
            f"Unknown symbol {quoted} in '{expr_str}'. "
            "3D surfaces use 'x' and 'y' — if this is a constant, put its name in the Parameter field."
        )
    else:
        msg = (
            f"Unknown symbol {quoted} in '{expr_str}'. "
            "2D plots use 'x' — if this is a constant, put its name in the Parameter field."
        )

    raise InvalidExpressionError(msg, details={"unbound_parameters": names})


def _validate_range(bounds: list[float], label: str) -> tuple[float, float]:
    if len(bounds) != 2:
        raise InvalidExpressionError(f"Please provide both a minimum and maximum value for {label}.")
    lo, hi = float(bounds[0]), float(bounds[1])
    if not (np.isfinite(lo) and np.isfinite(hi)) or lo >= hi:
        raise InvalidExpressionError("Range minimum must be smaller than maximum (for example -5 to 5).")
    if hi - lo > 1e5:
        raise ComputationLimitError("Plot range is too wide — try keeping the span under 100,000.")
    return lo, hi


def _generate_2d_plot(
    expressions: list[str],
    variable: str,
    x_range: list[float],
    num_points: int,
    parameters: dict[str, float] | None,
    assumptions: dict[str, str] | None,
    include_derivative: bool,
    include_integral: bool,
    tangent_at: float | None,
    detect_features: bool,
) -> dict[str, Any]:
    x_min, x_max = _validate_range(x_range, "x_range")
    var_sym = parse_symbol(variable, assumptions=assumptions)
    xs = np.linspace(x_min, x_max, num_points)
    x_list = [round(float(x), 6) for x in xs]

    traces: list[dict[str, Any]] = []
    key_points: list[dict[str, Any]] = []

    for idx, expr_str in enumerate(expressions):
        parsed = _apply_parameters(parse_math_expression(expr_str, assumptions=assumptions), parameters, assumptions)
        extra_vars = parsed.free_symbols - {var_sym}
        if extra_vars:
            names = sorted(s.name for s in extra_vars)
            _raise_unbound_symbol_error(names, is_3d=False, expr_str=expr_str, parameters=parameters)

        ys = _eval_grid_1d(parsed, var_sym, xs)
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": f"f{idx + 1}(x) = {format_sympy_expr(parsed)}" if len(expressions) > 1 else format_sympy_expr(parsed),
                "x": x_list,
                "y": ys,
                "connectgaps": False,
            }
        )

        # Primary expression overlays & key mathematical points
        if idx == 0:
            if detect_features:
                key_points = detect_key_points(parsed, var_sym, x_min, x_max, xs, ys)
                if key_points:
                    traces.append(
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "name": "Key Points",
                            "x": [pt["x"] for pt in key_points],
                            "y": [pt["y"] for pt in key_points],
                            "text": [pt["label"] for pt in key_points],
                            "marker": {"size": 8},
                        }
                    )

            if include_derivative:
                deriv = sp.diff(parsed, var_sym)
                dy = _eval_grid_1d(deriv, var_sym, xs)
                traces.append(
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "name": f"d/d{var_sym.name}: {format_sympy_expr(deriv)}",
                        "x": x_list,
                        "y": dy,
                        "line": {"dash": "dash"},
                        "connectgaps": False,
                    }
                )

            if include_integral:
                traces.append(
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "name": f"Area under {format_sympy_expr(parsed)}",
                        "x": x_list,
                        "y": ys,
                        "fill": "tozeroy",
                        "opacity": 0.25,
                        "connectgaps": False,
                    }
                )

            if tangent_at is not None:
                x0 = float(tangent_at)
                y0 = _finite_real(parsed.subs(var_sym, x0))
                slope = _finite_real(sp.diff(parsed, var_sym).subs(var_sym, x0))
                if y0 is not None and slope is not None:
                    tan_expr = y0 + slope * (var_sym - x0)
                    ty = _eval_grid_1d(tan_expr, var_sym, xs)
                    traces.append(
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "name": f"Tangent at {var_sym.name}={x0:g} (slope={slope:.4g})",
                            "x": x_list,
                            "y": ty,
                            "line": {"dash": "dot"},
                        }
                    )
                    traces.append(
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "name": f"Tangent Point ({x0:g}, {y0:.4g})",
                            "x": [x0],
                            "y": [y0],
                            "marker": {"size": 9},
                        }
                    )

    return {
        "plot_type": "2d",
        "traces": traces,
        "key_points": key_points,
        "layout": {
            "title": ", ".join(expressions),
            "xaxis_title": var_sym.name,
            "yaxis_title": "y",
        },
        "metadata": {
            "num_points": num_points,
            "x_range": [x_min, x_max],
            "parameters": parameters or {},
        },
    }


def _eval_grid_2d(
    expr: sp.Basic,
    x_sym: sp.Symbol,
    y_sym: sp.Symbol,
    xs: np.ndarray,
    ys: np.ndarray,
) -> list[list[float | None]]:
    """Sample a 2-variable expression over the (x, y) mesh with singularity clipping."""
    fn = sp.lambdify((x_sym, y_sym), expr, modules=["numpy"])
    z_matrix: list[list[float | None]] = []
    for y_val in ys:
        row: list[float | None] = []
        for x_val in xs:
            try:
                c = complex(fn(float(x_val), float(y_val)))
                if abs(c.imag) > 1e-8 or np.isnan(c.real) or np.isinf(c.real) or abs(c.real) > _Y_CLIP:
                    row.append(None)
                else:
                    row.append(float(c.real))
            except Exception:
                row.append(None)
        z_matrix.append(row)
    return z_matrix


def _generate_3d_plot(
    expressions: list[str],
    x_var: str,
    y_var: str,
    x_range: list[float],
    y_range: list[float],
    grid_size: int,
    parameters: dict[str, float] | None,
    assumptions: dict[str, str] | None,
    include_derivative: bool = False,
    tangent_at: float | None = None,
    tangent_y: float | None = None,
) -> dict[str, Any]:
    x_min, x_max = _validate_range(x_range, "x_range")
    y_min, y_max = _validate_range(y_range, "y_range")
    x_sym = parse_symbol(x_var, assumptions=assumptions)
    y_sym = parse_symbol(y_var, assumptions=assumptions)
    if x_sym == y_sym:
        raise InvalidExpressionError("3D plots require two distinct variables.")

    xs = np.linspace(x_min, x_max, grid_size)
    ys = np.linspace(y_min, y_max, grid_size)
    x_list = [round(float(x), 6) for x in xs]
    y_list = [round(float(y), 6) for y in ys]

    traces: list[dict[str, Any]] = []
    primary_parsed: sp.Basic | None = None

    for idx, expr_str in enumerate(expressions):
        parsed = _apply_parameters(parse_math_expression(expr_str, assumptions=assumptions), parameters, assumptions)
        extra_vars = parsed.free_symbols - {x_sym, y_sym}
        if extra_vars:
            names = sorted(s.name for s in extra_vars)
            _raise_unbound_symbol_error(names, is_3d=True, expr_str=expr_str, parameters=parameters)

        if idx == 0:
            primary_parsed = parsed

        z_matrix = _eval_grid_2d(parsed, x_sym, y_sym, xs, ys)
        surface_trace: dict[str, Any] = {
            "type": "surface",
            "name": f"f{idx + 1}(x, y) = {format_sympy_expr(parsed)}" if len(expressions) > 1 else format_sympy_expr(parsed),
            "x": x_list,
            "y": y_list,
            "z": z_matrix,
            "showlegend": True,
        }
        if idx > 0:
            surface_trace["opacity"] = 0.65
            surface_trace["showscale"] = False
            surface_trace["colorscale"] = "Viridis"
        traces.append(surface_trace)

    if primary_parsed is not None:
        df_dx = sp.diff(primary_parsed, x_sym)
        df_dy = sp.diff(primary_parsed, y_sym)

        if include_derivative:
            traces.append(
                {
                    "type": "surface",
                    "name": f"∂f/∂{x_sym.name}: {format_sympy_expr(df_dx)}",
                    "x": x_list,
                    "y": y_list,
                    "z": _eval_grid_2d(df_dx, x_sym, y_sym, xs, ys),
                    "opacity": 0.45,
                    "showscale": False,
                    "colorscale": "Cividis",
                    "showlegend": True,
                }
            )
            if y_sym in primary_parsed.free_symbols:
                traces.append(
                    {
                        "type": "surface",
                        "name": f"∂f/∂{y_sym.name}: {format_sympy_expr(df_dy)}",
                        "x": x_list,
                        "y": y_list,
                        "z": _eval_grid_2d(df_dy, x_sym, y_sym, xs, ys),
                        "opacity": 0.45,
                        "showscale": False,
                        "colorscale": "Portland",
                        "showlegend": True,
                    }
                )

        if tangent_at is not None:
            x0 = float(tangent_at)
            y0 = float(tangent_y) if tangent_y is not None else 0.0
            subs_pt = {x_sym: x0, y_sym: y0}
            z0 = _finite_real(primary_parsed.subs(subs_pt))
            fx = _finite_real(df_dx.subs(subs_pt))
            fy = _finite_real(df_dy.subs(subs_pt))
            if z0 is not None and fx is not None and fy is not None:
                tan_plane_expr = z0 + fx * (x_sym - x0) + fy * (y_sym - y0)
                traces.append(
                    {
                        "type": "surface",
                        "name": f"Tangent Plane at ({x0:g}, {y0:g})",
                        "x": x_list,
                        "y": y_list,
                        "z": _eval_grid_2d(tan_plane_expr, x_sym, y_sym, xs, ys),
                        "opacity": 0.4,
                        "showscale": False,
                        "colorscale": [[0, "#f59e0b"], [1, "#f59e0b"]],
                        "showlegend": True,
                    }
                )
                traces.append(
                    {
                        "type": "scatter3d",
                        "mode": "lines",
                        "name": f"Tangent ∂{x_sym.name} (slope={fx:.4g})",
                        "x": x_list,
                        "y": [y0] * len(x_list),
                        "z": [round(float(z0 + fx * (float(xv) - x0)), 6) for xv in xs],
                        "line": {"width": 5, "color": "#dc2626"},
                    }
                )
                if y_sym in primary_parsed.free_symbols or abs(fy) > 1e-12:
                    traces.append(
                        {
                            "type": "scatter3d",
                            "mode": "lines",
                            "name": f"Tangent ∂{y_sym.name} (slope={fy:.4g})",
                            "x": [x0] * len(y_list),
                            "y": y_list,
                            "z": [round(float(z0 + fy * (float(yv) - y0)), 6) for yv in ys],
                            "line": {"width": 5, "color": "#2563eb"},
                        }
                    )
                traces.append(
                    {
                        "type": "scatter3d",
                        "mode": "markers",
                        "name": f"Tangent Point ({x0:g}, {y0:g}, {z0:.4g})",
                        "x": [x0],
                        "y": [y0],
                        "z": [z0],
                        "marker": {"size": 6, "color": "#7c3aed"},
                    }
                )

    return {
        "plot_type": "3d",
        "traces": traces,
        "key_points": [],
        "layout": {
            "title": ", ".join(expressions),
            "xaxis_title": x_sym.name,
            "yaxis_title": y_sym.name,
            "zaxis_title": "z",
        },
        "metadata": {
            "grid_size": grid_size,
            "x_range": [x_min, x_max],
            "y_range": [y_min, y_max],
            "parameters": parameters or {},
        },
    }


def generate_visualization_data(
    *,
    expression: str | None = None,
    expressions: list[str] | None = None,
    plot_type: str = "2d",
    variables: list[str] | None = None,
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    num_points: int = 250,
    grid_size: int = 35,
    parameters: dict[str, float] | None = None,
    assumptions: dict[str, str] | None = None,
    include_derivative: bool = False,
    include_integral: bool = False,
    tangent_at: float | None = None,
    tangent_y: float | None = None,
    detect_features: bool = True,
    matrix: list[list[Any]] | None = None,
    matrix_b: list[list[Any]] | None = None,
    vector: list[Any] | None = None,
    matrix_view: str = "auto",
) -> dict[str, Any]:
    """Generate bounded 2D, 3D, or matrix Plotly-compatible visualization datasets."""
    ptype = plot_type.strip().lower()
    if ptype == "matrix":
        return run_with_timeout(
            generate_matrix_visualization_data,
            matrix=matrix,
            matrix_b=matrix_b,
            vector=vector,
            matrix_view=matrix_view,
            parameters=parameters,
            assumptions=assumptions,
        )

    expr_list = [e.strip() for e in (expressions or []) if e and e.strip()]
    if expression and expression.strip() and expression.strip() not in expr_list:
        expr_list.insert(0, expression.strip())

    if not expr_list:
        raise InvalidExpressionError("At least one mathematical expression is required for plotting.")
    if len(expr_list) > MAX_EXPRESSIONS:
        raise ComputationLimitError(f"Maximum of {MAX_EXPRESSIONS} expressions per plot exceeded.")

    if ptype == "3d":
        if grid_size < 10 or grid_size > MAX_3D_GRID:
            raise ComputationLimitError(f"3D 'grid_size' must be between 10 and {MAX_3D_GRID}.")
        vars_2 = variables or ["x", "y"]
        if len(vars_2) != 2:
            raise InvalidExpressionError("3D plots require exactly 2 variables in 'variables', e.g. ['x', 'y'].")
        return run_with_timeout(
            _generate_3d_plot,
            expr_list,
            vars_2[0],
            vars_2[1],
            x_range or [-5.0, 5.0],
            y_range or [-5.0, 5.0],
            grid_size,
            parameters,
            assumptions,
            include_derivative,
            tangent_at,
            tangent_y,
        )

    if ptype != "2d":
        raise InvalidExpressionError("Field 'plot_type' must be '2d' or '3d'.")

    if num_points < 10 or num_points > MAX_2D_POINTS:
        raise ComputationLimitError(f"2D 'num_points' must be between 10 and {MAX_2D_POINTS}.")

    x_var = variables[0] if variables else "x"
    return run_with_timeout(
        _generate_2d_plot,
        expr_list,
        x_var,
        x_range or [-10.0, 10.0],
        num_points,
        parameters,
        assumptions,
        include_derivative,
        include_integral,
        tangent_at,
        detect_features,
    )
