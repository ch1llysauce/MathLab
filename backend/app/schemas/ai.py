"""Pydantic schemas for M6 AI and Educational Integration endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AIExplainRequest(BaseModel):
    """Request payload for natural-language interpretation and grounded explanation."""

    prompt: str | None = Field(
        default=None,
        description="Natural-language mathematical request (e.g. 'differentiate x^3 + 2*x').",
    )
    operation: str | None = Field(
        default=None,
        description="Optional structured operation when prompt is not used.",
    )
    expression: str | None = Field(default=None)
    variable: str | None = Field(default=None)
    assumptions: dict[str, str] | None = Field(default=None)
    options: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["computational", "learning"] = Field(default="learning")


class ExplanationStepSchema(BaseModel):
    """Single structured step in a grounded mathematical walkthrough."""

    title: str
    content: str


class AIExplainResponse(BaseModel):
    """Structured response from POST /api/v1/ai/explain."""

    mode: Literal["computational", "learning"]
    interpretation_source: str
    explanation_source: str
    operation: str
    expression: str | None = None
    variable: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    result: str
    latex: str
    summary: str
    steps: list[ExplanationStepSchema] = Field(default_factory=list)
    reasoning: dict[str, Any]
    verification: dict[str, Any]


class WorkedExampleSchema(BaseModel):
    """Curated worked example for Learning Mode."""

    id: str
    title: str
    domain: str
    difficulty: str
    description: str
    prompt: str | None = None
    operation: str
    expression: str | None = None
    variable: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
