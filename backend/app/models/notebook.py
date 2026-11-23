"""Domain dataclasses for notebooks, cells, variables, and execution results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CellResult:
    """Persisted computation output for a notebook cell."""

    result_text: str
    result_latex: str
    metadata: dict[str, Any] = field(default_factory=dict)
    reasoning: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    executed_at: str = ""


@dataclass
class NotebookCellModel:
    """Structured notebook cell without arbitrary Python execution."""

    id: str
    notebook_id: str
    position: int
    cell_type: str = "math"  # "math" | "markdown" | "ai"
    operation: str | None = None
    expression: str | None = None
    variable: str | None = None
    assign_to: str | None = None
    assumptions: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    status: str = "idle"  # "idle" | "valid" | "stale" | "error"
    depends_on: list[str] = field(default_factory=list)
    error_message: str | None = None
    result: CellResult | None = None


@dataclass
class VariableBinding:
    """Notebook-scoped mathematical variable binding and assumptions."""

    symbol_name: str
    value_expr: str
    value_latex: str
    cell_id: str
    assumptions: dict[str, str] = field(default_factory=dict)


@dataclass
class NotebookModel:
    """Top-level computational notebook aggregate."""

    id: str
    title: str
    mode: str = "computational"
    created_at: str = ""
    updated_at: str = ""
    cells: list[NotebookCellModel] = field(default_factory=list)
    variables: dict[str, VariableBinding] = field(default_factory=dict)
