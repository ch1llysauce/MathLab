"""AI and educational integration API routes."""

from fastapi import APIRouter

from app.schemas.ai import AIExplainRequest, AIExplainResponse, WorkedExampleSchema
from app.services.ai_service import explain_math, get_worked_examples

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain", response_model=AIExplainResponse)
def explain(request: AIExplainRequest) -> AIExplainResponse:
    """Interpret a natural-language math prompt and return a verified, grounded explanation."""
    return explain_math(request)


@router.get("/examples", response_model=list[WorkedExampleSchema])
def list_examples() -> list[WorkedExampleSchema]:
    """List curated guided worked examples for Learning Mode."""
    return get_worked_examples()
