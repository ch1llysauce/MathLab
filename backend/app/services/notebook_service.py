"""Service layer coordinating notebook persistence, invalidation, and execution."""

from __future__ import annotations

from typing import Any, Protocol
import uuid

from app.api.dependencies.auth import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.notebook import CellResult, NotebookCellModel, NotebookModel, VariableBinding
from app.modules.notebook_engine.dependencies import recompute_dependencies_and_invalidate
from app.modules.notebook_engine.executor import execute_notebook
from app.repositories.notebook_repository import NotebookRepository, utc_now_iso
from app.repositories.postgres_notebook_repository import PostgresNotebookRepository
from app.schemas.notebook import (
    CellInputSchema,
    CellResultSchema,
    NotebookCellSchema,
    NotebookCreateRequest,
    NotebookExecuteRequest,
    NotebookExecuteResponseSchema,
    NotebookHistoryEntrySchema,
    NotebookResponseSchema,
    NotebookStatelessExecuteRequest,
    NotebookSummarySchema,
    NotebookUpdateRequest,
    VariableBindingSchema,
)


class NotebookRepositoryProtocol(Protocol):
    def ensure_user(self, user_id: str, email: str | None) -> None: ...
    def list_notebooks(self, user_id: str | None = None) -> list[dict[str, Any]]: ...
    def get_notebook(self, notebook_id: str) -> NotebookModel | None: ...
    def save_notebook(self, notebook: NotebookModel) -> NotebookModel: ...
    def delete_notebook(self, notebook_id: str) -> bool: ...
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


def _assert_notebook_access(notebook: NotebookModel, user: AuthenticatedUser | None) -> None:
    if notebook.user_id is None:
        return
    if user is None or notebook.user_id != user.id:
        raise ForbiddenError("You do not have permission to access this notebook.")


def list_notebooks(
    repo: NotebookRepositoryProtocol,
    user: AuthenticatedUser | None = None,
) -> list[NotebookSummarySchema]:
    return [NotebookSummarySchema(**row) for row in repo.list_notebooks(user_id=user.id if user else None)]


def create_notebook(
    repo: NotebookRepositoryProtocol,
    request: NotebookCreateRequest,
    user: AuthenticatedUser | None = None,
) -> NotebookResponseSchema:
    notebook_id = str(uuid.uuid4())
    if user is not None:
        repo.ensure_user(user.id, user.email)
    cells = _to_cell_models(notebook_id, request.cells)
    cells = recompute_dependencies_and_invalidate([], cells)
    notebook = NotebookModel(
        id=notebook_id,
        user_id=user.id if user else None,
        title=request.title,
        mode=request.mode,
        cells=cells,
    )
    saved = repo.save_notebook(notebook)
    return _to_notebook_response(saved)


def get_notebook_details(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    user: AuthenticatedUser | None = None,
) -> NotebookResponseSchema:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    _assert_notebook_access(notebook, user)
    return _to_notebook_response(notebook)


def update_notebook(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    request: NotebookUpdateRequest,
    user: AuthenticatedUser | None = None,
) -> NotebookResponseSchema:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    _assert_notebook_access(notebook, user)

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
    user: AuthenticatedUser | None = None,
) -> NotebookExecuteResponseSchema:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    _assert_notebook_access(notebook, user)

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


def execute_stateless_notebook(request: NotebookStatelessExecuteRequest) -> NotebookExecuteResponseSchema:
    """Execute notebook cells sequentially in memory without writing to any database."""
    notebook_id = request.id or str(uuid.uuid4())
    now_iso = utc_now_iso()
    cells = [
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
            status=item.status if item.cell_type == "math" else "valid",
            depends_on=list(item.depends_on),
            error_message=item.error_message,
            result=(
                CellResult(
                    result_text=item.result.result_text,
                    result_latex=item.result.result_latex,
                    metadata=dict(item.result.metadata),
                    reasoning=dict(item.result.reasoning) if item.result.reasoning is not None else None,
                    verification=dict(item.result.verification) if item.result.verification is not None else None,
                    executed_at=item.result.executed_at,
                )
                if item.result is not None
                else None
            ),
        )
        for idx, item in enumerate(request.cells)
    ]
    variables = {
        k: VariableBinding(
            symbol_name=v.symbol_name,
            value_expr=v.value_expr,
            value_latex=v.value_latex,
            cell_id=v.cell_id,
            assumptions=dict(v.assumptions),
        )
        for k, v in request.variables.items()
    }
    notebook = NotebookModel(
        id=notebook_id,
        title=request.title,
        mode=request.mode,
        created_at=request.created_at or now_iso,
        updated_at=now_iso,
        cells=cells,
        variables=variables,
    )
    summary = execute_notebook(
        notebook,
        only_stale=request.only_stale,
        up_to_cell_id=request.up_to_cell_id,
    )
    summary.notebook.updated_at = utc_now_iso()
    return NotebookExecuteResponseSchema(
        notebook=_to_notebook_response(summary.notebook),
        executed_cell_ids=summary.executed_cell_ids,
        skipped_cell_ids=summary.skipped_cell_ids,
        history_id="stateless",
    )


def delete_notebook_by_id(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    user: AuthenticatedUser | None = None,
) -> None:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    _assert_notebook_access(notebook, user)
    repo.delete_notebook(notebook_id)


def list_notebook_history(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    user: AuthenticatedUser | None = None,
) -> list[NotebookHistoryEntrySchema]:
    """Return execution history snapshots for an accessible notebook."""
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    _assert_notebook_access(notebook, user)

    entries: list[NotebookHistoryEntrySchema] = []
    for row in repo.list_history(notebook_id):
        snap = row.get("snapshot") or {}
        nb_payload = snap.get("notebook")
        entries.append(
            NotebookHistoryEntrySchema(
                id=str(row["id"]),
                notebook_id=str(row["notebook_id"]),
                created_at=str(row.get("created_at", "")),
                executed_cell_ids=list(snap.get("executed_cell_ids") or []),
                skipped_cell_ids=list(snap.get("skipped_cell_ids") or []),
                notebook=NotebookResponseSchema(**nb_payload) if isinstance(nb_payload, dict) else None,
            )
        )
    return entries


def export_notebook(
    repo: NotebookRepositoryProtocol,
    notebook_id: str,
    export_format: str = "markdown",
    user: AuthenticatedUser | None = None,
) -> dict[str, str]:
    notebook = repo.get_notebook(notebook_id)
    if notebook is None:
        raise NotFoundError(f"Notebook '{notebook_id}' was not found.")
    _assert_notebook_access(notebook, user)

    nb_schema = _to_notebook_response(notebook)
    safe_slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in nb_schema.title.lower()).strip("_") or "notebook"

    if export_format == "json":
        return {
            "filename": f"{safe_slug}.json",
            "media_type": "application/json",
            "content": nb_schema.model_dump_json(indent=2),
        }

    lines: list[str] = [
        f"# {nb_schema.title}",
        "",
        f"- **Mode:** `{nb_schema.mode}`",
        f"- **Updated:** `{nb_schema.updated_at}`",
        "",
    ]

    if nb_schema.variables:
        lines.append("## Active Variables")
        lines.append("")
        for sym, binding in nb_schema.variables.items():
            lines.append(f"- `{sym} = {binding.value_expr}` (`$${binding.value_latex}$$`)")
        lines.append("")

    lines.append("## Cells")
    lines.append("")
    for idx, cell in enumerate(nb_schema.cells, start=1):
        op_label = cell.operation or cell.cell_type
        lines.append(f"### Cell {idx} · `{op_label}` ({cell.status})")
        lines.append("")
        if cell.expression:
            lines.append(f"Input: `{cell.expression}`")
            lines.append("")
        if cell.error_message:
            lines.append(f"> **Error:** {cell.error_message}")
            lines.append("")
        if cell.result:
            lines.append(f"Output: `{cell.result.result_text}`")
            lines.append("")
            lines.append(f"$$ {cell.result.result_latex} $$")
            lines.append("")
            if cell.result.verification:
                v_status = cell.result.verification.get("status", "inconclusive")
                v_summary = cell.result.verification.get("summary", "")
                lines.append(f"- **Verification:** `{v_status}` — {v_summary}")
                lines.append("")

    return {
        "filename": f"{safe_slug}.md",
        "media_type": "text/markdown",
        "content": "\n".join(lines).strip() + "\n",
    }
