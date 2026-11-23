"""Integration and security tests for the M4 Computational Notebook Engine."""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.repositories.notebook_repository import NotebookRepository
from app.services.notebook_service import get_notebook_repository


@pytest.fixture()
def isolated_client(tmp_path):
    db_file = tmp_path / "test_notebooks.db"
    repo = NotebookRepository(db_file)
    app.dependency_overrides[get_notebook_repository] = lambda: repo
    try:
        yield TestClient(app), repo
    finally:
        app.dependency_overrides.clear()


class TestNotebookExecutionAndDependencies:
    def test_sequential_execution_shares_variables_and_persists(self, isolated_client):
        client, repo = isolated_client

        create_resp = client.post(
            "/api/v1/notebooks",
            json={
                "title": "Calculus Exploration",
                "mode": "computational",
                "cells": [
                    {"operation": "assign", "expression": "f = x^3 + 2*x"},
                    {"operation": "differentiate", "expression": "f", "variable": "x", "assign_to": "df"},
                    {"operation": "simplify", "expression": "df + 5"},
                ],
            },
        )
        assert create_resp.status_code == 201
        nb = create_resp.json()
        nb_id = nb["id"]
        assert len(nb["cells"]) == 3

        exec_resp = client.post(f"/api/v1/notebooks/{nb_id}/execute", json={})
        assert exec_resp.status_code == 200
        exec_body = exec_resp.json()
        cells = exec_body["notebook"]["cells"]

        assert cells[0]["status"] == "valid"
        assert cells[0]["result"]["result_text"] == "f = x^3 + 2*x"

        assert cells[1]["status"] == "valid"
        assert cells[1]["depends_on"] == [cells[0]["id"]]
        assert cells[1]["result"]["result_text"] == "3*x^2 + 2"
        assert cells[1]["result"]["verification"]["verified"] is True

        assert cells[2]["status"] == "valid"
        assert cells[2]["depends_on"] == [cells[1]["id"]]
        assert cells[2]["result"]["result_text"] == "3*x^2 + 7"

        assert exec_body["notebook"]["variables"]["f"]["value_expr"] == "x^3 + 2*x"
        assert exec_body["notebook"]["variables"]["df"]["value_expr"] == "3*x^2 + 2"

        # Verify clean reload from SQLite persistence and history snapshot
        reloaded = client.get(f"/api/v1/notebooks/{nb_id}")
        assert reloaded.status_code == 200
        assert reloaded.json()["cells"][2]["result"]["result_text"] == "3*x^2 + 7"
        assert len(repo.list_history(nb_id)) == 1

    def test_editing_earlier_cell_invalidates_only_dependent_downstream_cells(self, isolated_client):
        client, _ = isolated_client

        create_resp = client.post(
            "/api/v1/notebooks",
            json={
                "title": "Dependency Invalidation Test",
                "cells": [
                    {"id": "c1", "operation": "assign", "expression": "a = 2"},
                    {"id": "c2", "operation": "simplify", "expression": "a * x + 1"},
                    {"id": "c3", "operation": "factor", "expression": "x^2 - 9"},
                ],
            },
        )
        nb_id = create_resp.json()["id"]
        client.post(f"/api/v1/notebooks/{nb_id}/execute", json={})

        # Edit cell 1 (a = 2 -> a = 5); cell 2 depends on a, cell 3 is independent
        update_resp = client.put(
            f"/api/v1/notebooks/{nb_id}",
            json={
                "cells": [
                    {"id": "c1", "operation": "assign", "expression": "a = 5"},
                    {"id": "c2", "operation": "simplify", "expression": "a * x + 1"},
                    {"id": "c3", "operation": "factor", "expression": "x^2 - 9"},
                ]
            },
        )
        assert update_resp.status_code == 200
        updated_cells = update_resp.json()["cells"]
        assert updated_cells[0]["status"] == "stale"
        assert updated_cells[1]["status"] == "stale"
        assert updated_cells[2]["status"] == "valid"

        # Execute only stale cells and confirm c3 was skipped while c1, c2 updated
        reexec = client.post(f"/api/v1/notebooks/{nb_id}/execute", json={"only_stale": True})
        assert reexec.status_code == 200
        reexec_body = reexec.json()
        assert reexec_body["executed_cell_ids"] == ["c1", "c2"]
        assert reexec_body["skipped_cell_ids"] == ["c3"]
        assert reexec_body["notebook"]["cells"][1]["result"]["result_text"] == "5*x + 1"


class TestNotebookCRUDAndSecurity:
    def test_list_and_404_not_found(self, isolated_client):
        client, _ = isolated_client
        client.post("/api/v1/notebooks", json={"title": "Notebook A", "cells": []})
        listed = client.get("/api/v1/notebooks")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["title"] == "Notebook A"

        missing = client.get("/api/v1/notebooks/nonexistent-id")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "NOT_FOUND"

    def test_rejects_arbitrary_python_in_cell_and_blocks_downstream(self, isolated_client):
        client, _ = isolated_client
        create_resp = client.post(
            "/api/v1/notebooks",
            json={
                "title": "Security Notebook",
                "cells": [
                    {"id": "bad", "operation": "assign", "expression": "x = __import__('os').system('ls')"},
                    {"id": "down", "operation": "simplify", "expression": "x + 1"},
                ],
            },
        )
        nb_id = create_resp.json()["id"]
        exec_resp = client.post(f"/api/v1/notebooks/{nb_id}/execute", json={})
        assert exec_resp.status_code == 200
        cells = exec_resp.json()["notebook"]["cells"]
        assert cells[0]["status"] == "error"
        assert "Forbidden token" in cells[0]["error_message"]
        assert cells[1]["status"] == "stale"
