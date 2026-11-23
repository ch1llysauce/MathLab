"""SQLite-backed persistence repository for computational notebooks (aligned with Supabase schema)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
import uuid

from app.models.notebook import (
    CellResult,
    NotebookCellModel,
    NotebookModel,
    VariableBinding,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotebookRepository:
    """Repository managing notebook persistence, cell results, variables, and history."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notebooks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'computational',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notebook_cells (
                    id TEXT PRIMARY KEY,
                    notebook_id TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    cell_type TEXT NOT NULL DEFAULT 'math',
                    operation TEXT,
                    expression TEXT,
                    variable TEXT,
                    assign_to TEXT,
                    assumptions_json TEXT NOT NULL DEFAULT '{}',
                    options_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'idle',
                    depends_on TEXT NOT NULL DEFAULT '[]',
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS computation_results (
                    id TEXT PRIMARY KEY,
                    cell_id TEXT NOT NULL REFERENCES notebook_cells(id) ON DELETE CASCADE,
                    result_text TEXT NOT NULL,
                    result_latex TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    reasoning_json TEXT,
                    verification_json TEXT,
                    executed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS variables_and_assumptions (
                    id TEXT PRIMARY KEY,
                    notebook_id TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
                    cell_id TEXT NOT NULL REFERENCES notebook_cells(id) ON DELETE CASCADE,
                    symbol_name TEXT NOT NULL,
                    value_expr TEXT NOT NULL,
                    value_latex TEXT NOT NULL,
                    assumptions_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE (notebook_id, symbol_name)
                );

                CREATE TABLE IF NOT EXISTS notebook_history (
                    id TEXT PRIMARY KEY,
                    notebook_id TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def list_notebooks(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT n.id, n.title, n.mode, n.created_at, n.updated_at,
                       COUNT(c.id) AS cell_count
                FROM notebooks n
                LEFT JOIN notebook_cells c ON c.notebook_id = n.id
                GROUP BY n.id
                ORDER BY n.updated_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_notebook(self, notebook_id: str) -> NotebookModel | None:
        with self._connect() as conn:
            nb_row = conn.execute(
                "SELECT id, title, mode, created_at, updated_at FROM notebooks WHERE id = ?",
                (notebook_id,),
            ).fetchone()
            if nb_row is None:
                return None

            cell_rows = conn.execute(
                """
                SELECT id, notebook_id, position, cell_type, operation, expression, variable,
                       assign_to, assumptions_json, options_json, status, depends_on, error_message
                FROM notebook_cells
                WHERE notebook_id = ?
                ORDER BY position ASC
                """,
                (notebook_id,),
            ).fetchall()

            result_rows = conn.execute(
                """
                SELECT cr.cell_id, cr.result_text, cr.result_latex, cr.metadata_json,
                       cr.reasoning_json, cr.verification_json, cr.executed_at
                FROM computation_results cr
                JOIN notebook_cells nc ON nc.id = cr.cell_id
                WHERE nc.notebook_id = ?
                """,
                (notebook_id,),
            ).fetchall()
            results_by_cell = {
                row["cell_id"]: CellResult(
                    result_text=row["result_text"],
                    result_latex=row["result_latex"],
                    metadata=json.loads(row["metadata_json"]),
                    reasoning=json.loads(row["reasoning_json"]) if row["reasoning_json"] else None,
                    verification=json.loads(row["verification_json"]) if row["verification_json"] else None,
                    executed_at=row["executed_at"],
                )
                for row in result_rows
            }

            cells = [
                NotebookCellModel(
                    id=row["id"],
                    notebook_id=row["notebook_id"],
                    position=row["position"],
                    cell_type=row["cell_type"],
                    operation=row["operation"],
                    expression=row["expression"],
                    variable=row["variable"],
                    assign_to=row["assign_to"],
                    assumptions=json.loads(row["assumptions_json"]),
                    options=json.loads(row["options_json"]),
                    status=row["status"],
                    depends_on=json.loads(row["depends_on"]),
                    error_message=row["error_message"],
                    result=results_by_cell.get(row["id"]),
                )
                for row in cell_rows
            ]

            var_rows = conn.execute(
                """
                SELECT symbol_name, value_expr, value_latex, cell_id, assumptions_json
                FROM variables_and_assumptions
                WHERE notebook_id = ?
                ORDER BY symbol_name ASC
                """,
                (notebook_id,),
            ).fetchall()
            variables = {
                row["symbol_name"]: VariableBinding(
                    symbol_name=row["symbol_name"],
                    value_expr=row["value_expr"],
                    value_latex=row["value_latex"],
                    cell_id=row["cell_id"],
                    assumptions=json.loads(row["assumptions_json"]),
                )
                for row in var_rows
            }

            return NotebookModel(
                id=nb_row["id"],
                title=nb_row["title"],
                mode=nb_row["mode"],
                created_at=nb_row["created_at"],
                updated_at=nb_row["updated_at"],
                cells=cells,
                variables=variables,
            )

    def save_notebook(self, notebook: NotebookModel) -> NotebookModel:
        now = utc_now_iso()
        if not notebook.created_at:
            notebook.created_at = now
        notebook.updated_at = now

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM notebooks WHERE id = ?",
                (notebook.id,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE notebooks SET title = ?, mode = ?, updated_at = ? WHERE id = ?",
                    (notebook.title, notebook.mode, notebook.updated_at, notebook.id),
                )
                conn.execute("DELETE FROM variables_and_assumptions WHERE notebook_id = ?", (notebook.id,))
                conn.execute("DELETE FROM notebook_cells WHERE notebook_id = ?", (notebook.id,))
            else:
                conn.execute(
                    "INSERT INTO notebooks (id, title, mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (notebook.id, notebook.title, notebook.mode, notebook.created_at, notebook.updated_at),
                )

            for cell in notebook.cells:
                conn.execute(
                    """
                    INSERT INTO notebook_cells (
                        id, notebook_id, position, cell_type, operation, expression, variable,
                        assign_to, assumptions_json, options_json, status, depends_on, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cell.id,
                        notebook.id,
                        cell.position,
                        cell.cell_type,
                        cell.operation,
                        cell.expression,
                        cell.variable,
                        cell.assign_to,
                        json.dumps(cell.assumptions),
                        json.dumps(cell.options),
                        cell.status,
                        json.dumps(cell.depends_on),
                        cell.error_message,
                    ),
                )
                if cell.result is not None:
                    conn.execute(
                        """
                        INSERT INTO computation_results (
                            id, cell_id, result_text, result_latex, metadata_json,
                            reasoning_json, verification_json, executed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            cell.id,
                            cell.result.result_text,
                            cell.result.result_latex,
                            json.dumps(cell.result.metadata),
                            json.dumps(cell.result.reasoning) if cell.result.reasoning is not None else None,
                            json.dumps(cell.result.verification) if cell.result.verification is not None else None,
                            cell.result.executed_at or now,
                        ),
                    )

            for var_name, binding in notebook.variables.items():
                conn.execute(
                    """
                    INSERT INTO variables_and_assumptions (
                        id, notebook_id, cell_id, symbol_name, value_expr, value_latex, assumptions_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        notebook.id,
                        binding.cell_id,
                        var_name,
                        binding.value_expr,
                        binding.value_latex,
                        json.dumps(binding.assumptions),
                    ),
                )

        return notebook

    def record_history(self, notebook_id: str, snapshot: dict[str, Any]) -> str:
        history_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO notebook_history (id, notebook_id, snapshot_json, created_at) VALUES (?, ?, ?, ?)",
                (history_id, notebook_id, json.dumps(snapshot), utc_now_iso()),
            )
        return history_id

    def list_history(self, notebook_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, notebook_id, snapshot_json, created_at FROM notebook_history WHERE notebook_id = ? ORDER BY created_at DESC",
                (notebook_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "notebook_id": row["notebook_id"],
                    "snapshot": json.loads(row["snapshot_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
