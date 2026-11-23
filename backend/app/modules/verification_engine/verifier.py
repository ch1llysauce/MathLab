"""Unified entry point for the M3 Verification and Analysis Engine."""

from __future__ import annotations

from typing import Any

from app.core.security import run_with_timeout
from app.modules.verification_engine.analysis.classifier import classify_verification_checks
from app.modules.verification_engine.equivalence.comparison import run_cross_method_checks
from app.modules.verification_engine.models import VerificationCheck
from app.modules.verification_engine.numerical.checks import run_numerical_checks
from app.modules.verification_engine.symbolic.checks import run_symbolic_checks

_EXACT_SYMBOLIC_OPS = {
    "differentiate",
    "diff",
    "derivative",
    "integrate",
    "int",
    "integral",
    "simplify",
    "expand",
    "factor",
    "solve",
    "matrix_determinant",
    "det",
    "determinant",
    "matrix_inverse",
    "inverse",
    "inv",
    "matrix_eigenvalues",
    "eigenvalues",
    "matrix_eigenvectors",
    "eigenvectors",
}


def _run_verification(
    operation: str,
    expression: str | None,
    result: str,
    variable: str | None,
    assumptions: dict[str, str] | None,
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    checks: list[VerificationCheck] = []
    checks.extend(
        run_symbolic_checks(
            operation=operation,
            expression=expression,
            result=result,
            variable=variable,
            assumptions=assumptions,
            options=options,
        )
    )
    checks.extend(
        run_numerical_checks(
            operation=operation,
            expression=expression,
            result=result,
            variable=variable,
            assumptions=assumptions,
            options=options,
        )
    )
    checks.extend(
        run_cross_method_checks(
            operation=operation,
            expression=expression,
            result=result,
            variable=variable,
            assumptions=assumptions,
            options=options,
        )
    )

    op_key = operation.strip().lower()
    return classify_verification_checks(
        checks,
        symbolic_baseline=(op_key in _EXACT_SYMBOLIC_OPS),
    )


def verify_computation(
    operation: str,
    result: str,
    expression: str | None = None,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run bounded verification checks on a mathematical computation result."""
    return run_with_timeout(
        _run_verification,
        operation,
        expression,
        result,
        variable,
        assumptions,
        options,
    )
