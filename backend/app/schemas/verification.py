"""Pydantic schemas for the M3 Verification and Analysis endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class VerificationCheckRequest(BaseModel):
    """Request payload for verifying a mathematical computation result."""

    operation: str = Field(..., min_length=1, description="Operation name or alias.")
    result: str = Field(..., min_length=1, description="Proposed computational result string.")
    expression: str | None = Field(
        default=None,
        description="Original mathematical expression or equation.",
    )
    variable: str | None = Field(default=None, description="Target variable name.")
    assumptions: dict[str, str] | None = Field(
        default=None,
        description="Optional symbol assumptions.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific options (e.g. bounds, matrix, details).",
    )


class VerificationCheckItem(BaseModel):
    """Individual verification check result."""

    check_type: str
    name: str
    passed: bool | None = None
    message: str
    residual: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class VerificationCheckResponse(BaseModel):
    """Structured response from POST /api/v1/verification/check."""

    status: Literal["verified", "numerical_support", "partial", "inconclusive"]
    verified: bool
    discrepancy_detected: bool
    summary: str
    checks: list[VerificationCheckItem] = Field(default_factory=list)
