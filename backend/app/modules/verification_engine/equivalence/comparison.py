"""Cross-method verification checks (symbolic vs. numerical)."""

from __future__ import annotations

from typing import Any

from scipy import integrate as scipy_integrate
import sympy as sp

from app.modules.math_engine.numerical.operations import _compile_real_callable
from app.modules.math_engine.parser.safe_parser import parse_math_expression, parse_symbol
from app.modules.verification_engine.models import VerificationCheck


def run_cross_method_checks(
    operation: str,
    expression: str | None,
    result: str,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
    options: dict[str, Any] | None = None,
) -> list[VerificationCheck]:
    """Cross-check results using an independent computational method when applicable."""
    op = operation.strip().lower()
    opts = options or {}
    checks: list[VerificationCheck] = []

    if op in ("integrate", "int", "integral", "numerical_integrate", "quad") and expression:
        lower = opts.get("lower")
        upper = opts.get("upper")
        if lower is None or upper is None:
            return checks

        parsed = parse_math_expression(expression, assumptions=assumptions)
        free_syms = sorted(parsed.free_symbols, key=lambda s: s.name)
        var_sym = parse_symbol(variable, assumptions=assumptions) if variable else (
            free_syms[0] if len(free_syms) == 1 else sp.Symbol("x")
        )
        if parsed.free_symbols - {var_sym}:
            return checks

        try:
            a = float(sp.N(parse_math_expression(str(lower), assumptions=assumptions)))
            b = float(sp.N(parse_math_expression(str(upper), assumptions=assumptions)))
            res_num = float(sp.N(parse_math_expression(result, assumptions=assumptions)))
            fn = _compile_real_callable(parsed, var_sym)
            quad_val, quad_err = scipy_integrate.quad(fn, a, b)
        except Exception as exc:
            checks.append(
                VerificationCheck(
                    check_type="cross_method",
                    name="definite_integral_quadrature_cross_check",
                    passed=None,
                    message=f"Cross-method quadrature skipped: {exc}",
                )
            )
            return checks

        diff = abs(res_num - float(quad_val))
        tol = max(1e-6, 100.0 * float(quad_err))
        checks.append(
            VerificationCheck(
                check_type="cross_method",
                name="definite_integral_quadrature_cross_check",
                passed=diff <= tol,
                residual=diff,
                message=f"Comparison with adaptive quadrature (scipy.quad): |diff| = {diff:.3e} (tol {tol:.3e}).",
                details={"quad_value": float(quad_val), "quad_estimated_error": float(quad_err)},
            )
        )

    return checks
