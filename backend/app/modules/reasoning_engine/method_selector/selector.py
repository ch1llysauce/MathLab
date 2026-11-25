"""Deterministic method selector and rationale generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.reasoning_engine.classifier.classifier import ClassificationResult
from app.modules.reasoning_engine.rules.rules import RuleCheck


@dataclass(frozen=True)
class MethodCandidate:
    """Candidate computational method with applicability assessment."""

    operation: str
    method: str
    applicable: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "method": self.method,
            "applicable": self.applicable,
            "reason": self.reason,
        }


@dataclass
class MethodSelection:
    """Selected method, applicability status, alternatives, and rationale."""

    recommended_operation: str
    recommended_method: str
    applicable: bool
    rationale: str
    candidates: list[MethodCandidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_operation": self.recommended_operation,
            "recommended_method": self.recommended_method,
            "applicable": self.applicable,
            "rationale": self.rationale,
            "candidates": [c.to_dict() for c in self.candidates],
        }


_DEFAULT_METHODS = {
    "simplify": ("simplify", "symbolic_simplification"),
    "expand": ("expand", "symbolic_expansion"),
    "factor": ("factor", "symbolic_factorization"),
    "solve": ("solve", "symbolic_solve"),
    "differentiate": ("differentiate", "symbolic_differentiation"),
    "diff": ("differentiate", "symbolic_differentiation"),
    "derivative": ("differentiate", "symbolic_differentiation"),
    "integrate": ("integrate", "symbolic_indefinite_integration"),
    "int": ("integrate", "symbolic_indefinite_integration"),
    "integral": ("integrate", "symbolic_indefinite_integration"),
    "limit": ("limit", "symbolic_limit"),
    "partial_derivative": ("partial_derivative", "symbolic_partial_differentiation"),
    "partial": ("partial_derivative", "symbolic_partial_differentiation"),
    "pdiff": ("partial_derivative", "symbolic_partial_differentiation"),
    "taylor_series": ("taylor_series", "symbolic_taylor_series"),
    "taylor": ("taylor_series", "symbolic_taylor_series"),
    "series": ("taylor_series", "symbolic_taylor_series"),
    "solve_ode": ("solve_ode", "symbolic_ode_dsolve"),
    "ode": ("solve_ode", "symbolic_ode_dsolve"),
    "dsolve": ("solve_ode", "symbolic_ode_dsolve"),
    "matrix_determinant": ("matrix_determinant", "matrix_determinant"),
    "det": ("matrix_determinant", "matrix_determinant"),
    "determinant": ("matrix_determinant", "matrix_determinant"),
    "matrix_rank": ("matrix_rank", "matrix_rank"),
    "rank": ("matrix_rank", "matrix_rank"),
    "matrix_transpose": ("matrix_transpose", "matrix_transpose"),
    "transpose": ("matrix_transpose", "matrix_transpose"),
    "matrix_inverse": ("matrix_inverse", "matrix_inverse"),
    "inverse": ("matrix_inverse", "matrix_inverse"),
    "inv": ("matrix_inverse", "matrix_inverse"),
    "matrix_rref": ("matrix_rref", "matrix_rref"),
    "rref": ("matrix_rref", "matrix_rref"),
    "matrix_eigenvalues": ("matrix_eigenvalues", "matrix_eigenvalues"),
    "eigenvalues": ("matrix_eigenvalues", "matrix_eigenvalues"),
    "matrix_eigenvectors": ("matrix_eigenvectors", "matrix_eigenvectors"),
    "eigenvectors": ("matrix_eigenvectors", "matrix_eigenvectors"),
    "matrix_add": ("matrix_add", "matrix_addition"),
    "matrix_multiply": ("matrix_multiply", "matrix_multiplication"),
    "linear_system_solve": ("linear_system_solve", "symbolic_linsolve"),
    "solve_system": ("linear_system_solve", "symbolic_linsolve"),
    "linsolve": ("linear_system_solve", "symbolic_linsolve"),
    "numerical_eval": ("numerical_eval", "numerical_evaluation"),
    "evalf": ("numerical_eval", "numerical_evaluation"),
    "evaluate": ("numerical_eval", "numerical_evaluation"),
    "root_find": ("root_find", "sympy_nsolve"),
    "nsolve": ("root_find", "sympy_nsolve"),
    "numerical_integrate": ("numerical_integrate", "scipy_quad"),
    "quad": ("numerical_integrate", "scipy_quad"),
}


def select_method(
    operation: str | None,
    classification: ClassificationResult,
    rules: list[RuleCheck],
    options: dict[str, Any] | None = None,
) -> MethodSelection:
    """Select the best applicable mathematical method and explain why."""
    opts = options or {}
    op = (operation or "").strip().lower()
    required_failures = [r for r in rules if r.severity == "required" and not r.passed]
    advisory_failures = [r for r in rules if r.severity == "advisory" and not r.passed]

    # Auto-infer operation when none was specified
    if not op:
        if classification.domain == "linear_algebra":
            op = "matrix_determinant" if classification.features.get("is_square") else "matrix_rank"
        elif classification.features.get("is_equation"):
            op = "solve"
        else:
            op = "simplify"

    canonical_op, method_name = _DEFAULT_METHODS.get(op, (op, op))
    candidates: list[MethodCandidate] = []

    # Definite integration & automatic quadrature fallback
    if canonical_op == "integrate":
        has_bounds = opts.get("lower") is not None and opts.get("upper") is not None
        if has_bounds:
            method_name = "symbolic_definite_integration"
            symbolic_ok = not any(r.rule_id == "elementary_antiderivative_check" and not r.passed for r in advisory_failures)
            candidates.append(
                MethodCandidate(
                    operation="integrate",
                    method="symbolic_definite_integration",
                    applicable=symbolic_ok and not required_failures,
                    reason=(
                        "Exact symbolic definite integration applies when an elementary antiderivative exists."
                        if symbolic_ok
                        else "No elementary antiderivative exists for closed-form symbolic integration."
                    ),
                )
            )
            candidates.append(
                MethodCandidate(
                    operation="numerical_integrate",
                    method="scipy_quad",
                    applicable=not required_failures,
                    reason="Adaptive numerical quadrature evaluates definite integrals over finite bounds without requiring an elementary antiderivative.",
                )
            )
            if not symbolic_ok and not required_failures:
                return MethodSelection(
                    recommended_operation="numerical_integrate",
                    recommended_method="scipy_quad",
                    applicable=True,
                    rationale="Symbolic definite integration found no elementary antiderivative, so adaptive numerical quadrature (scipy_quad) is selected over the given bounds.",
                    candidates=candidates,
                )

    # Root finding method specialization
    if canonical_op == "root_find":
        has_bracket = isinstance(opts.get("bracket"), list) and len(opts["bracket"]) == 2
        method_name = "scipy_brentq" if has_bracket else "sympy_nsolve"
        candidates.append(
            MethodCandidate(
                operation="root_find",
                method=method_name,
                applicable=not required_failures,
                reason=(
                    "Brent's bracketed method guarantees convergence when f(a) and f(b) have opposite signs."
                    if has_bracket
                    else "Newton/secant nsolve searches locally from an initial guess."
                ),
            )
        )

    # Algebraic solve with numerical root-finding alternative for transcendental equations
    if canonical_op == "solve":
        candidates.append(
            MethodCandidate(
                operation="solve",
                method="symbolic_solve",
                applicable=not required_failures,
                reason="Exact symbolic solver handles linear, quadratic, polynomial, and supported algebraic equations.",
            )
        )
        if classification.problem_type == "transcendental_equation":
            candidates.append(
                MethodCandidate(
                    operation="root_find",
                    method="sympy_nsolve",
                    applicable=len(classification.variables) == 1,
                    reason="Numerical root finding can approximate roots when transcendental equations lack closed-form solutions.",
                )
            )

    if not candidates:
        candidates.append(
            MethodCandidate(
                operation=canonical_op,
                method=method_name,
                applicable=not required_failures,
                reason=(
                    f"Preconditions satisfied for {classification.problem_type} using {method_name}."
                    if not required_failures
                    else "; ".join(r.message for r in required_failures)
                ),
            )
        )

    applicable = len(required_failures) == 0
    if applicable:
        rationale = (
            f"Classified as {classification.problem_type} ({classification.domain}); "
            f"selected '{method_name}' because all required applicability conditions passed."
        )
    else:
        rationale = (
            f"Classified as {classification.problem_type} ({classification.domain}), "
            f"but '{method_name}' is not applicable: {'; '.join(r.message for r in required_failures)}"
        )

    return MethodSelection(
        recommended_operation=canonical_op,
        recommended_method=method_name,
        applicable=applicable,
        rationale=rationale,
        candidates=candidates,
    )
