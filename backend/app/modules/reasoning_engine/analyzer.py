"""Unified entry point for the M2 Intelligent Mathematical Reasoning Engine."""

from __future__ import annotations

from typing import Any

from app.core.security import run_with_timeout
from app.modules.reasoning_engine.assumptions.assumptions import analyze_assumptions
from app.modules.reasoning_engine.classifier.classifier import classify_problem
from app.modules.reasoning_engine.method_selector.selector import select_method
from app.modules.reasoning_engine.rules.rules import evaluate_rules


def _run_analysis(
    operation: str | None,
    expression: str | None,
    variable: str | None,
    assumptions: dict[str, str] | None,
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    classification = classify_problem(
        operation=operation,
        expression=expression,
        variable=variable,
        options=options,
        assumptions=assumptions,
    )
    assumption_ctx = analyze_assumptions(
        classification.parsed_expr,
        assumptions=assumptions,
        is_matrix=(classification.domain == "linear_algebra"),
    )
    rules = evaluate_rules(
        operation=operation,
        classification=classification,
        variable=variable,
        options=options,
    )
    selection = select_method(
        operation=operation,
        classification=classification,
        rules=rules,
        options=options,
    )
    return {
        "classification": classification.to_dict(),
        "assumptions": assumption_ctx.to_dict(),
        "rules": [r.to_dict() for r in rules],
        "selection": selection.to_dict(),
    }


def analyze_mathematical_problem(
    operation: str | None = None,
    expression: str | None = None,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run bounded deterministic classification, assumption, rule, and method analysis."""
    return run_with_timeout(
        _run_analysis,
        operation,
        expression,
        variable,
        assumptions,
        options,
    )
