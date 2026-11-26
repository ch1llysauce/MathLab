"""Grounded AI explanation orchestrator combining M1, M2, and M3 outputs."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.exceptions import InvalidExpressionError
from app.modules.ai_engine.llm_client import (
    call_llm_chat,
    is_llm_configured,
    parse_llm_json_object,
)
from app.modules.ai_engine.nl_parser import interpret_natural_language
from app.modules.math_engine.registry.registry import OPERATION_REGISTRY
from app.modules.reasoning_engine.analyzer import analyze_mathematical_problem
from app.modules.verification_engine.verifier import verify_computation

_EXPLAIN_SYSTEM_PROMPT = (
    "You are MathLab's mathematical tutor. NEVER invent or alter mathematical answers — "
    "rely strictly on the verified computation, variable, options (e.g. point, lower, upper, order), "
    "and result provided in the JSON context. "
    "Return a JSON object ONLY with keys: "
    "'steps' (an ordered list of 3-4 objects {'title': string, 'content': string} showing the actual "
    "mathematical procedure, substitutions, and algebraic/calculus rules used to get the result) and "
    "'summary' (1-2 clear plain-text sentences explaining WHY the final result holds mathematically). "
    "Do NOT talk about internal software classification or verification logs unless relevant to a mathematical constraint. "
    "Use clean plain text and Unicode math (x³, ·, √, →) with no Markdown headings, tables, or LaTeX delimiters like \\[ \\]."
)


def _build_pedagogical_hint(
    operation: str,
    expression: str | None,
    variable: str | None,
    options: dict[str, Any],
) -> str:
    var = variable or "x"
    if operation == "differentiate":
        return f"Differentiate `{expression}` term-by-term with respect to `{var}` using standard symbolic derivative rules (power, product, quotient, and chain rules)."
    if operation == "partial_derivative":
        return f"Hold all independent symbols constant except `{var}` when computing the partial derivative of `{expression}`."
    if operation == "integrate":
        lower, upper = options.get("lower"), options.get("upper")
        if lower is not None and upper is not None:
            return f"Find an antiderivative F({var}) of `{expression}` and evaluate F({upper}) - F({lower}) via the Fundamental Theorem of Calculus."
        return f"Compute a symbolic antiderivative of `{expression}` with respect to `{var}` and include the integration constant + C."
    if operation == "limit":
        point = options.get("point", "0")
        return f"Inspect behavior of `{expression}` as `{var}` approaches `{point}`, resolving indeterminate forms algebraically or via L'Hopital's rule."
    if operation == "taylor_series":
        point = options.get("point", "0")
        order = options.get("order", 5)
        return f"Expand `{expression}` using derivatives evaluated at `{var} = {point}` up to truncation order {order}."
    if operation == "solve":
        return f"Isolate `{var}` symbolically in `{expression}` by factoring or solving the algebraic equation."
    if operation == "solve_ode":
        return f"Solve the differential equation `{expression}` symbolically and apply any declared initial conditions."
    if operation.startswith("matrix_") or operation == "linear_system_solve":
        return "Check matrix dimensions and linear independence/invertibility preconditions before extracting the exact algebraic result."
    return f"Transform `{expression}` symbolically under `{operation}` while preserving mathematical equivalence."


def _build_grounded_steps(
    *,
    operation: str,
    expression: str | None,
    variable: str | None,
    options: dict[str, Any],
    result: str,
    latex: str,
    reasoning: dict[str, Any],
    verification: dict[str, Any],
    mode: str,
) -> list[dict[str, str]]:
    cls = reasoning["classification"]
    sel = reasoning["selection"]
    assump = reasoning["assumptions"]

    constraints = assump.get("constraints") or []
    constraint_summary = (
        "; ".join(c["condition"] for c in constraints)
        if constraints
        else "No special domain singularities or branch restrictions detected."
    )
    pedagogical_hint = _build_pedagogical_hint(operation, expression, variable, options)

    steps = [
        {
            "title": "Problem Recognition",
            "content": (
                f"Identified a {cls['problem_type'].replace('_', ' ')} in {cls['domain']} "
                f"(operation: '{operation}')."
                if mode == "computational"
                else f"First, we classify the input as a {cls['problem_type'].replace('_', ' ')} within {cls['domain']} so we know which mathematical rules apply."
            ),
        },
        {
            "title": "Method Selection",
            "content": sel["rationale"],
        },
        {
            "title": "Mathematical Assumptions",
            "content": constraint_summary,
        },
        {
            "title": "Computed Result",
            "content": (
                f"Result: {result}"
                if mode == "computational"
                else f"{pedagogical_hint} Applying {sel['recommended_method']} yields `{result}` (LaTeX: `{latex}`)."
            ),
        },
        {
            "title": "Verification & Reliability",
            "content": f"[{verification['status']}] {verification['summary']}",
        },
    ]
    return steps


def _clean_llm_text(text: str) -> str:
    """Normalize escaped newlines from LLM JSON while preserving LaTeX commands like \\neq."""
    normalized = re.sub(r"\\n(?![a-zA-Z])", "\n", text.replace("\r\n", "\n"))
    return normalized.strip()


def _build_deterministic_summary(
    *,
    operation: str,
    expression: str | None,
    result: str,
    reasoning: dict[str, Any],
    verification: dict[str, Any],
    mode: str,
) -> str:
    sel = reasoning["selection"]
    cls = reasoning["classification"]
    if mode == "learning":
        target = f"`{expression}`" if expression else "the given matrix"
        return (
            f"To perform **{operation}** on {target}, MathLab identified this as a "
            f"**{cls['problem_type'].replace('_', ' ')}** and selected **{sel['recommended_method']}**. "
            f"The grounded result is **`{result}`**, with verification status **`{verification['status']}`** "
            f"({verification['summary']})."
        )
    return (
        f"Operation `{operation}` ({sel['recommended_method']}) produced `{result}` "
        f"[verification: {verification['status']}]."
    )


def generate_grounded_explanation(
    *,
    prompt: str | None = None,
    operation: str | None = None,
    expression: str | None = None,
    variable: str | None = None,
    assumptions: dict[str, str] | None = None,
    options: dict[str, Any] | None = None,
    mode: str = "learning",
) -> dict[str, Any]:
    """Interpret optional NL prompt, run M1+M2+M3 engines, and build a grounded explanation."""
    interpretation_source = "structured_request"
    resolved_op = operation
    resolved_expr = expression
    resolved_var = variable
    resolved_opts = dict(options or {})

    if prompt and prompt.strip() and not resolved_op:
        interpreted = interpret_natural_language(prompt)
        resolved_op = interpreted["operation"]
        resolved_expr = interpreted["expression"]
        resolved_var = resolved_var or interpreted.get("variable")
        resolved_opts = {**interpreted.get("options", {}), **resolved_opts}
        interpretation_source = interpreted["interpretation_source"]

    if not resolved_op:
        raise InvalidExpressionError("Provide either a natural-language 'prompt' or a structured 'operation'.")

    # 1. Execute M1 computation
    raw = OPERATION_REGISTRY.execute(
        resolved_op,
        {
            "operation": resolved_op,
            "expression": resolved_expr,
            "variable": resolved_var,
            "assumptions": assumptions,
            "options": resolved_opts,
        },
    )
    details = dict(raw.get("details") or {})
    method = str(details.pop("method", raw["canonical_operation"]))

    # 2. Run M2 reasoning
    reasoning = analyze_mathematical_problem(
        operation=raw["canonical_operation"],
        expression=resolved_expr,
        variable=resolved_var,
        assumptions=assumptions,
        options=resolved_opts,
    )

    # 3. Run M3 verification
    verification = verify_computation(
        operation=raw["canonical_operation"],
        result=raw["result"],
        expression=resolved_expr,
        variable=resolved_var,
        assumptions=assumptions,
        options={**resolved_opts, "details": details},
    )

    steps = _build_grounded_steps(
        operation=raw["canonical_operation"],
        expression=resolved_expr,
        variable=resolved_var,
        options=resolved_opts,
        result=raw["result"],
        latex=raw["latex"],
        reasoning=reasoning,
        verification=verification,
        mode=mode,
    )

    explanation_source = "deterministic_grounded"
    summary = _build_deterministic_summary(
        operation=raw["canonical_operation"],
        expression=resolved_expr,
        result=raw["result"],
        reasoning=reasoning,
        verification=verification,
        mode=mode,
    )

    if is_llm_configured():
        grounded_context = {
            "mode": mode,
            "operation": raw["canonical_operation"],
            "expression": resolved_expr,
            "variable": resolved_var,
            "options": resolved_opts,
            "result": raw["result"],
            "latex": raw["latex"],
            "method": method,
            "reasoning": reasoning,
            "verification": verification,
        }
        llm_text = call_llm_chat(
            _EXPLAIN_SYSTEM_PROMPT,
            f"Show the step-by-step mathematical procedure and why the result holds in '{mode}' mode:\n{json.dumps(grounded_context)}",
        )
        if llm_text:
            parsed_llm = parse_llm_json_object(llm_text)
            if parsed_llm and isinstance(parsed_llm.get("summary"), str):
                raw_steps = parsed_llm.get("steps")
                if isinstance(raw_steps, list):
                    cleaned_steps = [
                        {
                            "title": _clean_llm_text(str(s["title"])),
                            "content": _clean_llm_text(str(s["content"])),
                        }
                        for s in raw_steps
                        if isinstance(s, dict) and s.get("title") and s.get("content")
                    ]
                    if cleaned_steps:
                        steps = cleaned_steps
                if parsed_llm["summary"].strip():
                    summary = _clean_llm_text(parsed_llm["summary"])
            else:
                summary = _clean_llm_text(llm_text)
            explanation_source = "llm_grounded"

    return {
        "mode": mode,
        "interpretation_source": interpretation_source,
        "explanation_source": explanation_source,
        "operation": raw["canonical_operation"],
        "expression": resolved_expr,
        "variable": resolved_var,
        "options": resolved_opts,
        "result": raw["result"],
        "latex": raw["latex"],
        "summary": summary,
        "steps": steps,
        "reasoning": reasoning,
        "verification": verification,
    }
