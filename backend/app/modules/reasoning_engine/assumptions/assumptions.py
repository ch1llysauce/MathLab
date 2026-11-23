"""Assumption normalization and implicit domain constraint extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from app.modules.math_engine.parser.safe_parser import format_sympy_expr


@dataclass(frozen=True)
class DomainConstraint:
    """Represents a mathematical domain condition or restriction."""

    expression: str
    condition: str
    reason: str
    source: str = "inferred"


@dataclass
class AssumptionContext:
    """Normalized user assumptions and inferred domain constraints."""

    declared: dict[str, str] = field(default_factory=dict)
    constraints: list[DomainConstraint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "declared": dict(self.declared),
            "constraints": [
                {
                    "expression": c.expression,
                    "condition": c.condition,
                    "reason": c.reason,
                    "source": c.source,
                }
                for c in self.constraints
            ],
            "notes": list(self.notes),
        }


def analyze_assumptions(
    parsed_expr: sp.Basic | sp.Eq | None,
    assumptions: dict[str, str] | None = None,
    *,
    is_matrix: bool = False,
) -> AssumptionContext:
    """Extract declared assumptions and infer domain constraints from a parsed expression."""
    declared = {k: v.strip().lower() for k, v in (assumptions or {}).items()}
    constraints: list[DomainConstraint] = []
    notes: list[str] = []

    if is_matrix or parsed_expr is None:
        if declared:
            notes.append("User-declared symbol assumptions are applied to matrix entries.")
        return AssumptionContext(declared=declared, constraints=constraints, notes=notes)

    target = (parsed_expr.lhs - parsed_expr.rhs) if isinstance(parsed_expr, sp.Eq) else parsed_expr

    # Check denominators (negative powers)
    seen_denoms: set[str] = set()
    for node in sp.preorder_traversal(target):
        if isinstance(node, sp.Pow):
            base, exp = node.args
            if exp.is_number and exp.is_real and exp < 0:
                denom_str = format_sympy_expr(base)
                if denom_str not in seen_denoms and base.free_symbols:
                    seen_denoms.add(denom_str)
                    constraints.append(
                        DomainConstraint(
                            expression=denom_str,
                            condition=f"{denom_str} != 0",
                            reason="Denominator must be nonzero to avoid division by zero.",
                        )
                    )
            elif isinstance(exp, sp.Rational) and exp.q % 2 == 0 and base.free_symbols:
                base_str = format_sympy_expr(base)
                constraints.append(
                    DomainConstraint(
                        expression=base_str,
                        condition=f"{base_str} >= 0 (over reals)",
                        reason="Even-root radicand must be non-negative for real-valued results.",
                    )
                )

        if isinstance(node, sp.log) and node.args and node.args[0].free_symbols:
            arg_str = format_sympy_expr(node.args[0])
            constraints.append(
                DomainConstraint(
                    expression=arg_str,
                    condition=f"{arg_str} > 0 (over reals)",
                    reason="Logarithm argument must be strictly positive on the real principal branch.",
                )
            )

    free_vars = sorted(sym.name for sym in target.free_symbols)
    undeclared = [v for v in free_vars if v not in declared]
    if undeclared:
        notes.append(
            f"No explicit domain assumption provided for {', '.join(undeclared)}; SymPy treats undeclared symbols as general complex/symbolic unless restricted."
        )

    return AssumptionContext(declared=declared, constraints=constraints, notes=notes)
