"""Deterministic applicability rules for mathematical methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sympy as sp
from sympy.integrals.manualintegrate import manualintegrate

from app.modules.math_engine.parser.safe_parser import parse_math_expression, parse_symbol
from app.modules.reasoning_engine.classifier.classifier import ClassificationResult


@dataclass(frozen=True)
class RuleCheck:
    """Result of evaluating a single mathematical applicability rule."""

    rule_id: str
    description: str
    passed: bool
    severity: str  # "required" | "advisory"
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
        }


def evaluate_rules(
    operation: str | None,
    classification: ClassificationResult,
    variable: str | None = None,
    options: dict[str, Any] | None = None,
) -> list[RuleCheck]:
    """Evaluate deterministic preconditions for the requested operation and classified problem."""
    opts = options or {}
    op = (operation or "").strip().lower()
    checks: list[RuleCheck] = []

    if classification.domain == "linear_algebra":
        mat_a = classification.parsed_matrix
        mat_b = classification.parsed_matrix_b

        if mat_a is None:
            checks.append(
                RuleCheck(
                    rule_id="matrix_present",
                    description="Primary matrix must be provided.",
                    passed=False,
                    severity="required",
                    message="Missing 'options.matrix' for linear algebra operation.",
                )
            )
            return checks

        if op in ("matrix_determinant", "det", "determinant", "matrix_inverse", "inverse", "inv", "matrix_eigenvalues", "eigenvalues", "matrix_eigenvectors", "eigenvectors"):
            is_sq = mat_a.rows == mat_a.cols
            checks.append(
                RuleCheck(
                    rule_id="square_matrix_required",
                    description="Operation requires a square matrix (rows == cols).",
                    passed=is_sq,
                    severity="required",
                    message=(
                        f"Matrix is square ({mat_a.rows}x{mat_a.cols})."
                        if is_sq
                        else f"Matrix has shape {mat_a.rows}x{mat_a.cols}, which is not square."
                    ),
                )
            )
            if is_sq and op in ("matrix_inverse", "inverse", "inv"):
                det_val = mat_a.det()
                invertible = det_val != 0
                checks.append(
                    RuleCheck(
                        rule_id="nonsingular_matrix_required",
                        description="Matrix inverse requires a non-zero determinant.",
                        passed=invertible,
                        severity="required",
                        message=(
                            f"Determinant is {det_val} (non-zero); matrix is invertible."
                            if invertible
                            else "Determinant is 0; matrix is singular and has no inverse."
                        ),
                    )
                )

        if op == "matrix_add":
            same_shape = mat_b is not None and mat_a.shape == mat_b.shape
            checks.append(
                RuleCheck(
                    rule_id="matching_matrix_dimensions",
                    description="Matrix addition requires identical dimensions.",
                    passed=same_shape,
                    severity="required",
                    message=(
                        f"Both matrices share shape {mat_a.shape}."
                        if same_shape
                        else "Matrix dimensions do not match or matrix_b is missing."
                    ),
                )
            )

        if op == "matrix_multiply":
            compat = mat_b is not None and mat_a.cols == mat_b.rows
            checks.append(
                RuleCheck(
                    rule_id="multiplicative_dimension_match",
                    description="Matrix multiplication A*B requires A.cols == B.rows.",
                    passed=compat,
                    severity="required",
                    message=(
                        f"Inner dimensions match ({mat_a.cols} == {mat_b.rows})."
                        if compat
                        else "Inner matrix dimensions do not match or matrix_b is missing."
                    ),
                )
            )

        if op in ("linear_system_solve", "solve_system", "linsolve"):
            vec_raw = opts.get("vector")
            vec_len = len(vec_raw) if isinstance(vec_raw, list) else 0
            compat = isinstance(vec_raw, list) and vec_len == mat_a.rows
            checks.append(
                RuleCheck(
                    rule_id="linear_system_dimension_match",
                    description="Linear system Ax = b requires vector b length to match A.rows.",
                    passed=compat,
                    severity="required",
                    message=(
                        f"System dimensions compatible ({mat_a.rows} equations, {mat_a.cols} unknowns)."
                        if compat
                        else f"Vector b length ({vec_len}) must match matrix row count ({mat_a.rows})."
                    ),
                )
            )
        return checks

    expr = classification.parsed_expr
    if expr is None:
        checks.append(
            RuleCheck(
                rule_id="expression_present",
                description="A mathematical expression is required.",
                passed=False,
                severity="required",
                message="No mathematical expression was provided.",
            )
        )
        return checks

    free_vars = classification.variables

    # Solve rules
    if op == "solve" or (not op and classification.features.get("is_equation")):
        has_var = len(free_vars) >= 1
        checks.append(
            RuleCheck(
                rule_id="solve_variable_present",
                description="Solving requires at least one unknown variable.",
                passed=has_var,
                severity="required",
                message="Unknown variable detected." if has_var else "No free variable found to solve for.",
            )
        )
        if len(free_vars) > 1 and not variable:
            checks.append(
                RuleCheck(
                    rule_id="unambiguous_target_variable",
                    description="Multiple variables require explicit target variable.",
                    passed=False,
                    severity="required",
                    message=f"Multiple variables present ({', '.join(free_vars)}); specify 'variable'.",
                )
            )
        if classification.problem_type == "transcendental_equation":
            checks.append(
                RuleCheck(
                    rule_id="transcendental_solvability_advisory",
                    description="Transcendental equations may require numerical root finding.",
                    passed=True,
                    severity="advisory",
                    message="Symbolic solve may return principal-branch or conditional roots; numerical root_find is available as fallback.",
                )
            )

    # Calculus rules
    if op in ("differentiate", "diff", "derivative", "integrate", "int", "integral", "limit", "taylor_series", "taylor", "series"):
        if len(free_vars) > 1 and not variable:
            checks.append(
                RuleCheck(
                    rule_id="unambiguous_calculus_variable",
                    description="Multivariate expressions require an explicit differentiation/integration/limit variable.",
                    passed=False,
                    severity="required",
                    message=f"Multiple variables present ({', '.join(free_vars)}); specify 'variable'.",
                )
            )

    if op in ("partial_derivative", "partial", "pdiff") and not variable and not opts.get("variables") and len(free_vars) > 1:
        checks.append(
            RuleCheck(
                rule_id="partial_variable_required",
                description="Multivariable partial derivative requires 'variable' or 'options.variables'.",
                passed=False,
                severity="required",
                message=f"Specify target variable among ({', '.join(free_vars)}).",
            )
        )

    if op in ("taylor_series", "taylor", "series"):
        order_val = opts.get("order", 5)
        valid_order = isinstance(order_val, int) and 1 <= order_val <= 12
        checks.append(
            RuleCheck(
                rule_id="taylor_order_bounds",
                description="Taylor series order must be an integer between 1 and 12.",
                passed=valid_order,
                severity="required",
                message=f"Taylor order {order_val} is within [1, 12]." if valid_order else "Taylor order must be between 1 and 12.",
            )
        )

    if op in ("integrate", "int", "integral"):
        lower = opts.get("lower")
        upper = opts.get("upper")
        if (lower is None) != (upper is None):
            checks.append(
                RuleCheck(
                    rule_id="definite_bounds_paired",
                    description="Definite integration requires both lower and upper bounds.",
                    passed=False,
                    severity="required",
                    message="Provide both 'lower' and 'upper' bounds, or omit both for indefinite integration.",
                )
            )
        elif not isinstance(expr, sp.Eq):
            var_sym = parse_symbol(variable) if variable else (sp.Symbol(free_vars[0]) if free_vars else sp.Symbol("x"))
            antideriv = manualintegrate(expr, var_sym)
            has_elementary = not antideriv.has(sp.Integral)
            checks.append(
                RuleCheck(
                    rule_id="elementary_antiderivative_check",
                    description="Checks whether a closed-form symbolic antiderivative exists.",
                    passed=has_elementary,
                    severity="advisory" if (lower is not None and upper is not None) else "required",
                    message=(
                        "Closed-form symbolic antiderivative found."
                        if has_elementary
                        else "No elementary closed-form antiderivative; definite bounds allow numerical quadrature."
                    ),
                )
            )

    # Numerical rules
    if op in ("root_find", "nsolve"):
        single_var = len(free_vars) == 1
        checks.append(
            RuleCheck(
                rule_id="univariate_root_finding",
                description="Numerical root finding requires a single variable.",
                passed=single_var,
                severity="required",
                message=(
                    f"Single variable '{free_vars[0]}' detected."
                    if single_var
                    else f"Expected 1 variable for root finding, found {len(free_vars)}."
                ),
            )
        )
        bracket = opts.get("bracket")
        if isinstance(bracket, list) and len(bracket) == 2 and single_var and not isinstance(expr, sp.Eq):
            a, b = float(bracket[0]), float(bracket[1])
            ordered = a < b
            checks.append(
                RuleCheck(
                    rule_id="valid_bracket_order",
                    description="Root-finding bracket [a, b] must satisfy a < b.",
                    passed=ordered,
                    severity="required",
                    message="Bracket ordering a < b is valid." if ordered else f"Invalid bracket [{a}, {b}]: require a < b.",
                )
            )
            if ordered:
                var_sym = sp.Symbol(free_vars[0])
                try:
                    fa = float(sp.N(expr.subs(var_sym, a)))
                    fb = float(sp.N(expr.subs(var_sym, b)))
                    sign_change = fa == 0 or fb == 0 or (fa * fb < 0)
                    checks.append(
                        RuleCheck(
                            rule_id="bracket_sign_change",
                            description="Brent's method requires opposite signs f(a) and f(b) across [a, b].",
                            passed=sign_change,
                            severity="required",
                            message=(
                                "Sign change verified across bracket endpoints."
                                if sign_change
                                else f"No sign change on [{a}, {b}] (f(a)={fa:.4g}, f(b)={fb:.4g})."
                            ),
                        )
                    )
                except Exception:
                    checks.append(
                        RuleCheck(
                            rule_id="bracket_real_evaluation",
                            description="Bracket endpoints must evaluate to real finite numbers.",
                            passed=False,
                            severity="required",
                            message="Could not evaluate real finite values at bracket endpoints.",
                        )
                    )

    if op in ("numerical_eval", "evalf", "evaluate"):
        subs = opts.get("substitutions") or {}
        remaining = [v for v in free_vars if v not in subs]
        checks.append(
            RuleCheck(
                rule_id="all_variables_bound",
                description="Numerical evaluation requires all variables to be substituted.",
                passed=len(remaining) == 0,
                severity="required",
                message=(
                    "All variables are bound."
                    if not remaining
                    else f"Unbound variables remain: {', '.join(remaining)}."
                ),
            )
        )

    if op in ("numerical_integrate", "quad"):
        has_bounds = opts.get("lower") is not None and opts.get("upper") is not None
        checks.append(
            RuleCheck(
                rule_id="quadrature_bounds_present",
                description="Numerical quadrature requires finite lower and upper bounds.",
                passed=has_bounds,
                severity="required",
                message="Integration bounds provided." if has_bounds else "Missing 'lower' and/or 'upper' bounds.",
            )
        )
        if has_bounds:
            try:
                _ = float(sp.N(parse_math_expression(str(opts["lower"]))))
                _ = float(sp.N(parse_math_expression(str(opts["upper"]))))
            except Exception:
                checks.append(
                    RuleCheck(
                        rule_id="numeric_bounds_valid",
                        description="Quadrature bounds must evaluate numerically.",
                        passed=False,
                        severity="required",
                        message="Lower or upper bound could not be evaluated as a real number.",
                    )
                )

    return checks
