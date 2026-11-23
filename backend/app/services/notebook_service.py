"""Service layer coordinating notebook persistence, invalidation, and execution."""

from __future__ import annotations

from typing import Any, Protocol
import uuid

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.notebook import NotebookCellModel, NotebookModel
from app.modules.notebook_engine.dependencies import recompute_dependencies_and_invalidate
from app.modules.notebook_engine.executor import execute_notebook
from app.repositories.notebook_repository import NotebookRepository
from app.repositories.postgres_notebook_repository import PostgresNotebookRepository
from app.schemas.notebook import (
    CellInputSchema,
    CellResultSchema,
    NotebookCellSchema,
    NotebookCreateRequest,
    NotebookExecuteRequest,
    NotebookExecuteResponseSchema,
    NotebookResponseSchema,
    NotebookSummarySchema,
    NotebookUpdateRequest,
    VariableBindingSchema,
)


class NotebookRepositoryProtocol(Protocol):
    def list_notebooks(self) -> list[dict[str, Any]]: ...
    def get_notebook(self, notebook_id: str) -> NotebookModel | None: ...
    def save_notebook(self, notebook: NotebookModel) -> NotebookModel: ...
    def record_history(self, notebook_id: str, snapshot: dict[str, Any]) -> str: ...
    def list_history(self, notebook_id: str) -> list[dict[str, Any]]: ...


def get_notebook_repository() -> NotebookRepositoryProtocol:
    """Return PostgreSQL repository when DATABASE_URL is configured, otherwise local SQLite."""
    if settings.database_url:
        return PostgresNotebookRepository(settings.database_url)
    return NotebookRepository(settings.notebook_db_path)


def _to_cell_models(notebook_id: str, inputs: list[CellInputSchema]) -> list[NotebookCellModel]:
    return [
        NotebookCellModel(
            id=item.id or str(uuid.uuid4()),
            notebook_id=notebook_id,
            position=idx,
            cell_type=item.cell_type,
            operation=item.operation,
            expression=item.expression,
            variable=item.variable,
            assign_to=item.assign_to,
            assumptions=dict(item.assumptions),
            options=dict(item.options),
            status="idle" if item.cell_type == "math" else "valid",
        )
        for idx, item in enumerate(inputs)
    ]


def _to_notebook_response(nb: NotebookModel) -> NotebookResponseSchema:
    return NotebookResponseSchema(
        id=nb.id,
        title=nb.title,
        mode=nb.mode,  # type: ignore[arg-type]
        created_at=nb.created_at,
        updated_at=nb.updated_at,
        cells=[
            NotebookCellSchema(
                id=c.id,
                notebook_id=c.notebook_id,
                position=c.position,
                cell_type=c.cell_type,  # type: ignore[arg-type]
                operation=c.operation,
                expression=c.expression,
                variable=c.variable,
                assign_to=c.assign_to,
                assumptions=c.assumptions,
                options=c.options,
                status=c.status,  # type: ignore[arg-type]
                depends_on=c.depends_on,
                error_message=c.error_message,
                result=(
                    CellResultSchema(
                        result_text=c.result.result_text,
                        result_latex=c.result.result_latex,
                        metadata=c.result.metadata,
                        reasoning=c.result.reasoning,
                        verification=c.result.verification,
                        executed_at=c.result.executed_at,
                    )
                    if c.result is not None
                    else None
                ),
            )
            for c in sorted(nb.cells, key=lambda x: x.position)
        ],
        variables={
            k: VariableBindingSchema(
                symbol_name=v.symbol_name,
                value_expr=v.value_expr,
                value_latex=v.value_latex,
                cell_id=v.cell_id,
                assumptions=v.assumptions,
            )
            for k, v in nb.variables.items()
        },
    )


def list_notebooks(repo: NotebookRepositoryProtocol) -> list[NotebookSummarySchema]:
    return [NotebookSummarySchema(**row) for row in repo.list_notebooks()]


def create_notebook(repo: NotebookRepositoryProtocol, request: NotebookCreateRequest) -> NotebookResponseSchema:
    notebook_id = str(uuid.uuid4())
    cells = _to_cell_models(notebook_id, request.cells)
    cells = recompute_dependencies_and_invalidate([], cells)
    notebook = NotebookModel(
        id=notebook_id,
        title=request.title,
        mode=request.mode,
        cells=cells,
    )
    saved = repo.save_notebook(notebook)
    return _to_notebook_response(saved)


def get_notebook_details(repo: NotebookRepositoryProtocol, notebook_id: str) -> NotebookResponseSchema:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    return _to_notebook_response(notebook)


def update_notebook(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    request: NotebookUpdateRequest,
) -> NotebookResponseSchema:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")

    if request.title is not None:
        notebook.title = request.title
    if request.mode is not None:
        notebook.mode = request.mode
    if request.cells is not None:
        new_cells = _to_cell_models(notebook_id, request.cells)
        notebook.cells = recompute_dependencies_and_invalidate(notebook.cells, new_cells)

    saved = repo.save_notebook(notebook)
    return _to_notebook_response(saved)


def run_notebook_execution(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    request: NotebookExecuteRequest,
) -> NotebookExecuteResponseSchema:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")

    summary = execute_notebook(
        notebook,
        only_stale=request.only_stale,
        up_to_cell_id=request.up_to_cell_id,
    )
    saved = repo.save_notebook(summary.notebook)
    response_nb = _to_notebook_response(saved)
    history_id = repo.record_history(
        notebook_id,
        {
            "executed_cell_ids": summary.executed_cell_ids,
            "skipped_cell_ids": summary.skipped_cell_ids,
            "notebook": response_nb.model_dump(),
        },
    )

    return NotebookExecuteResponseSchema(
        notebook=response_nb,
        executed_cell_ids=summary.executed_cell_ids,
        skipped_cell_ids=summary.skipped_cell_ids,
        history_id=history_id,
    )
