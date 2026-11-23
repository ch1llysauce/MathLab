"""Computation service coordinating mathematical engine execution."""

from __future__ import annotations

from app.modules.math_engine.registry.registry import OPERATION_REGISTRY
from app.modules.reasoning_engine.analyzer import analyze_mathematical_problem
from app.modules.verification_engine.verifier import verify_computation
from app.schemas.compute import ComputeMetadata, ComputeRequest, ComputeResponse, OperationInfo


def list_supported_operations() -> list[OperationInfo]:
    """Return all whitelisted operations from the math engine registry."""
    return [OperationInfo(**item) for item in OPERATION_REGISTRY.list_operations()]


def execute_computation(request: ComputeRequest) -> ComputeResponse:
    """Validate and dispatch a computation request through the operation registry."""
    payload = request.model_dump()
    raw = OPERATION_REGISTRY.execute(request.operation, payload)
    details = dict(raw.get("details") or {})
    method = str(details.pop("method", raw["canonical_operation"]))

    reasoning = (
        analyze_mathematical_problem(
            operation=raw["canonical_operation"],
            expression=request.expression,
            variable=request.variable,
            assumptions=request.assumptions,
            options=request.options,
        )
        if request.include_reasoning
        else None
    )

    verification = (
        verify_computation(
            operation=raw["canonical_operation"],
            result=raw["result"],
            expression=request.expression,
            variable=request.variable,
            assumptions=request.assumptions,
            options={**request.options, "details": details},
        )
        if request.include_verification
        else None
    )

    return ComputeResponse(
        operation=raw["canonical_operation"],
        input=request.expression,
        result=raw["result"],
        latex=raw["latex"],
        metadata=ComputeMetadata(
            domain=raw["domain"],
            method=method,
            details=details,
        ),
        reasoning=reasoning,
        verification=verification,
    )
