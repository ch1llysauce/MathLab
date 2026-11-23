"""Service layer for M3 mathematical verification."""

from __future__ import annotations

from app.modules.verification_engine.verifier import verify_computation
from app.schemas.verification import VerificationCheckRequest, VerificationCheckResponse


def check_verification(request: VerificationCheckRequest) -> VerificationCheckResponse:
    """Run verification checks for a computation result."""
    raw = verify_computation(
        operation=request.operation,
        result=request.result,
        expression=request.expression,
        variable=request.variable,
        assumptions=request.assumptions,
        options=request.options,
    )
    return VerificationCheckResponse(**raw)
