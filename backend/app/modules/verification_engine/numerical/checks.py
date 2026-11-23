"""Numerical residual and sample-point verification checks."""

from __future__ import annotations

from typing import Any

import numpy as np
import sympy as sp

from app.modules.math_engine.linear_algebra.operations import parse_matrix
from app.modules.math_engine.parser.safe_parser import (
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)
from app.modules.verification_engine.models import VerificationCheck

_SAMPLE_POINTS = (-1.7, -0.45, 0.35, 1.25, 2.4)
_RESIDUAL_TOL = 1e-6


def _safe_eval_complex(expr: sp.Basic, subs: dict[sp.Symbol, float]) -> complex | None:
    try:
        val = complex(sp.N(expr.subs(subs), 18))
    except Exception:
        return None
    if np.isnan(val.real) or np.isnan(val.imag) or np.isinf(val.real) or np.isinf(val.imag):
        return None
    return val


def run_numerical_checks(
    operation: str,
    expression: str | None,
    result: str,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
    options: dict[str, Any] | None = None,
) -> list[VerificationCheck]:
    """Run numerical residual and sample evaluation checks."""
    op = operation.strip().lower()
    opts = options or {}
    checks: list[VerificationCheck] = []

    if op in ("simplify", "expand", "factor") and expression:
        orig_expr = parse_math_expression(expression, assumptions=assumptions)
        res_expr = parse_math_expression(result, assumptions=assumptions)
        vars_list = sorted((orig_expr.free_symbols | res_expr.free_symbols), key=lambda s: s.name)
        if not vars_list:
            diff_val = _safe_eval_complex(orig_expr - res_expr, {})
            if diff_val is not None:
                err = abs(diff_val)
                checks.append(
                    VerificationCheck(
                        check_type="numerical",
                        name="constant_residual",
                        passed=err < _RESIDUAL_TOL,
                        residual=err,
                        message=f"Numerical residual between expressions is {err:.3e}.",
                    )
                )
            return checks

        residuals: list[float] = []
        for idx, base_pt in enumerate(_SAMPLE_POINTS):
            subs = {sym: base_pt + 0.13 * offset for offset, sym in enumerate(vars_list)}
            v1 = _safe_eval_complex(orig_expr, subs)
            v2 = _safe_eval_complex(res_expr, subs)
            if v1 is not None and v2 is not None:
                residuals.append(abs(v1 - v2))

        if residuals:
            max_err = max(residuals)
            checks.append(
                VerificationCheck(
                    check_type="numerical",
                    name="sample_point_equivalence",
                    passed=max_err < _RESIDUAL_TOL,
                    residual=max_err,
                    message=f"Checked {len(residuals)} sample point(s); max residual = {max_err:.3e}.",
                )
            )
        return checks

    if op in ("differentiate", "diff", "derivative") and expression:
        orig_expr = parse_math_expression(expression, assumptions=assumptions)
        res_expr = parse_math_expression(result, assumptions=assumptions)
        order = opts.get("order", 1)
        if order != 1:
            return checks

        all_vars = sorted((orig_expr.free_symbols | res_expr.free_symbols), key=lambda s: s.name)
        var_sym = parse_symbol(variable, assumptions=assumptions) if variable else (
            all_vars[0] if len(all_vars) == 1 else None
        )
        if var_sym is None or (all_vars and set(all_vars) != {var_sym}):
            return checks

        h = 1e-6
        residuals = []
        for pt in _SAMPLE_POINTS:
            f_plus = _safe_eval_complex(orig_expr, {var_sym: pt + h})
            f_minus = _safe_eval_complex(orig_expr, {var_sym: pt - h})
            df_res = _safe_eval_complex(res_expr, {var_sym: pt})
            if f_plus is not None and f_minus is not None and df_res is not None:
                fd = (f_plus - f_minus) / (2.0 * h)
                residuals.append(abs(fd - df_res))

        if residuals:
            max_err = max(residuals)
            checks.append(
                VerificationCheck(
                    check_type="numerical",
                    name="finite_difference_derivative",
                    passed=max_err < 1e-4,
                    residual=max_err,
                    message=f"Central finite-difference check across {len(residuals)} points; max error = {max_err:.3e}.",
                )
            )
        return checks

    if op in ("root_find", "nsolve") and expression:
        parsed_in = parse_math_input(expression, assumptions=assumptions)
        target_expr = (parsed_in.lhs - parsed_in.rhs) if isinstance(parsed_in, sp.Eq) else parsed_in
        free_syms = sorted(target_expr.free_symbols, key=lambda s: s.name)
        if len(free_syms) == 1:
            var_sym = parse_symbol(variable, assumptions=assumptions) if variable else free_syms[0]
            rhs_str = result.split("=", 1)[1].strip() if "=" in result else result.strip()
            root_expr = parse_math_expression(rhs_str, assumptions=assumptions)
            root_val = _safe_eval_complex(root_expr, {})
            if root_val is not None:
                res_val = _safe_eval_complex(target_expr, {var_sym: float(root_val.real)})
                if res_val is not None:
                    err = abs(res_val)
                    checks.append(
                        VerificationCheck(
                            check_type="numerical",
                            name="root_residual",
                            passed=err < _RESIDUAL_TOL,
                            residual=err,
                            message=f"Equation residual at root is |f(x)| = {err:.3e}.",
                        )
                    )
        return checks

    if op in ("matrix_determinant", "det", "determinant") and opts.get("matrix") is not None:
        mat = parse_matrix(opts["matrix"], assumptions=assumptions)
        if not mat.free_symbols and mat.rows == mat.cols:
            np_mat = np.array(mat.tolist(), dtype=np.complex128)
            np_det = complex(np.linalg.det(np_mat))
            res_expr = parse_math_expression(result, assumptions=assumptions)
            sym_det = _safe_eval_complex(res_expr, {})
            if sym_det is not None:
                err = abs(np_det - sym_det)
                checks.append(
                    VerificationCheck(
                        check_type="numerical",
                        name="numpy_determinant_residual",
                        passed=err < _RESIDUAL_TOL,
                        residual=err,
                        message=f"NumPy determinant difference is {err:.3e}.",
                    )
                )
        return checks

    return checks
