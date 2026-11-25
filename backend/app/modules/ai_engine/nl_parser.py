"""Natural-language mathematical prompt interpreter with strict validation."""

from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import InvalidExpressionError
from app.core.security import validate_expression_bounds
from app.modules.ai_engine.llm_client import call_llm_chat, is_llm_configured, parse_llm_json_object
from app.modules.math_engine.registry.registry import OPERATION_REGISTRY

_NL_TRANSLATION_PROMPT = (
    "You translate mathematical natural-language requests into a single JSON object with keys: "
    "'operation' (one of: simplify, expand, factor, solve, differentiate, integrate, limit, "
    "partial_derivative, taylor_series, solve_ode, linear_system_solve, numerical_eval, root_find, "
    "numerical_integrate, matrix_add, matrix_multiply, matrix_transpose, matrix_determinant, "
    "matrix_inverse, matrix_rank, matrix_rref, matrix_eigenvalues, matrix_eigenvectors), "
    "'expression' (string or null), 'variable' (string or null), and 'options' (object). Output JSON only."
)

_DEFINITE_INT_RE = re.compile(
    r"^(?:integrate|find\s+the\s+integral\s+of|compute\s+the\s+integral\s+of)\s+(.+?)\s+from\s+([^\s]+)\s+to\s+([^\s]+?)(?:\s+(?:with\s+respect\s+to|wrt|d)\s*([a-zA-Z][a-zA-Z0-9_]*))?$",
    re.IGNORECASE,
)
_LIMIT_RE = re.compile(
    r"^(?:find\s+the\s+)?limit\s+(?:of\s+(.+?)\s+as\s+([a-zA-Z][a-zA-Z0-9_]*)\s*(?:->|approaches)\s*([^\s]+)|as\s+([a-zA-Z][a-zA-Z0-9_]*)\s*(?:->|approaches)\s*([^\s]+)\s+of\s+(.+?))$",
    re.IGNORECASE,
)
_ROOT_RE = re.compile(
    r"^(?:find\s+(?:a\s+)?root\s+of)\s+(.+?)\s+(?:on|in)\s*\[\s*([^,\]]+)\s*,\s*([^\]]+)\s*\]$",
    re.IGNORECASE,
)
_DIFF_LEIBNIZ_RE = re.compile(
    r"^d/d([a-zA-Z][a-zA-Z0-9_]*)\s+(?:of\s+)?(.+)$",
    re.IGNORECASE,
)
_INT_DX_RE = re.compile(
    r"^(?:integrate|find\s+the\s+(?:indefinite\s+)?integral\s+of|antiderivative\s+of)\s+(.+?)\s+d([a-zA-Z][a-zA-Z0-9_]*)$",
    re.IGNORECASE,
)
_SIMPLE_OP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(?:partial\s+derivative\s+of)\s+(.+?)\s+(?:with\s+respect\s+to|wrt)\s+([a-zA-Z][a-zA-Z0-9_]*)$", re.IGNORECASE), "partial_derivative"),
    (re.compile(r"^(?:maclaurin\s+(?:series|expansion)\s+(?:of|for))\s+(.+?)(?:\s+order\s+(\d+))?$", re.IGNORECASE), "maclaurin_series"),
    (re.compile(r"^(?:taylor\s+(?:series|expansion)\s+(?:of|for))\s+(.+?)(?:\s+(?:around|at)\s+([^\s]+))?(?:\s+order\s+(\d+))?$", re.IGNORECASE), "taylor_series"),
    (re.compile(r"^(?:solve\s+ode|ode)\s*:?\s*(.+)$", re.IGNORECASE), "solve_ode"),
    (re.compile(r"^(?:differentiate|diff|find\s+the\s+derivative\s+of|derivative\s+of)\s+(.+?)(?:\s+(?:with\s+respect\s+to|wrt)\s+([a-zA-Z][a-zA-Z0-9_]*))?$", re.IGNORECASE), "differentiate"),
    (re.compile(r"^(?:integrate|find\s+the\s+(?:indefinite\s+)?integral\s+of|antiderivative\s+of)\s+(.+?)(?:\s+(?:with\s+respect\s+to|wrt)\s+([a-zA-Z][a-zA-Z0-9_]*))?$", re.IGNORECASE), "integrate"),
    (re.compile(r"^(?:(?:find\s+(?:the\s+)?roots\s+of|roots\s+of)|solve(?:\s+for\s+([a-zA-Z][a-zA-Z0-9_]*))?\s*:?)\s+(.+)$", re.IGNORECASE), "solve"),
    (re.compile(r"^(?:factor|factorize)\s+(.+)$", re.IGNORECASE), "factor"),
    (re.compile(r"^(?:expand)\s+(.+)$", re.IGNORECASE), "expand"),
    (re.compile(r"^(?:simplify)\s+(.+)$", re.IGNORECASE), "simplify"),
    (re.compile(r"^(?:evaluate|calculate|compute|approx(?:imate)?)\s+(.+)$", re.IGNORECASE), "numerical_eval"),
]


def _try_deterministic_parse(prompt: str) -> dict[str, Any] | None:
    cleaned = prompt.strip().rstrip("?.")

    m_def = _DEFINITE_INT_RE.match(cleaned)
    if m_def:
        expr, lower, upper, var = m_def.groups()
        return {
            "operation": "integrate",
            "expression": expr.strip(),
            "variable": var,
            "options": {"lower": lower.strip(), "upper": upper.strip()},
        }

    m_lim = _LIMIT_RE.match(cleaned)
    if m_lim:
        expr1, var1, pt1, var2, pt2, expr2 = m_lim.groups()
        expr = expr1 or expr2
        var = var1 or var2
        pt = pt1 or pt2
        return {
            "operation": "limit",
            "expression": expr.strip(),
            "variable": var.strip(),
            "options": {"point": pt.strip()},
        }

    m_root = _ROOT_RE.match(cleaned)
    if m_root:
        expr, a, b = m_root.groups()
        return {
            "operation": "root_find",
            "expression": expr.strip(),
            "variable": None,
            "options": {"bracket": [float(a), float(b)]},
        }

    m_leibniz = _DIFF_LEIBNIZ_RE.match(cleaned)
    if m_leibniz:
        var, expr = m_leibniz.groups()
        return {
            "operation": "differentiate",
            "expression": expr.strip(),
            "variable": var.strip(),
            "options": {},
        }

    m_int_dx = _INT_DX_RE.match(cleaned)
    if m_int_dx:
        expr, var = m_int_dx.groups()
        return {
            "operation": "integrate",
            "expression": expr.strip(),
            "variable": var.strip(),
            "options": {},
        }

    for pattern, op in _SIMPLE_OP_PATTERNS:
        m = pattern.match(cleaned)
        if not m:
            continue
        if op == "solve":
            var, expr = m.groups()
            return {"operation": "solve", "expression": expr.strip(), "variable": var, "options": {}}
        if op in ("differentiate", "integrate", "partial_derivative"):
            expr, var = m.groups()
            return {"operation": op, "expression": expr.strip(), "variable": var, "options": {}}
        if op == "maclaurin_series":
            expr, order_str = m.groups()
            opts: dict[str, Any] = {"point": "0"}
            if order_str:
                opts["order"] = int(order_str)
            return {"operation": "taylor_series", "expression": expr.strip(), "variable": None, "options": opts}
        if op == "taylor_series":
            expr, pt, order_str = m.groups()
            opts = {}
            if pt:
                opts["point"] = pt.strip()
            if order_str:
                opts["order"] = int(order_str)
            return {"operation": "taylor_series", "expression": expr.strip(), "variable": None, "options": opts}
        return {"operation": op, "expression": m.group(1).strip(), "variable": None, "options": {}}

    return None


def interpret_natural_language(prompt: str) -> dict[str, Any]:
    """Translate a natural-language prompt into a validated structured math request."""
    cleaned = validate_expression_bounds(prompt)

    candidate = _try_deterministic_parse(cleaned)
    source = "deterministic_nlp"

    if candidate is None and is_llm_configured():
        raw_llm = call_llm_chat(_NL_TRANSLATION_PROMPT, cleaned)
        llm_json = parse_llm_json_object(raw_llm)
        if llm_json:
            candidate = {
                "operation": llm_json.get("operation"),
                "expression": llm_json.get("expression"),
                "variable": llm_json.get("variable"),
                "options": llm_json.get("options") if isinstance(llm_json.get("options"), dict) else {},
            }
            source = "llm_translated"

    if not candidate or not candidate.get("operation") or not candidate.get("expression"):
        raise InvalidExpressionError(
            "Could not interpret natural-language request into an approved mathematical operation. "
            "Try phrases like 'differentiate x^3 + 2*x', 'integrate x^2 from 0 to 3', or 'solve x^2 - 5*x + 6 = 0'."
        )

    # Validate proposed operation against the approved whitelist before execution
    spec = OPERATION_REGISTRY.resolve(str(candidate["operation"]))
    validate_expression_bounds(str(candidate["expression"]))

    return {
        "operation": spec.name,
        "expression": str(candidate["expression"]),
        "variable": candidate.get("variable"),
        "options": candidate.get("options") or {},
        "interpretation_source": source,
    }
