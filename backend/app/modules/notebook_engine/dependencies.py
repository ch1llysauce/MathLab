"""Cell dependency graph computation and upstream edit invalidation."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidExpressionError
from app.modules.math_engine.parser.safe_parser import (
    ALLOWED_CONSTANTS,
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)
from app.models.notebook import NotebookCellModel

_EQUATION_OPERATIONS = {"solve", "solve_ode", "root_find"}


def _is_matrix_operation(op: str) -> bool:
    return op.startswith("matrix_") or op == "linear_system_solve"


def split_inline_assignment(cell: NotebookCellModel) -> tuple[str | None, str | None]:
    """Extract an optional leading `var = expr` binding for non-equation math cells."""
    if cell.cell_type != "math" or not cell.expression:
        return None, cell.expression

    op = (cell.operation or "simplify").strip().lower()
    raw = cell.expression.strip()
    if _is_matrix_operation(op) or op in _EQUATION_OPERATIONS or "=" not in raw:
        return None, cell.expression

    parts = raw.split("=")
    if len(parts) != 2:
        return None, cell.expression

    lhs, rhs = parts[0].strip(), parts[1].strip()
    if not lhs or not rhs or lhs in ALLOWED_CONSTANTS:
        return None, cell.expression
    if cell.variable and lhs == cell.variable.strip():
        return None, cell.expression

    try:
        sym = parse_symbol(lhs)
    except InvalidExpressionError:
        return None, cell.expression

    return sym.name, rhs


def resolve_defined_variable(cell: NotebookCellModel) -> str | None:
    """Return the variable name bound by a cell, if any."""
    if cell.cell_type != "math":
        return None
    if cell.assign_to and cell.assign_to.strip():
        return cell.assign_to.strip()
    inline_var, _ = split_inline_assignment(cell)
    return inline_var


def extract_referenced_symbols(cell: NotebookCellModel) -> set[str]:
    """Safely extract variable names referenced by a cell's expression and string bounds."""
    if cell.cell_type != "math":
        return set()

    refs: set[str] = set()
    op = (cell.operation or "").strip().lower()

    if _is_matrix_operation(op):
        def _collect_entry_symbols(entry: Any) -> None:
            try:
                refs.update(sym.name for sym in parse_math_expression(str(entry)).free_symbols)
            except Exception:
                pass

        opts = cell.options or {}
        for key in ("matrix", "matrix_a", "matrix_b"):
            mat = opts.get(key)
            if isinstance(mat, list):
                for row in mat:
                    if isinstance(row, list):
                        for entry in row:
                            _collect_entry_symbols(entry)
        vec = opts.get("vector")
        if isinstance(vec, list):
            for entry in vec:
                _collect_entry_symbols(entry)
        return refs

    _, expr_candidate = split_inline_assignment(cell)
    if expr_candidate and expr_candidate.strip():
        expr_text = expr_candidate.strip()
        try:
            parsed = parse_math_input(expr_text) if "=" in expr_text else parse_math_expression(expr_text)
            refs.update(sym.name for sym in parsed.free_symbols)
        except Exception:
            pass

    for bound_key in ("lower", "upper", "point"):
        val = (cell.options or {}).get(bound_key)
        if isinstance(val, str) and val.strip():
            try:
                refs.update(sym.name for sym in parse_math_expression(val).free_symbols)
            except Exception:
                pass

    # If the cell explicitly targets a calculus/solve variable and doesn't define it, keep note;
    # note: a cell referencing its own `assign_to` still reads the upstream variable if it existed.
    if cell.variable and cell.variable.strip() in refs and op in ("differentiate", "diff", "derivative", "integrate", "int", "integral", "limit", "solve", "root_find", "nsolve"):
        refs.discard(cell.variable.strip())

    return refs


def _cell_definition_signature(cell: NotebookCellModel) -> tuple[Any, ...]:
    return (
        cell.cell_type,
        (cell.operation or "").strip().lower() or None,
        (cell.expression or "").strip() or None,
        (cell.variable or "").strip() or None,
        (cell.assign_to or "").strip() or None,
        tuple(sorted((cell.assumptions or {}).items())),
        repr(sorted((cell.options or {}).items())),
    )


def recompute_dependencies_and_invalidate(
    old_cells: list[NotebookCellModel],
    new_cells: list[NotebookCellModel],
) -> list[NotebookCellModel]:
    """Compute dependency links and mark edited or downstream-dependent cells as stale."""
    old_by_id = {c.id: c for c in old_cells}

    # Detect variables whose definitions changed or were removed compared to old notebook state
    old_var_sources: dict[str, tuple[str, tuple[Any, ...]]] = {}
    for c in sorted(old_cells, key=lambda x: x.position):
        var = resolve_defined_variable(c)
        if var:
            old_var_sources[var] = (c.id, _cell_definition_signature(c))

    active_producers: dict[str, str] = {}  # var_name -> upstream cell_id
    invalidated_ids: set[str] = set()
    dirty_vars: set[str] = set()

    # Check if any previously defined variable was deleted or moved to a different cell
    new_defined_vars = {
        resolve_defined_variable(c): c.id for c in new_cells if resolve_defined_variable(c) is not None
    }
    for old_var in old_var_sources:
        if old_var not in new_defined_vars:
            dirty_vars.add(old_var)

    for cell in sorted(new_cells, key=lambda x: x.position):
        refs = extract_referenced_symbols(cell)
        direct_deps = [
            active_producers[var]
            for var in sorted(refs)
            if var in active_producers and active_producers[var] != cell.id
        ]
        # Deduplicate while preserving order
        cell.depends_on = list(dict.fromkeys(direct_deps))

        old_cell = old_by_id.get(cell.id)
        if old_cell is None:
            is_changed = True
        else:
            is_changed = (
                _cell_definition_signature(old_cell) != _cell_definition_signature(cell)
                or old_cell.depends_on != cell.depends_on
            )

        upstream_dirty = any(dep_id in invalidated_ids for dep_id in cell.depends_on) or any(
            var in dirty_vars for var in refs
        )

        if cell.cell_type != "math":
            cell.status = "valid"
            cell.error_message = None
        elif is_changed or upstream_dirty:
            invalidated_ids.add(cell.id)
            if old_cell is not None:
                cell.result = old_cell.result
            cell.status = "stale" if (old_cell is not None and old_cell.status != "idle") else "idle"
            cell.error_message = None
        else:
            cell.status = old_cell.status
            cell.result = old_cell.result
            cell.error_message = old_cell.error_message
            if cell.status in ("stale", "error"):
                invalidated_ids.add(cell.id)

        defined_var = resolve_defined_variable(cell)
        if defined_var:
            if cell.id in invalidated_ids:
                dirty_vars.add(defined_var)
            active_producers[defined_var] = cell.id

    return new_cells
