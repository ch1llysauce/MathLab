"""Sequential controlled notebook execution engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from app.core.exceptions import InvalidExpressionError, MathLabError
from app.models.notebook import (
    CellResult,
    NotebookCellModel,
    NotebookModel,
    VariableBinding,
)
from app.modules.math_engine.parser.safe_parser import (
    format_sympy_expr,
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)
from app.modules.math_engine.registry.registry import OPERATION_REGISTRY
from app.modules.notebook_engine.dependencies import (
    extract_referenced_symbols,
    resolve_defined_variable,
    split_inline_assignment,
)
from app.modules.reasoning_engine.analyzer import analyze_mathematical_problem
from app.modules.verification_engine.verifier import verify_computation
from app.repositories.notebook_repository import utc_now_iso


@dataclass
class ExecutionSummary:
    """Result summary from executing a notebook."""

    notebook: NotebookModel
    executed_cell_ids: list[str] = field(default_factory=list)
    skipped_cell_ids: list[str] = field(default_factory=list)


def _substitute_expr_text(
    text: str,
    active_vars: dict[str, VariableBinding],
    *,
    excluded_var: str | None = None,
    assumptions: dict[str, str] | None = None,
) -> tuple[str, sp.Basic | sp.Eq]:
    parsed = parse_math_input(text, assumptions=assumptions) if "=" in text else parse_math_expression(text, assumptions=assumptions)
    subs_map: dict[sp.Symbol, sp.Basic] = {}
    for sym in parsed.free_symbols:
        if sym.name == excluded_var:
            continue
        binding = active_vars.get(sym.name)
        if binding is not None:
            subs_map[sym] = parse_math_expression(binding.value_expr, assumptions=assumptions)

    if not subs_map:
        return text, parsed

    if isinstance(parsed, sp.Eq):
        substituted = sp.Eq(parsed.lhs.subs(subs_map), parsed.rhs.subs(subs_map))
        return f"{format_sympy_expr(substituted.lhs)} = {format_sympy_expr(substituted.rhs)}", substituted

    substituted_expr = parsed.subs(subs_map)
    return format_sympy_expr(substituted_expr), substituted_expr


def _substitute_options(
    options: dict[str, Any],
    active_vars: dict[str, VariableBinding],
    assumptions: dict[str, str] | None,
) -> dict[str, Any]:
    resolved = dict(options)
    for key in ("lower", "upper", "point"):
        val = resolved.get(key)
        if isinstance(val, str) and val.strip():
            new_str, _ = _substitute_expr_text(val, active_vars, assumptions=assumptions)
            resolved[key] = new_str
    return resolved


def _execute_assign_cell(
    cell: NotebookCellModel,
    active_vars: dict[str, VariableBinding],
    merged_assumptions: dict[str, str],
) -> tuple[CellResult, VariableBinding]:
    expr_raw = (cell.expression or "").strip()
    if not expr_raw:
        raise InvalidExpressionError("Assignment cell requires an expression.")

    if cell.assign_to and cell.assign_to.strip():
        target_sym = parse_symbol(cell.assign_to.strip(), assumptions=merged_assumptions)
        rhs_raw = expr_raw
    elif "=" in expr_raw:
        parts = expr_raw.split("=")
        if len(parts) != 2:
            raise InvalidExpressionError("Assignment expression must contain exactly one '='.")
        target_sym = parse_symbol(parts[0].strip(), assumptions=merged_assumptions)
        rhs_raw = parts[1].strip()
    else:
        raise InvalidExpressionError("Assignment cell requires 'assign_to' or 'var = expr' syntax.")

    _, substituted_rhs = _substitute_expr_text(rhs_raw, active_vars, assumptions=merged_assumptions)
    if isinstance(substituted_rhs, sp.Eq):
        raise InvalidExpressionError("Assignment RHS cannot be an equation.")

    val_str = format_sympy_expr(substituted_rhs)
    val_latex = sp.latex(substituted_rhs)

    binding = VariableBinding(
        symbol_name=target_sym.name,
        value_expr=val_str,
        value_latex=val_latex,
        cell_id=cell.id,
        assumptions=dict(cell.assumptions),
    )
    result = CellResult(
        result_text=f"{target_sym.name} = {val_str}",
        result_latex=f"{sp.latex(target_sym)} = {val_latex}",
        metadata={"domain": "notebook", "method": "variable_assignment", "variable": target_sym.name},
        reasoning=None,
        verification={"status": "verified", "verified": True, "discrepancy_detected": False, "summary": "Variable binding recorded.", "checks": []},
        executed_at=utc_now_iso(),
    )
    return result, binding


def execute_notebook(
    notebook: NotebookModel,
    *,
    only_stale: bool = False,
    up_to_cell_id: str | None = None,
) -> ExecutionSummary:
    """Execute notebook cells sequentially while preserving variable context and tracking failures."""
    active_vars: dict[str, VariableBinding] = {}
    active_assumptions: dict[str, str] = {}
    executed_ids: list[str] = []
    skipped_ids: list[str] = []
    failed_cell_ids: set[str] = set()
    active_producers: dict[str, str] = {}

    ordered_cells = sorted(notebook.cells, key=lambda c: c.position)

    for cell in ordered_cells:
        if cell.cell_type != "math":
            cell.status = "valid"
            cell.error_message = None
            skipped_ids.append(cell.id)
            if up_to_cell_id and cell.id == up_to_cell_id:
                break
            continue

        refs = extract_referenced_symbols(cell)
        cell.depends_on = list(
            dict.fromkeys(
                active_producers[var]
                for var in sorted(refs)
                if var in active_producers and active_producers[var] != cell.id
            )
        )

        # If any upstream dependency failed in this run, mark downstream cell stale and stop advancing it
        if any(dep_id in failed_cell_ids for dep_id in cell.depends_on):
            cell.status = "stale"
            cell.error_message = "Blocked by an upstream cell error."
            failed_cell_ids.add(cell.id)
            skipped_ids.append(cell.id)
            if up_to_cell_id and cell.id == up_to_cell_id:
                break
            continue

        if only_stale and cell.status == "valid" and cell.result is not None:
            skipped_ids.append(cell.id)
            defined = resolve_defined_variable(cell)
            if defined and defined in notebook.variables:
                active_vars[defined] = notebook.variables[defined]
            active_assumptions.update(cell.assumptions)
            if defined:
                active_producers[defined] = cell.id
            if up_to_cell_id and cell.id == up_to_cell_id:
                break
            continue

        merged_assumptions = {**active_assumptions, **(cell.assumptions or {})}
        op = (cell.operation or "simplify").strip().lower()

        try:
            if op == "assign":
                cell_res, binding = _execute_assign_cell(cell, active_vars, merged_assumptions)
                active_vars[binding.symbol_name] = binding
                active_assumptions.update(cell.assumptions)
                active_producers[binding.symbol_name] = cell.id
                cell.result = cell_res
                cell.status = "valid"
                cell.error_message = None
                executed_ids.append(cell.id)
            else:
                inline_var, expr_candidate = split_inline_assignment(cell)
                resolved_expr = expr_candidate
                if resolved_expr and resolved_expr.strip():
                    resolved_expr, _ = _substitute_expr_text(
                        resolved_expr,
                        active_vars,
                        excluded_var=cell.variable,
                        assumptions=merged_assumptions,
                    )
                resolved_options = _substitute_options(cell.options or {}, active_vars, merged_assumptions)

                raw = OPERATION_REGISTRY.execute(
                    op,
                    {
                        "operation": op,
                        "expression": resolved_expr,
                        "variable": cell.variable,
                        "assumptions": merged_assumptions or None,
                        "options": resolved_options,
                    },
                )
                details = dict(raw.get("details") or {})
                method = str(details.pop("method", raw["canonical_operation"]))

                reasoning = analyze_mathematical_problem(
                    operation=raw["canonical_operation"],
                    expression=resolved_expr,
                    variable=cell.variable,
                    assumptions=merged_assumptions or None,
                    options=resolved_options,
                )
                verification = verify_computation(
                    operation=raw["canonical_operation"],
                    result=raw["result"],
                    expression=resolved_expr,
                    variable=cell.variable,
                    assumptions=merged_assumptions or None,
                    options={**resolved_options, "details": details},
                )

                cell.result = CellResult(
                    result_text=raw["result"],
                    result_latex=raw["latex"],
                    metadata={"domain": raw["domain"], "method": method, "details": details},
                    reasoning=reasoning,
                    verification=verification,
                    executed_at=utc_now_iso(),
                )
                cell.status = "valid"
                cell.error_message = None
                executed_ids.append(cell.id)

                target_name = (cell.assign_to or "").strip() or inline_var
                if target_name:
                    target_sym = parse_symbol(target_name, assumptions=merged_assumptions)
                    bind_expr = raw["result"].removesuffix(" + C").strip()
                    active_vars[target_sym.name] = VariableBinding(
                        symbol_name=target_sym.name,
                        value_expr=bind_expr,
                        value_latex=raw["latex"],
                        cell_id=cell.id,
                        assumptions=dict(cell.assumptions),
                    )
                    active_producers[target_sym.name] = cell.id

                active_assumptions.update(cell.assumptions)

        except MathLabError as exc:
            cell.status = "error"
            cell.error_message = exc.message
            failed_cell_ids.add(cell.id)
            defined = resolve_defined_variable(cell)
            if defined:
                active_vars.pop(defined, None)
                active_producers[defined] = cell.id

        if up_to_cell_id and cell.id == up_to_cell_id:
            break

    notebook.variables = active_vars
    return ExecutionSummary(
        notebook=notebook,
        executed_cell_ids=executed_ids,
        skipped_cell_ids=skipped_ids,
    )
