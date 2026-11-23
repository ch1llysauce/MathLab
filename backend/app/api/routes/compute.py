"""Computation API routes."""

from fastapi import APIRouter

from app.schemas.compute import ComputeRequest, ComputeResponse, OperationInfo
from app.services.compute_service import execute_computation, list_supported_operations

router = APIRouter(prefix="/compute", tags=["computation"])


@router.get("/operations", response_model=list[OperationInfo])
def get_operations() -> list[OperationInfo]:
    """List all approved mathematical operations."""
    return list_supported_operations()


@router.post("", response_model=ComputeResponse)
def compute(request: ComputeRequest) -> ComputeResponse:
    """Execute a validated mathematical operation."""
    return execute_computation(request)
