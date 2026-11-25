"""Service layer for M6 AI explanations and worked examples."""

from __future__ import annotations

from app.modules.ai_engine.explainer import generate_grounded_explanation
from app.modules.ai_engine.worked_examples import WORKED_EXAMPLES
from app.schemas.ai import AIExplainRequest, AIExplainResponse, WorkedExampleSchema


def explain_math(request: AIExplainRequest) -> AIExplainResponse:
    """Interpret NL input if given, run M1+M2+M3 engines, and return a grounded explanation."""
    raw = generate_grounded_explanation(
        prompt=request.prompt,
        operation=request.operation,
        expression=request.expression,
        variable=request.variable,
        assumptions=request.assumptions,
        options=request.options,
        mode=request.mode,
    )
    return AIExplainResponse(**raw)


def get_worked_examples() -> list[WorkedExampleSchema]:
    """Return curated worked examples for Learning Mode."""
    return [WorkedExampleSchema(**item) for item in WORKED_EXAMPLES]
