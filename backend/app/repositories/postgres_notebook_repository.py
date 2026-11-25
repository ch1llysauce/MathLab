"""PostgreSQL persistence repository for computational notebooks (Supabase-compatible)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.models.notebook import (
    CellResult,
    NotebookCellModel,
    NotebookModel,
    VariableBinding,
)
from app.repositories.notebook_repository import utc_now_iso


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value is not None else ""


def _ensure_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    return value


class PostgresNotebookRepository:
    """PostgreSQL repository targeting the Supabase schema in 001_initial_schema.sql."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        # prepare_threshold=None ensures compatibility with Supabase PgBouncer transaction pooling.
        return psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            prepare_threshold=None,
        )

    def ensure_user(self, user_id: str, email: str | None) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (user_id, email or f"{user_id}@supabase.local", utc_now_iso()),
            )

    def list_notebooks(self, user_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            if user_id is not None:
                cur.execute(
                    """
                    SELECT n.id::text AS id,
                           n.title,
                           n.mode,
                           n.created_at,
                           n.updated_at,
                           COUNT(c.id)::int AS cell_count
                    FROM notebooks n
                    LEFT JOIN notebook_cells c ON c.notebook_id = n.id
                    WHERE n.user_id = %s
                    GROUP BY n.id
                    ORDER BY n.updated_at DESC
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT n.id::text AS id,
                           n.title,
                           n.mode,
                           n.created_at,
                           n.updated_at,
                           COUNT(c.id)::int AS cell_count
                    FROM notebooks n
                    LEFT JOIN notebook_cells c ON c.notebook_id = n.id
                    WHERE n.user_id IS NULL
                    GROUP BY n.id
                    ORDER BY n.updated_at DESC
                    """
                )
            rows = cur.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "mode": row["mode"],
                    "cell_count": row["cell_count"],
                    "created_at": _iso(row["created_at"]),
                    "updated_at": _iso(row["updated_at"]),
                }
                for row in rows
            ]

    def get_notebook(self, notebook_id: str) -> NotebookModel | None:
        try:
            uuid.UUID(notebook_id)
        except ValueError:
            return None

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id::text AS id, user_id::text AS user_id, title, mode, created_at, updated_at FROM notebooks WHERE id = %s",
                (notebook_id,),
            )
            nb_row = cur.fetchone()
            if nb_row is None:
                return None

            cur.execute(
                """
                SELECT id::text AS id,
                       notebook_id::text AS notebook_id,
                       position,
                       cell_type,
                       operation,
                       expression,
                       variable,
                       assign_to,
                       assumptions_json,
                       options_json,
                       status,
                       depends_on,
                       error_message
                FROM notebook_cells
                WHERE notebook_id = %s
                ORDER BY position ASC
                """,
                (notebook_id,),
            )
            cell_rows = cur.fetchall()

            cur.execute(
                """
                SELECT cr.cell_id::text AS cell_id,
                       cr.result_text,
                       cr.result_latex,
                       cr.metadata_json,
                       cr.reasoning_json,
                       cr.verification_json,
                       cr.executed_at
                FROM computation_results cr
                JOIN notebook_cells nc ON nc.id = cr.cell_id
                WHERE nc.notebook_id = %s
                """,
                (notebook_id,),
            )
            result_rows = cur.fetchall()
            results_by_cell = {
                row["cell_id"]: CellResult(
                    result_text=row["result_text"],
                    result_latex=row["result_latex"],
                    metadata=_ensure_json(row["metadata_json"], {}),
                    reasoning=row["reasoning_json"],
                    verification=row["verification_json"],
                    executed_at=_iso(row["executed_at"]),
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
                    assumptions=_ensure_json(row["assumptions_json"], {}),
                    options=_ensure_json(row["options_json"], {}),
                    status=row["status"],
                    depends_on=[str(dep) for dep in _ensure_json(row["depends_on"], [])],
                    error_message=row["error_message"],
                    result=results_by_cell.get(row["id"]),
                )
                for row in cell_rows
            ]

            cur.execute(
                """
                SELECT symbol_name,
                       value_expr,
                       value_latex,
                       cell_id::text AS cell_id,
                       assumptions_json
                FROM variables_and_assumptions
                WHERE notebook_id = %s
                ORDER BY symbol_name ASC
                """,
                (notebook_id,),
            )
            var_rows = cur.fetchall()
            variables = {
                row["symbol_name"]: VariableBinding(
                    symbol_name=row["symbol_name"],
                    value_expr=row["value_expr"],
                    value_latex=row["value_latex"],
                    cell_id=row["cell_id"],
                    assumptions=_ensure_json(row["assumptions_json"], {}),
                )
                for row in var_rows
            }

            return NotebookModel(
                id=nb_row["id"],
                user_id=nb_row.get("user_id"),
                title=nb_row["title"],
                mode=nb_row["mode"],
                created_at=_iso(nb_row["created_at"]),
                updated_at=_iso(nb_row["updated_at"]),
                cells=cells,
                variables=variables,
            )

    def save_notebook(self, notebook: NotebookModel) -> NotebookModel:
        now = utc_now_iso()
        if not notebook.created_at:
            notebook.created_at = now
        notebook.updated_at = now

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM notebooks WHERE id = %s", (notebook.id,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE notebooks SET title = %s, mode = %s, updated_at = %s WHERE id = %s",
                    (notebook.title, notebook.mode, notebook.updated_at, notebook.id),
                )
                cur.execute("DELETE FROM variables_and_assumptions WHERE notebook_id = %s", (notebook.id,))
                cur.execute("DELETE FROM notebook_cells WHERE notebook_id = %s", (notebook.id,))
            else:
                cur.execute(
                    "INSERT INTO notebooks (id, user_id, title, mode, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (notebook.id, notebook.user_id, notebook.title, notebook.mode, notebook.created_at, notebook.updated_at),
                )

            for cell in notebook.cells:
                cur.execute(
                    """
                    INSERT INTO notebook_cells (
                        id, notebook_id, position, cell_type, operation, expression, variable,
                        assign_to, assumptions_json, options_json, status, depends_on, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        Jsonb(cell.assumptions),
                        Jsonb(cell.options),
                        cell.status,
                        Jsonb(cell.depends_on),
                        cell.error_message,
                    ),
                )
                if cell.result is not None:
                    cur.execute(
                        """
                        INSERT INTO computation_results (
                            id, cell_id, result_text, result_latex, metadata_json,
                            reasoning_json, verification_json, executed_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            cell.id,
                            cell.result.result_text,
                            cell.result.result_latex,
                            Jsonb(cell.result.metadata),
                            Jsonb(cell.result.reasoning) if cell.result.reasoning is not None else None,
                            Jsonb(cell.result.verification) if cell.result.verification is not None else None,
                            cell.result.executed_at or now,
                        ),
                    )

            for var_name, binding in notebook.variables.items():
                cur.execute(
                    """
                    INSERT INTO variables_and_assumptions (
                        id, notebook_id, cell_id, symbol_name, value_expr, value_latex, assumptions_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        notebook.id,
                        binding.cell_id,
                        var_name,
                        binding.value_expr,
                        binding.value_latex,
                        Jsonb(binding.assumptions),
                    ),
                )

        return notebook

    def record_history(self, notebook_id: str, snapshot: dict[str, Any]) -> str:
        history_id = str(uuid.uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notebook_history (id, notebook_id, snapshot_json, created_at) VALUES (%s, %s, %s, %s)",
                (history_id, notebook_id, Jsonb(snapshot), utc_now_iso()),
            )
        return history_id

    def list_history(self, notebook_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id,
                       notebook_id::text AS notebook_id,
                       snapshot_json,
                       created_at
                FROM notebook_history
                WHERE notebook_id = %s
                ORDER BY created_at DESC
                """,
                (notebook_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": row["id"],
                    "notebook_id": row["notebook_id"],
                    "snapshot": _ensure_json(row["snapshot_json"], {}),
                    "created_at": _iso(row["created_at"]),
                }
                for row in rows
            ]

    def delete_notebook(self, notebook_id: str) -> bool:
        try:
            uuid.UUID(notebook_id)
        except ValueError:
            return False

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM notebooks WHERE id = %s", (notebook_id,))
            return cur.rowcount > 0
