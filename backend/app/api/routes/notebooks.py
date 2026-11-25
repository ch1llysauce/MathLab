"""Notebook API routes for CRUD and sequential execution."""

from fastapi import APIRouter, Body, Depends, Query, Response, status

from app.api.dependencies.auth import AuthenticatedUser, get_optional_user
from app.schemas.notebook import (
    NotebookCreateRequest,
    NotebookExecuteRequest,
    NotebookExecuteResponseSchema,
    NotebookHistoryEntrySchema,
    NotebookResponseSchema,
    NotebookStatelessExecuteRequest,
    NotebookSummarySchema,
    NotebookUpdateRequest,
)
from app.services.notebook_service import (
    NotebookRepositoryProtocol,
    create_notebook,
    delete_notebook_by_id,
    execute_stateless_notebook,
    export_notebook,
    get_notebook_details,
    get_notebook_repository,
    list_notebook_history,
    list_notebooks,
    run_notebook_execution,
    update_notebook,
)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("", response_model=list[NotebookSummarySchema])
def get_all_notebooks(
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> list[NotebookSummarySchema]:
    """Retrieve all saved notebooks visible to the active user."""
    return list_notebooks(repo, user=user)


@router.post("", response_model=NotebookResponseSchema, status_code=status.HTTP_201_CREATED)
def create_new_notebook(
    request: NotebookCreateRequest,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> NotebookResponseSchema:
    """Create a new computational notebook."""
    return create_notebook(repo, request, user=user)


@router.post("/execute-stateless", response_model=NotebookExecuteResponseSchema)
def execute_stateless(
    request: NotebookStatelessExecuteRequest,
) -> NotebookExecuteResponseSchema:
    """Execute guest/local notebook cells sequentially without database persistence."""
    return execute_stateless_notebook(request)


@router.get("/{notebook_id}", response_model=NotebookResponseSchema)
def get_notebook(
    notebook_id: str,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> NotebookResponseSchema:
    """Retrieve a single notebook with cells, variables, and results."""
    return get_notebook_details(repo, notebook_id, user=user)


@router.put("/{notebook_id}", response_model=NotebookResponseSchema)
def put_notebook(
    notebook_id: str,
    request: NotebookUpdateRequest,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> NotebookResponseSchema:
    """Update notebook metadata or cells, invalidating dependent downstream cells."""
    return update_notebook(repo, notebook_id, request, user=user)


@router.post("/{notebook_id}/execute", response_model=NotebookExecuteResponseSchema)
def execute_notebook_cells(
    notebook_id: str,
    request: NotebookExecuteRequest | None = Body(default=None),
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> NotebookExecuteResponseSchema:
    """Execute notebook cells sequentially with shared variable context."""
    return run_notebook_execution(repo, notebook_id, request or NotebookExecuteRequest(), user=user)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    notebook_id: str,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> Response:
    """Delete a notebook and its dependent cells/results."""
    delete_notebook_by_id(repo, notebook_id, user=user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{notebook_id}/export")
def get_notebook_export(
    notebook_id: str,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> dict[str, str]:
    """Export a notebook as Markdown or structured JSON."""
    return export_notebook(repo, notebook_id, export_format=format, user=user)


@router.get("/{notebook_id}/history", response_model=list[NotebookHistoryEntrySchema])
def get_notebook_history(
    notebook_id: str,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
    user: AuthenticatedUser | None = Depends(get_optional_user),
) -> list[NotebookHistoryEntrySchema]:
    """Retrieve execution history snapshots for a notebook."""
    return list_notebook_history(repo, notebook_id, user=user)
