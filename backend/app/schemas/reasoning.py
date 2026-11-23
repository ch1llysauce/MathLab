"""Pydantic schemas for the M2 Intelligent Mathematical Reasoning endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class ReasoningAnalyzeRequest(BaseModel):
    """Request payload for classifying a problem and selecting an applicable method."""

    operation: str | None = Field(
        default=None,
        description="Optional intended operation; inferred automatically when omitted.",
    )
    expression: str | None = Field(
        default=None,
        description="Mathematical expression or equation.",
    )
    variable: str | None = Field(default=None, description="Target variable name.")
    assumptions: dict[str, str] | None = Field(
        default=None,
        description="Optional symbol assumptions (e.g. {'x': 'real'}).",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific options (e.g. bounds, matrix, bracket).",
    )


class ProblemClassification(BaseModel):
    """Problem classification summary."""

    domain: str
    problem_type: str
    variables: list[str] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)


class DomainConstraintSchema(BaseModel):
    """Inferred or declared mathematical domain constraint."""

    expression: str
    condition: str
    reason: str
    source: str


class AssumptionSummary(BaseModel):
    """Normalized assumptions and domain constraints."""

    declared: dict[str, str] = Field(default_factory=dict)
    constraints: list[DomainConstraintSchema] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RuleCheckSchema(BaseModel):
    """Applicability rule check outcome."""

    rule_id: str
    description: str
    passed: bool
    severity: str
    message: str


class MethodCandidateSchema(BaseModel):
    """Candidate computational method evaluation."""

    operation: str
    method: str
    applicable: bool
    reason: str


class MethodSelectionSchema(BaseModel):
    """Selected method and explanation."""

    recommended_operation: str
    recommended_method: str
    applicable: bool
    rationale: str
    candidates: list[MethodCandidateSchema] = Field(default_factory=list)


class ReasoningAnalyzeResponse(BaseModel):
    """Structured response from POST /api/v1/reasoning/analyze."""

    classification: ProblemClassification
    assumptions: AssumptionSummary
    rules: list[RuleCheckSchema] = Field(default_factory=list)
    selection: MethodSelectionSchema
