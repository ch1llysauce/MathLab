"""Pydantic schemas for mathematical computation endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class ComputeRequest(BaseModel):
    """Request payload for executing a whitelisted mathematical operation."""

    operation: str = Field(..., min_length=1, description="Approved operation name or alias.")
    expression: str | None = Field(
        default=None,
        description="Mathematical expression or equation (required for non-matrix operations).",
    )
    variable: str | None = Field(default=None, description="Target variable name.")
    assumptions: dict[str, str] | None = Field(
        default=None,
        description="Optional symbol assumptions (e.g. {'x': 'real'}).",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific options (e.g. bounds, matrix, precision, bracket).",
    )
    include_reasoning: bool = Field(
        default=True,
        description="Include M2 reasoning analysis metadata in the response.",
    )
    include_verification: bool = Field(
        default=True,
        description="Include M3 verification summary in the response.",
    )


class ComputeMetadata(BaseModel):
    """Execution metadata returned with a computation result."""

    domain: str
    method: str
    details: dict[str, Any] = Field(default_factory=dict)


class ComputeResponse(BaseModel):
    """Structured response from POST /api/v1/compute."""

    operation: str
    input: str | None = None
    result: str
    latex: str
    metadata: ComputeMetadata
    reasoning: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None


class OperationInfo(BaseModel):
    """Metadata describing a supported operation in the registry."""

    name: str
    domain: str
    description: str
    aliases: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Standard error payload."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Consistent error envelope returned by API handlers."""

    error: ErrorDetail
