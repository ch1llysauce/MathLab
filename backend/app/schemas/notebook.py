"""Pydantic schemas for M4 Computational Notebook endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class CellInputSchema(BaseModel):
    """Input definition for creating or updating a notebook cell."""

    id: str | None = Field(default=None, description="Existing cell UUID; generated if omitted.")
    cell_type: Literal["math", "markdown", "ai"] = Field(default="math")
    operation: str | None = Field(default=None, description="Approved math operation or 'assign'.")
    expression: str | None = Field(default=None, description="Mathematical expression, equation, or markdown content.")
    variable: str | None = Field(default=None, description="Target variable for solve/calculus ops.")
    assign_to: str | None = Field(default=None, description="Optional symbol name to bind the cell's result to.")
    assumptions: dict[str, str] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class CellResultSchema(BaseModel):
    """Latest structured execution output for a cell."""

    result_text: str
    result_latex: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    reasoning: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    executed_at: str


class NotebookCellSchema(BaseModel):
    """Full notebook cell state returned by API endpoints."""

    id: str
    notebook_id: str
    position: int
    cell_type: Literal["math", "markdown", "ai"]
    operation: str | None = None
    expression: str | None = None
    variable: str | None = None
    assign_to: str | None = None
    assumptions: dict[str, str] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    status: Literal["idle", "valid", "stale", "error"]
    depends_on: list[str] = Field(default_factory=list)
    error_message: str | None = None
    result: CellResultSchema | None = None


class VariableBindingSchema(BaseModel):
    """Active variable binding inside a notebook."""

    symbol_name: str
    value_expr: str
    value_latex: str
    cell_id: str
    assumptions: dict[str, str] = Field(default_factory=dict)


class NotebookCreateRequest(BaseModel):
    """Request payload for creating a notebook."""

    title: str = Field(..., min_length=1, max_length=200)
    mode: Literal["computational", "learning"] = Field(default="computational")
    cells: list[CellInputSchema] = Field(default_factory=list)


class NotebookUpdateRequest(BaseModel):
    """Request payload for updating notebook metadata and/or cells."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    mode: Literal["computational", "learning"] | None = Field(default=None)
    cells: list[CellInputSchema] | None = Field(default=None)


class NotebookExecuteRequest(BaseModel):
    """Options for executing notebook cells sequentially."""

    only_stale: bool = Field(
        default=False,
        description="When true, re-execute only stale/idle/error cells while keeping valid upstream bindings.",
    )
    up_to_cell_id: str | None = Field(
        default=None,
        description="Optional cell ID at which to stop sequential execution.",
    )


class StatelessCellInputSchema(CellInputSchema):
    """Cell payload for stateless (guest/local) sequential execution."""

    status: Literal["idle", "valid", "stale", "error"] = Field(default="idle")
    depends_on: list[str] = Field(default_factory=list)
    error_message: str | None = None
    result: CellResultSchema | None = None


class NotebookStatelessExecuteRequest(NotebookExecuteRequest):
    """Request payload for running notebook cells without database persistence."""

    id: str | None = None
    title: str = Field(default="Guest Notebook", min_length=1, max_length=200)
    mode: Literal["computational", "learning"] = Field(default="computational")
    created_at: str | None = None
    cells: list[StatelessCellInputSchema] = Field(default_factory=list)
    variables: dict[str, VariableBindingSchema] = Field(default_factory=dict)


class NotebookSummarySchema(BaseModel):
    """Summary item for notebook listing."""

    id: str
    title: str
    mode: Literal["computational", "learning"]
    cell_count: int
    created_at: str
    updated_at: str


class NotebookResponseSchema(BaseModel):
    """Complete notebook response including cells and variable bindings."""

    id: str
    title: str
    mode: Literal["computational", "learning"]
    created_at: str
    updated_at: str
    cells: list[NotebookCellSchema] = Field(default_factory=list)
    variables: dict[str, VariableBindingSchema] = Field(default_factory=dict)


class NotebookExecuteResponseSchema(BaseModel):
    """Response from executing notebook cells."""

    notebook: NotebookResponseSchema
    executed_cell_ids: list[str] = Field(default_factory=list)
    skipped_cell_ids: list[str] = Field(default_factory=list)
    history_id: str


class NotebookHistoryEntrySchema(BaseModel):
    """Saved execution history snapshot for a notebook."""

    id: str
    notebook_id: str
    created_at: str
    executed_cell_ids: list[str] = Field(default_factory=list)
    skipped_cell_ids: list[str] = Field(default_factory=list)
    notebook: NotebookResponseSchema | None = None
