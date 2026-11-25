"""Key mathematical point detection for 2D function plots (roots, intercepts, critical points)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import optimize as scipy_optimize
import sympy as sp

from app.modules.math_engine.parser.safe_parser import format_sympy_expr


def _finite_real(val: Any, *, max_abs: float = 1e6) -> float | None:
    try:
        c = complex(sp.N(val, 16))
    except Exception:
        return None
    if abs(c.imag) > 1e-8 or np.isnan(c.real) or np.isinf(c.real) or abs(c.real) > max_abs:
        return None
    return float(c.real)


def _find_roots_in_interval(
    expr: sp.Basic,
    var_sym: sp.Symbol,
    x_min: float,
    x_max: float,
    xs: np.ndarray,
    ys: list[float | None],
) -> list[float]:
    roots: list[float] = []

    # 1. Try symbolic solveset on bounded real interval
    try:
        sol_set = sp.solveset(expr, var_sym, domain=sp.Interval(x_min, x_max))
        if isinstance(sol_set, sp.FiniteSet):
            for s in sol_set:
                val = _finite_real(s)
                if val is not None and x_min <= val <= x_max:
                    roots.append(val)
    except Exception:
        pass

    # 2. Fallback / supplement via sampled sign-change bracketing + Brent's method
    if not roots:
        fn = sp.lambdify(var_sym, expr, modules=["numpy"])
        for i in range(len(xs) - 1):
            y1, y2 = ys[i], ys[i + 1]
            if y1 is None or y2 is None:
                continue
            if y1 == 0.0:
                roots.append(float(xs[i]))
            elif y1 * y2 < 0.0:
                try:
                    r = float(scipy_optimize.brentq(lambda t: float(np.real(fn(t))), float(xs[i]), float(xs[i + 1])))
                    if x_min <= r <= x_max:
                        roots.append(r)
                except Exception:
                    continue

    # Deduplicate nearby roots
    deduped: list[float] = []
    for r in sorted(roots):
        if not deduped or abs(r - deduped[-1]) > 1e-5:
            deduped.append(round(r, 6))
    return deduped[:25]


def detect_key_points(
    expr: sp.Basic,
    var_sym: sp.Symbol,
    x_min: float,
    x_max: float,
    xs: np.ndarray,
    ys: list[float | None],
) -> list[dict[str, Any]]:
    """Detect y-intercept, roots, and critical points (minima/maxima/stationary) on [x_min, x_max]."""
    points: list[dict[str, Any]] = []

    # Y-intercept
    if x_min <= 0.0 <= x_max:
        y0 = _finite_real(expr.subs(var_sym, 0))
        if y0 is not None:
            points.append(
                {
                    "kind": "y_intercept",
                    "x": 0.0,
                    "y": round(y0, 6),
                    "label": f"y-intercept (0, {round(y0, 4)})",
                }
            )

    # Roots
    for r in _find_roots_in_interval(expr, var_sym, x_min, x_max, xs, ys):
        y_check = _finite_real(expr.subs(var_sym, r))
        if y_check is not None and abs(y_check) < 1e-3:
            points.append(
                {
                    "kind": "root",
                    "x": r,
                    "y": 0.0,
                    "label": f"root ({round(r, 4)}, 0)",
                }
            )

    # Critical points via f'(x) = 0
    try:
        deriv = sp.diff(expr, var_sym)
        second_deriv = sp.diff(deriv, var_sym)
        deriv_fn = sp.lambdify(var_sym, deriv, modules=["numpy"])
        deriv_vals: list[float | None] = []
        for x_val in xs:
            try:
                c = complex(deriv_fn(float(x_val)))
                deriv_vals.append(float(c.real) if abs(c.imag) <= 1e-8 and np.isfinite(c.real) else None)
            except Exception:
                deriv_vals.append(None)

        crit_xs = _find_roots_in_interval(deriv, var_sym, x_min, x_max, xs, deriv_vals)
        for cx in crit_xs:
            cy = _finite_real(expr.subs(var_sym, cx))
            if cy is None:
                continue
            d2 = _finite_real(second_deriv.subs(var_sym, cx))
            if d2 is not None and d2 > 1e-6:
                kind = "local_min"
            elif d2 is not None and d2 < -1e-6:
                kind = "local_max"
            else:
                kind = "stationary_point"

            points.append(
                {
                    "kind": kind,
                    "x": cx,
                    "y": round(cy, 6),
                    "label": f"{kind.replace('_', ' ')} ({round(cx, 4)}, {round(cy, 4)})",
                    "derivative_expr": format_sympy_expr(deriv),
                }
            )
    except Exception:
        pass

    return points
