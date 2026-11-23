"""Notebook API routes for CRUD and sequential execution."""

from fastapi import APIRouter, Depends, status

from app.schemas.notebook import (
    NotebookCreateRequest,
    NotebookExecuteRequest,
    NotebookExecuteResponseSchema,
    NotebookResponseSchema,
    NotebookSummarySchema,
    NotebookUpdateRequest,
)
from app.services.notebook_service import (
    NotebookRepositoryProtocol,
    create_notebook,
    get_notebook_details,
    get_notebook_repository,
    list_notebooks,
    run_notebook_execution,
    update_notebook,
)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("", response_model=list[NotebookSummarySchema])
def get_all_notebooks(
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
) -> list[NotebookSummarySchema]:
    """Retrieve all saved notebooks."""
    return list_notebooks(repo)


@router.post("", response_model=NotebookResponseSchema, status_code=status.HTTP_201_CREATED)
def create_new_notebook(
    request: NotebookCreateRequest,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
) -> NotebookResponseSchema:
    """Create a new computational notebook."""
    return create_notebook(repo, request)


@router.get("/{notebook_id}", response_model=NotebookResponseSchema)
def get_notebook(
    notebook_id: str,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
) -> NotebookResponseSchema:
    """Retrieve a single notebook with cells, variables, and results."""
    return get_notebook_details(repo, notebook_id)


@router.put("/{notebook_id}", response_model=NotebookResponseSchema)
def put_notebook(
    notebook_id: str,
    request: NotebookUpdateRequest,
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
) -> NotebookResponseSchema:
    """Update notebook metadata or cells, invalidating dependent downstream cells."""
    return update_notebook(repo, notebook_id, request)


@router.post("/{notebook_id}/execute", response_model=NotebookExecuteResponseSchema)
def execute_notebook_cells(
    notebook_id: str,
    request: NotebookExecuteRequest = NotebookExecuteRequest(),
    repo: NotebookRepositoryProtocol = Depends(get_notebook_repository),
) -> NotebookExecuteResponseSchema:
    """Execute notebook cells sequentially with shared variable context."""
    return run_notebook_execution(repo, notebook_id, request)
