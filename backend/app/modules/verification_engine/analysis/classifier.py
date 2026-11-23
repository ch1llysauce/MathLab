"""Verification outcome aggregation and qualification analysis."""

from __future__ import annotations

from typing import Any

from app.modules.verification_engine.models import VerificationCheck


def classify_verification_checks(
    checks: list[VerificationCheck],
    *,
    symbolic_baseline: bool = False,
) -> dict[str, Any]:
    """Classify overall verification status into verified, numerical_support, partial, or inconclusive."""
    passed_checks = [c for c in checks if c.passed is True]
    failed_checks = [c for c in checks if c.passed is False]
    inconclusive_checks = [c for c in checks if c.passed is None]

    symbolic_passed = any(
        c.check_type in ("symbolic", "substitution") and c.passed is True for c in checks
    )
    numerical_passed = any(
        c.check_type in ("numerical", "cross_method") and c.passed is True for c in checks
    )

    discrepancy_detected = len(failed_checks) > 0

    if discrepancy_detected:
        status = "partial" if passed_checks else "inconclusive"
        verified = False
        summary = (
            "Discrepancy detected: some checks passed while others failed."
            if passed_checks
            else "Discrepancy detected: verification checks refuted the proposed result."
        )
    elif symbolic_passed or (symbolic_baseline and numerical_passed):
        status = "verified"
        verified = True
        summary = "Result is supported by exact symbolic verification."
    elif numerical_passed:
        status = "numerical_support"
        verified = True
        summary = "Result is supported by numerical residual/cross-method checks (not a formal symbolic proof)."
    elif inconclusive_checks or not checks:
        status = "inconclusive"
        verified = False
        summary = "Verification checks were inconclusive or not applicable for this operation."
    else:
        status = "inconclusive"
        verified = False
        summary = "No decisive verification checks ran."

    return {
        "status": status,
        "verified": verified,
        "discrepancy_detected": discrepancy_detected,
        "summary": summary,
        "checks": [c.to_dict() for c in checks],
    }
