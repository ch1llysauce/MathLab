"""Verification API routes."""

from fastapi import APIRouter

from app.schemas.verification import VerificationCheckRequest, VerificationCheckResponse
from app.services.verification_service import check_verification

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/check", response_model=VerificationCheckResponse)
def verify_result(request: VerificationCheckRequest) -> VerificationCheckResponse:
    """Verify a mathematical result via symbolic, numerical, substitution, and cross-method checks."""
    return check_verification(request)
