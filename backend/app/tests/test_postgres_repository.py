"""Unit tests for PostgresNotebookRepository and repository factory switching."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import uuid

from app.core.config import settings
from app.models.notebook import CellResult, NotebookCellModel, NotebookModel, VariableBinding
from app.repositories.notebook_repository import NotebookRepository
from app.repositories.postgres_notebook_repository import PostgresNotebookRepository
from app.services.notebook_service import get_notebook_repository


def test_get_notebook_repository_switches_based_on_database_url(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    assert isinstance(get_notebook_repository(), NotebookRepository)

    monkeypatch.setattr(settings, "database_url", "postgresql://postgres:pw@localhost:5432/postgres")
    repo = get_notebook_repository()
    assert isinstance(repo, PostgresNotebookRepository)
    assert repo.database_url == "postgresql://postgres:pw@localhost:5432/postgres"


def test_postgres_repository_roundtrip_sql_and_hydration():
    nb_id = str(uuid.uuid4())
    cell_id = str(uuid.uuid4())
    now_dt = datetime(2026, 11, 23, 14, 0, tzinfo=timezone.utc)

    mock_cur = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    repo = PostgresNotebookRepository("postgresql://postgres:pw@localhost:5432/postgres")

    # 1. Test save_notebook inserts notebook, cell, computation result, and variable binding
    mock_cur.fetchone.return_value = None
    notebook = NotebookModel(
        id=nb_id,
        title="Postgres Test",
        mode="computational",
        cells=[
            NotebookCellModel(
                id=cell_id,
                notebook_id=nb_id,
                position=0,
                operation="assign",
                expression="a = 5",
                status="valid",
                result=CellResult(result_text="a = 5", result_latex="a = 5"),
            )
        ],
        variables={
            "a": VariableBinding(
                symbol_name="a",
                value_expr="5",
                value_latex="5",
                cell_id=cell_id,
            )
        },
    )

    with patch("app.repositories.postgres_notebook_repository.psycopg.connect", return_value=mock_conn):
        saved = repo.save_notebook(notebook)
        assert saved.id == nb_id
        executed_sql = " ".join(call.args[0] for call in mock_cur.execute.call_args_list)
        assert "INSERT INTO notebooks" in executed_sql
        assert "INSERT INTO notebook_cells" in executed_sql
        assert "INSERT INTO computation_results" in executed_sql
        assert "INSERT INTO variables_and_assumptions" in executed_sql

    # 2. Test get_notebook hydrates NotebookModel properly
    mock_cur.reset_mock()
    mock_cur.fetchone.return_value = {
        "id": nb_id,
        "title": "Postgres Test",
        "mode": "computational",
        "created_at": now_dt,
        "updated_at": now_dt,
    }
    mock_cur.fetchall.side_effect = [
        [
            {
                "id": cell_id,
                "notebook_id": nb_id,
                "position": 0,
                "cell_type": "math",
                "operation": "assign",
                "expression": "a = 5",
                "variable": None,
                "assign_to": None,
                "assumptions_json": {},
                "options_json": {},
                "status": "valid",
                "depends_on": [],
                "error_message": None,
            }
        ],
        [
            {
                "cell_id": cell_id,
                "result_text": "a = 5",
                "result_latex": "a = 5",
                "metadata_json": {"domain": "notebook"},
                "reasoning_json": None,
                "verification_json": {"status": "verified", "verified": True},
                "executed_at": now_dt,
            }
        ],
        [
            {
                "symbol_name": "a",
                "value_expr": "5",
                "value_latex": "5",
                "cell_id": cell_id,
                "assumptions_json": {},
            }
        ],
    ]

    with patch("app.repositories.postgres_notebook_repository.psycopg.connect", return_value=mock_conn):
        loaded = repo.get_notebook(nb_id)
        assert loaded is not None
        assert loaded.id == nb_id
        assert loaded.cells[0].result is not None
        assert loaded.cells[0].result.result_text == "a = 5"
        assert loaded.variables["a"].value_expr == "5"
