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

        history_resp = client.get(f"/api/v1/notebooks/{nb_id}/history")
        assert history_resp.status_code == 200
        history_items = history_resp.json()
        assert len(history_items) == 1
        assert len(history_items[0]["executed_cell_ids"]) == 3
        assert history_items[0]["notebook"]["id"] == nb_id

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

    def test_export_and_delete_notebook(self, isolated_client):
        client, _ = isolated_client
        create_resp = client.post(
            "/api/v1/notebooks",
            json={
                "title": "Exportable Notebook",
                "cells": [{"operation": "differentiate", "expression": "x^3 + 2*x", "variable": "x"}],
            },
        )
        nb_id = create_resp.json()["id"]
        client.post(f"/api/v1/notebooks/{nb_id}/execute", json={})

        md_resp = client.get(f"/api/v1/notebooks/{nb_id}/export?format=markdown")
        assert md_resp.status_code == 200
        md_body = md_resp.json()
        assert md_body["filename"].endswith(".md")
        assert "# Exportable Notebook" in md_body["content"]
        assert "3*x^2 + 2" in md_body["content"]

        json_resp = client.get(f"/api/v1/notebooks/{nb_id}/export?format=json")
        assert json_resp.status_code == 200
        assert json_resp.json()["filename"].endswith(".json")

        del_resp = client.delete(f"/api/v1/notebooks/{nb_id}")
        assert del_resp.status_code == 204

        missing = client.get(f"/api/v1/notebooks/{nb_id}")
        assert missing.status_code == 404

    def test_stateless_execution_runs_without_persisting_to_database(self, isolated_client):
        client, _ = isolated_client
        resp = client.post(
            "/api/v1/notebooks/execute-stateless",
            json={
                "title": "Guest Scratchpad",
                "mode": "computational",
                "cells": [
                    {"id": "g1", "operation": "assign", "expression": "f = x^2 + 3*x"},
                    {"id": "g2", "operation": "differentiate", "expression": "f", "variable": "x"},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["history_id"] == "stateless"
        assert body["executed_cell_ids"] == ["g1", "g2"]
        assert body["notebook"]["cells"][1]["result"]["result_text"] == "2*x + 3"
        assert body["notebook"]["cells"][1]["depends_on"] == ["g1"]
        assert client.get("/api/v1/notebooks").json() == []

    def test_inline_assignment_works_across_expression_operations(self, isolated_client):
        client, _ = isolated_client
        create_resp = client.post(
            "/api/v1/notebooks",
            json={
                "title": "Inline Assignment Notebook",
                "cells": [
                    {"operation": "simplify", "expression": "f = (x^2 - 1)/(x - 1)"},
                    {"operation": "differentiate", "expression": "f", "variable": "x"},
                ],
            },
        )
        assert create_resp.status_code == 201
        nb_id = create_resp.json()["id"]

        exec_resp = client.post(f"/api/v1/notebooks/{nb_id}/execute", json={})
        assert exec_resp.status_code == 200
        nb = exec_resp.json()["notebook"]
        assert nb["cells"][0]["status"] == "valid"
        assert nb["cells"][0]["result"]["result_text"] == "x + 1"
        assert nb["variables"]["f"]["value_expr"] == "x + 1"
        assert nb["cells"][1]["status"] == "valid"
        assert nb["cells"][1]["result"]["result_text"] == "1"

    def test_matrix_cell_ignores_stale_expression_for_dependencies(self, isolated_client):
        client, _ = isolated_client
        resp = client.post(
            "/api/v1/notebooks/execute-stateless",
            json={
                "title": "Matrix Deps Check",
                "mode": "computational",
                "cells": [
                    {"id": "c1", "operation": "simplify", "expression": "f = x^3 + 2*x"},
                    {
                        "id": "c2",
                        "operation": "matrix_inverse",
                        "expression": "f",
                        "options": {"matrix": [[1, 0], [0, 1]]},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        cells = resp.json()["notebook"]["cells"]
        assert cells[1]["status"] == "valid"
        assert cells[1]["depends_on"] == []
