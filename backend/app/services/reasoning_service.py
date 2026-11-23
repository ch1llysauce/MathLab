"""Service layer for mathematical problem reasoning and method selection."""

from __future__ import annotations

from app.modules.reasoning_engine.analyzer import analyze_mathematical_problem
from app.schemas.reasoning import ReasoningAnalyzeRequest, ReasoningAnalyzeResponse


def analyze_problem(request: ReasoningAnalyzeRequest) -> ReasoningAnalyzeResponse:
    """Classify the problem, check applicability rules, and select a method."""
    raw = analyze_mathematical_problem(
        operation=request.operation,
        expression=request.expression,
        variable=request.variable,
        assumptions=request.assumptions,
        options=request.options,
    )
    return ReasoningAnalyzeResponse(**raw)
