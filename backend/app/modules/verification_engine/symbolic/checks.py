"""Symbolic equivalence, inverse-operation, and matrix verification checks."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from app.modules.math_engine.calculus.operations import parse_ode_equation
from app.modules.math_engine.linear_algebra.operations import _parse_vector, parse_matrix
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)
from app.modules.verification_engine.models import VerificationCheck

_CONST_SUFFIX_RE = re.compile(r"\s*\+\s*C\s*$")


def _strip_constant_of_integration(result: str) -> str:
    return _CONST_SUFFIX_RE.sub("", result.strip())


def _extract_solutions(result: str, variable: str | None, fallback_vars: list[str]) -> tuple[str, list[str]]:
    cleaned = result.strip()
    if "=" in cleaned:
        lhs, rhs = cleaned.split("=", 1)
        var_name = lhs.strip()
        items = [part.strip() for part in rhs.split(",") if part.strip()]
        return var_name, items
    var_name = variable or (fallback_vars[0] if fallback_vars else "x")
    items = [part.strip() for part in cleaned.split(",") if part.strip()]
    return var_name, items


def run_symbolic_checks(
    operation: str,
    expression: str | None,
    result: str,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
    options: dict[str, Any] | None = None,
) -> list[VerificationCheck]:
    """Run exact symbolic verification checks tailored to the mathematical operation."""
    op = operation.strip().lower()
    opts = options or {}
    checks: list[VerificationCheck] = []

    if op in ("simplify", "expand", "factor") and expression:
        orig_expr = parse_math_expression(expression, assumptions=assumptions)
        res_expr = parse_math_expression(result, assumptions=assumptions)
        diff = sp.simplify(orig_expr - res_expr)
        passed = bool(diff == 0)
        checks.append(
            VerificationCheck(
                check_type="symbolic",
                name="symbolic_equivalence",
                passed=passed,
                message=(
                    "Symbolic difference simplifies identically to 0."
                    if passed
                    else f"Symbolic difference did not simplify to 0 (got {format_sympy_expr(diff)})."
                ),
            )
        )
        return checks

    if op in ("integrate", "int", "integral") and expression:
        has_bounds = opts.get("lower") is not None and opts.get("upper") is not None
        if not has_bounds:
            orig_expr = parse_math_expression(expression, assumptions=assumptions)
            free_vars = sorted(s.name for s in orig_expr.free_symbols)
            var_sym = parse_symbol(variable, assumptions=assumptions) if variable else (
                sp.Symbol(free_vars[0]) if len(free_vars) == 1 else sp.Symbol("x")
            )
            antideriv_str = _strip_constant_of_integration(result)
            antideriv = parse_math_expression(antideriv_str, assumptions=assumptions)
            recovered = sp.diff(antideriv, var_sym)
            diff = sp.simplify(recovered - orig_expr)
            passed = bool(diff == 0)
            checks.append(
                VerificationCheck(
                    check_type="symbolic",
                    name="antiderivative_differentiation",
                    passed=passed,
                    message=(
                        "Differentiating the antiderivative reproduces the original integrand."
                        if passed
                        else f"Derivative of antiderivative differs by {format_sympy_expr(diff)}."
                    ),
                )
            )
        return checks

    if op == "solve" and expression:
        parsed_in = parse_math_input(expression, assumptions=assumptions)
        eq = parsed_in if isinstance(parsed_in, sp.Eq) else sp.Eq(parsed_in, 0)
        residual_expr = eq.lhs - eq.rhs
        free_vars = sorted(s.name for s in residual_expr.free_symbols)
        if result.strip().lower() == "no solution":
            checks.append(
                VerificationCheck(
                    check_type="symbolic",
                    name="empty_solution_set",
                    passed=None,
                    message="Empty solution set cannot be verified by direct substitution.",
                )
            )
            return checks

        var_name, items = _extract_solutions(result, variable, free_vars)
        var_sym = parse_symbol(var_name, assumptions=assumptions)
        verified_roots: list[str] = []
        failed_roots: list[str] = []

        for item in items:
            sol_expr = parse_math_expression(item, assumptions=assumptions)
            sub_val = sp.simplify(residual_expr.subs(var_sym, sol_expr))
            if sub_val == 0:
                verified_roots.append(item)
            else:
                failed_roots.append(item)

        if verified_roots and not failed_roots:
            checks.append(
                VerificationCheck(
                    check_type="substitution",
                    name="symbolic_root_substitution",
                    passed=True,
                    message=f"All {len(verified_roots)} solution(s) satisfy the equation identically.",
                    details={"verified_roots": verified_roots},
                )
            )
        elif verified_roots and failed_roots:
            checks.append(
                VerificationCheck(
                    check_type="substitution",
                    name="symbolic_root_substitution_verified",
                    passed=True,
                    message=f"{len(verified_roots)} root(s) satisfied the equation.",
                    details={"verified_roots": verified_roots},
                )
            )
            checks.append(
                VerificationCheck(
                    check_type="substitution",
                    name="symbolic_root_substitution_failed",
                    passed=False,
                    message=f"{len(failed_roots)} root(s) failed equation substitution.",
                    details={"failed_roots": failed_roots},
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    check_type="substitution",
                    name="symbolic_root_substitution",
                    passed=False,
                    message="Candidate solution(s) failed equation substitution.",
                    details={"failed_roots": failed_roots},
                )
            )
        return checks

    if op in ("matrix_inverse", "inverse", "inv") and opts.get("matrix") is not None:
        mat = parse_matrix(opts["matrix"], assumptions=assumptions)
        res_matrix_raw = (opts.get("details") or {}).get("matrix") or opts.get("result_matrix")
        if res_matrix_raw is not None:
            inv_mat = parse_matrix(res_matrix_raw, assumptions=assumptions)
            identity = sp.eye(mat.rows)
            passed = bool(sp.simplify(mat * inv_mat - identity) == sp.zeros(mat.rows) and sp.simplify(inv_mat * mat - identity) == sp.zeros(mat.rows))
            checks.append(
                VerificationCheck(
                    check_type="symbolic",
                    name="matrix_inverse_identity",
                    passed=passed,
                    message=(
                        "Verified A * A^-1 = I and A^-1 * A = I symbolically."
                        if passed
                        else "Matrix product A * A^-1 did not equal the identity matrix."
                    ),
                )
            )
        return checks

    if op in ("matrix_eigenvalues", "eigenvalues") and opts.get("matrix") is not None:
        mat = parse_matrix(opts["matrix"], assumptions=assumptions)
        eig_items = (opts.get("details") or {}).get("eigenvalues") or []
        if eig_items:
            lam = sp.Symbol("_lam")
            char_poly = (mat - lam * sp.eye(mat.rows)).det()
            all_ok = True
            for item in eig_items:
                val = parse_math_expression(str(item["value"]), assumptions=assumptions)
                if sp.simplify(char_poly.subs(lam, val)) != 0:
                    all_ok = False
                    break
            checks.append(
                VerificationCheck(
                    check_type="symbolic",
                    name="characteristic_polynomial_roots",
                    passed=all_ok,
                    message=(
                        "All eigenvalues satisfy det(A - lambda*I) = 0."
                        if all_ok
                        else "One or more eigenvalues failed det(A - lambda*I) = 0."
                    ),
                )
            )
        return checks

    if op in ("matrix_eigenvectors", "eigenvectors") and opts.get("matrix") is not None:
        mat = parse_matrix(opts["matrix"], assumptions=assumptions)
        eigensystem = (opts.get("details") or {}).get("eigensystem") or []
        if eigensystem:
            all_ok = True
            for group in eigensystem:
                lam_val = parse_math_expression(str(group["eigenvalue"]), assumptions=assumptions)
                for vec in group.get("vectors", []):
                    col = sp.Matrix([parse_math_expression(str(entry), assumptions=assumptions) for entry in vec])
                    if col.is_zero_matrix or sp.simplify(mat * col - lam_val * col) != sp.zeros(mat.rows, 1):
                        all_ok = False
                        break
            checks.append(
                VerificationCheck(
                    check_type="symbolic",
                    name="eigenvector_equation",
                    passed=all_ok,
                    message=(
                        "All eigenpairs satisfy A*v = lambda*v with non-zero vectors."
                        if all_ok
                        else "One or more eigenpairs failed A*v = lambda*v."
                    ),
                )
            )
        return checks

    if op in ("linear_system_solve", "solve_system", "linsolve") and opts.get("matrix") is not None and opts.get("vector") is not None:
        details = opts.get("details") or {}
        sol_vec = details.get("solution_vector")
        if sol_vec and details.get("unique", True):
            mat_a = parse_matrix(opts["matrix"], assumptions=assumptions)
            vec_b = _parse_vector(opts["vector"], assumptions=assumptions)
            vec_x = _parse_vector(sol_vec, assumptions=assumptions)
            residual = sp.simplify(mat_a * vec_x - vec_b)
            passed = bool(residual == sp.zeros(mat_a.rows, 1))
            checks.append(
                VerificationCheck(
                    check_type="substitution",
                    name="linear_system_substitution",
                    passed=passed,
                    message=(
                        "Verified A*x = b identically."
                        if passed
                        else "Solution vector failed A*x = b substitution."
                    ),
                )
            )
        return checks

    if op in ("solve_ode", "ode", "dsolve") and expression:
        dep_name = str(opts.get("dependent") or "y").strip()
        indep_name = (variable or "x").strip()
        ode_eq, _, y_func = parse_ode_equation(
            expression,
            variable=indep_name,
            dependent=dep_name,
            assumptions=assumptions,
        )
        rhs_str = (opts.get("details") or {}).get("rhs") or (
            result.split("=", 1)[1].strip() if "=" in result else result.strip()
        )
        rhs_expr = parse_math_expression(rhs_str, assumptions=assumptions)
        residual = sp.simplify((ode_eq.lhs - ode_eq.rhs).subs(y_func, rhs_expr).doit())
        passed = bool(residual == 0)
        checks.append(
            VerificationCheck(
                check_type="symbolic",
                name="ode_substitution",
                passed=passed,
                message=(
                    "Substituting y(x) back into the ODE yields 0 identically."
                    if passed
                    else f"ODE residual did not simplify to 0 (got {format_sympy_expr(residual)})."
                ),
            )
        )
        return checks

    if op in ("taylor_series", "taylor", "series") and expression:
        orig_expr = parse_math_expression(expression, assumptions=assumptions)
        series_expr = parse_math_expression(result, assumptions=assumptions)
        free_vars = sorted(s.name for s in orig_expr.free_symbols)
        var_sym = parse_symbol(variable, assumptions=assumptions) if variable else (
            sp.Symbol(free_vars[0]) if len(free_vars) == 1 else sp.Symbol("x")
        )
        pt_expr = parse_math_expression(str(opts.get("point", "0")), assumptions=assumptions)
        try:
            center_diff = sp.simplify(series_expr.subs(var_sym, pt_expr) - orig_expr.subs(var_sym, pt_expr))
            passed = bool(center_diff == 0)
            checks.append(
                VerificationCheck(
                    check_type="symbolic",
                    name="taylor_center_match",
                    passed=passed,
                    message=(
                        f"Taylor polynomial matches f({format_sympy_expr(pt_expr)}) exactly at expansion center."
                        if passed
                        else "Taylor polynomial failed to match at expansion center."
                    ),
                )
            )
        except Exception:
            pass
        return checks

    return checks
