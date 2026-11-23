"""Reasoning API routes."""

from fastapi import APIRouter

from app.schemas.reasoning import ReasoningAnalyzeRequest, ReasoningAnalyzeResponse
from app.services.reasoning_service import analyze_problem

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


@router.post("/analyze", response_model=ReasoningAnalyzeResponse)
def analyze(request: ReasoningAnalyzeRequest) -> ReasoningAnalyzeResponse:
    """Classify a mathematical problem, inspect assumptions/rules, and select a method."""
    return analyze_problem(request)
