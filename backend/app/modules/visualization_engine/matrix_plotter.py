"""Matrix and linear system geometric/heatmap Plotly trace generators."""

from __future__ import annotations

from typing import Any

import numpy as np
import sympy as sp

from app.core.exceptions import InvalidExpressionError
from app.modules.math_engine.parser.safe_parser import parse_math_expression, parse_symbol

MAX_PLOT_MATRIX_DIM = 12


def _eval_numeric_cell(
    raw_val: Any,
    parameters: dict[str, float] | None,
    assumptions: dict[str, str] | None,
) -> float:
    text = str(raw_val).strip()
    if not text:
        return 0.0
    parsed = parse_math_expression(text, assumptions=assumptions)
    if parameters:
        subs = {
            parse_symbol(name, assumptions=assumptions): sp.Float(str(val))
            for name, val in parameters.items()
        }
        parsed = parsed.subs(subs)
    if parsed.free_symbols:
        names = sorted(s.name for s in parsed.free_symbols)
        raise InvalidExpressionError(
            f"Unbound symbol(s) {names} in matrix entry '{text}'. Supply numeric values to plot.",
            details={"unbound_parameters": names},
        )
    try:
        c = complex(sp.N(parsed))
    except Exception as exc:
        raise InvalidExpressionError(f"Matrix entry '{text}' could not be evaluated numerically.") from exc
    if abs(c.imag) > 1e-8 or not (np.isfinite(c.real)):
        raise InvalidExpressionError(f"Matrix entry '{text}' must evaluate to a finite real number for plotting.")
    return float(c.real)


def _parse_numeric_matrix(
    raw_matrix: list[list[Any]] | None,
    parameters: dict[str, float] | None,
    assumptions: dict[str, str] | None,
    label: str = "matrix",
) -> np.ndarray:
    if not isinstance(raw_matrix, list) or len(raw_matrix) == 0 or not isinstance(raw_matrix[0], list):
        raise InvalidExpressionError(f"A non-empty 2D '{label}' is required for matrix plotting.")
    rows = len(raw_matrix)
    cols = len(raw_matrix[0])
    if cols == 0 or rows > MAX_PLOT_MATRIX_DIM or cols > MAX_PLOT_MATRIX_DIM:
        raise InvalidExpressionError(f"'{label}' dimensions must be between 1x1 and {MAX_PLOT_MATRIX_DIM}x{MAX_PLOT_MATRIX_DIM}.")
    data: list[list[float]] = []
    for row in raw_matrix:
        if not isinstance(row, list) or len(row) != cols:
            raise InvalidExpressionError(f"All rows in '{label}' must have equal length.")
        data.append([_eval_numeric_cell(cell, parameters, assumptions) for cell in row])
    return np.array(data, dtype=float)


def _parse_numeric_vector(
    raw_vec: list[Any],
    expected_len: int,
    parameters: dict[str, float] | None,
    assumptions: dict[str, str] | None,
) -> np.ndarray:
    if len(raw_vec) != expected_len:
        raise InvalidExpressionError(f"'vector' length ({len(raw_vec)}) must match matrix rows ({expected_len}).")
    return np.array([_eval_numeric_cell(v, parameters, assumptions) for v in raw_vec], dtype=float)


def _plot_heatmap(A: np.ndarray) -> dict[str, Any]:
    rows, cols = A.shape
    flipped = A[::-1]
    x_labels = [f"Col {c + 1}" for c in range(cols)]
    y_labels = [f"Row {r + 1}" for r in range(rows)][::-1]
    text_rows = [[f"{float(val):.4g}" for val in row] for row in flipped]

    return {
        "plot_type": "2d",
        "traces": [
            {
                "type": "heatmap",
                "name": "Matrix Values",
                "x": x_labels,
                "y": y_labels,
                "z": [[round(float(val), 6) for val in row] for row in flipped],
                "text": text_rows,
                "texttemplate": "%{text}",
                "colorscale": "RdBu",
                "hoverongaps": False,
            }
        ],
        "key_points": [],
        "layout": {
            "title": f"{rows}×{cols} Matrix Heatmap",
            "xaxis_title": "Column",
            "yaxis_title": "Row",
        },
        "metadata": {
            "matrix_view": "heatmap",
            "is_heatmap": True,
            "shape": [rows, cols],
        },
    }


def _vector_hovertext(col_idx: int, vec: np.ndarray, prefix: str = "A", is_projected: bool = False) -> list[str]:
    """Build explicit Origin vs Tip hover descriptions for column vectors."""
    coords = ", ".join(f"{float(c):.3g}" for c in vec)
    norm = float(np.linalg.norm(vec))
    origin_desc = f"Origin · start of Column {col_idx + 1} ({prefix}·e{col_idx + 1})"
    tip_lines = [f"<b>Column {col_idx + 1}: {prefix}·e{col_idx + 1} = ({coords})</b>"]
    if is_projected and len(vec) > 3:
        tip_lines.append(f"3D projection: ({float(vec[0]):.3g}, {float(vec[1]):.3g}, {float(vec[2]):.3g})")
    tip_lines.append(f"Length |v| = {norm:.4g}")
    return [origin_desc, "<br>".join(tip_lines)]


def _plot_transform_2d(A: np.ndarray, B: np.ndarray | None = None) -> dict[str, Any]:
    e1_t = A[:, 0]
    e2_t = A[:, 1]
    sum_t = e1_t + e2_t
    det = float(np.linalg.det(A))

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines",
            "name": "Unit Square",
            "x": [0, 1, 1, 0, 0],
            "y": [0, 0, 1, 1, 0],
            "line": {"color": "#71717a", "dash": "dot", "width": 1.5},
            "hoverinfo": "name",
        },
        {
            "type": "scatter",
            "mode": "lines",
            "name": f"Transformed Area (det = {det:.4g})",
            "x": [0, float(e1_t[0]), float(sum_t[0]), float(e2_t[0]), 0],
            "y": [0, float(e1_t[1]), float(sum_t[1]), float(e2_t[1]), 0],
            "fill": "toself",
            "fillcolor": "rgba(37, 99, 235, 0.14)",
            "line": {"color": "#2563eb", "width": 1.5},
            "hoverinfo": "name",
        },
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": f"A·e₁ = ({e1_t[0]:.3g}, {e1_t[1]:.3g})",
            "x": [0, float(e1_t[0])],
            "y": [0, float(e1_t[1])],
            "hovertext": _vector_hovertext(0, e1_t),
            "hoverinfo": "text",
            "line": {"color": "#dc2626", "width": 3},
            "marker": {"size": [4, 9]},
        },
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": f"A·e₂ = ({e2_t[0]:.3g}, {e2_t[1]:.3g})",
            "x": [0, float(e2_t[0])],
            "y": [0, float(e2_t[1])],
            "hovertext": _vector_hovertext(1, e2_t),
            "hoverinfo": "text",
            "line": {"color": "#059669", "width": 3},
            "marker": {"size": [4, 9]},
        },
    ]

    eigvals, eigvecs = np.linalg.eig(A)
    span = max(float(np.max(np.abs(np.vstack([e1_t, e2_t, sum_t])))) * 1.15, 2.0)
    real_idx = 0
    for i in range(len(eigvals)):
        if abs(eigvals[i].imag) < 1e-7:
            real_idx += 1
            lam = float(eigvals[i].real)
            vec = np.real(eigvecs[:, i])
            norm = float(np.linalg.norm(vec))
            if norm > 1e-12:
                u = vec / norm
                traces.append(
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": f"Eigenvector v{real_idx} (λ = {lam:.3g})",
                        "x": [float(-span * u[0]), float(span * u[0])],
                        "y": [float(-span * u[1]), float(span * u[1])],
                        "line": {"color": "#d97706" if real_idx == 1 else "#7c3aed", "dash": "dash", "width": 1.5},
                        "marker": {"size": 6},
                    }
                )

    if B is not None and B.shape == (2, 2):
        b1 = B[:, 0]
        b2 = B[:, 1]
        bsum = b1 + b2
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Result / Compare Matrix B",
                "x": [0, float(b1[0]), float(bsum[0]), float(b2[0]), 0],
                "y": [0, float(b1[1]), float(bsum[1]), float(b2[1]), 0],
                "line": {"color": "#10b981", "dash": "dash", "width": 2},
            }
        )

    key_points = [
        {
            "kind": "column_1",
            "x": round(float(e1_t[0]), 6),
            "y": round(float(e1_t[1]), 6),
            "label": f"A·e₁ = ({e1_t[0]:.4g}, {e1_t[1]:.4g})",
        },
        {
            "kind": "column_2",
            "x": round(float(e2_t[0]), 6),
            "y": round(float(e2_t[1]), 6),
            "label": f"A·e₂ = ({e2_t[0]:.4g}, {e2_t[1]:.4g})",
        },
    ]

    return {
        "plot_type": "2d",
        "traces": traces,
        "key_points": key_points,
        "layout": {
            "title": "2D Linear Transformation & Eigenvectors",
            "xaxis_title": "x",
            "yaxis_title": "y",
        },
        "metadata": {
            "matrix_view": "transform",
            "equal_aspect": True,
            "determinant": round(det, 6),
        },
    }


def _parallelepiped_wireframe(
    v1: np.ndarray,
    v2: np.ndarray,
    v3: np.ndarray,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Build Plotly line-segment coordinates (with None breaks) for the 12 edges of a 3D parallelepiped."""
    zero = np.zeros(3, dtype=float)
    pts = [
        zero, v1, v2, v3,
        v1 + v2, v1 + v3, v2 + v3, v1 + v2 + v3,
    ]
    edges = [
        (0, 1), (0, 2), (0, 3),
        (1, 4), (1, 5), (2, 4), (2, 6), (3, 5), (3, 6),
        (4, 7), (5, 7), (6, 7),
    ]
    xs: list[float | None] = []
    ys: list[float | None] = []
    zs: list[float | None] = []
    for i, j in edges:
        xs.extend([round(float(pts[i][0]), 6), round(float(pts[j][0]), 6), None])
        ys.extend([round(float(pts[i][1]), 6), round(float(pts[j][1]), 6), None])
        zs.extend([round(float(pts[i][2]), 6), round(float(pts[j][2]), 6), None])
    return xs, ys, zs


def _plot_transform_3d(A: np.ndarray, B: np.ndarray | None = None) -> dict[str, Any]:
    colors = ["#dc2626", "#059669", "#2563eb"]
    ux, uy, uz = _parallelepiped_wireframe(
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    )
    tx, ty, tz = _parallelepiped_wireframe(A[:, 0], A[:, 1], A[:, 2])
    det = float(np.linalg.det(A))

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter3d",
            "mode": "lines",
            "name": "Unit Cube",
            "x": ux,
            "y": uy,
            "z": uz,
            "line": {"width": 2, "dash": "dot", "color": "#71717a"},
        },
        {
            "type": "scatter3d",
            "mode": "lines",
            "name": f"Transformed Volume (det = {det:.4g})",
            "x": tx,
            "y": ty,
            "z": tz,
            "line": {"width": 2.5, "color": "#3b82f6"},
        },
    ]

    for col_idx in range(3):
        v = A[:, col_idx]
        traces.append(
            {
                "type": "scatter3d",
                "mode": "lines+markers",
                "name": f"A·e{col_idx + 1} = ({v[0]:.3g}, {v[1]:.3g}, {v[2]:.3g})",
                "x": [0.0, float(v[0])],
                "y": [0.0, float(v[1])],
                "z": [0.0, float(v[2])],
                "hovertext": _vector_hovertext(col_idx, v),
                "hoverinfo": "text",
                "line": {"width": 6, "color": colors[col_idx]},
                "marker": {"size": [3, 6], "color": colors[col_idx]},
            }
        )

    eigvals, eigvecs = np.linalg.eig(A)
    span = max(float(np.max(np.abs(A))) * 1.35, 2.0)
    eig_colors = ["#d97706", "#7c3aed", "#0891b2"]
    real_idx = 0
    for i in range(len(eigvals)):
        if abs(eigvals[i].imag) < 1e-7:
            vec = np.real(eigvecs[:, i])
            norm = float(np.linalg.norm(vec))
            if norm > 1e-12:
                u = vec / norm
                lam = float(eigvals[i].real)
                col = eig_colors[real_idx % len(eig_colors)]
                real_idx += 1
                traces.append(
                    {
                        "type": "scatter3d",
                        "mode": "lines+markers",
                        "name": f"Eigenvector v{real_idx} (λ = {lam:.3g})",
                        "x": [float(-span * u[0]), float(span * u[0])],
                        "y": [float(-span * u[1]), float(span * u[1])],
                        "z": [float(-span * u[2]), float(span * u[2])],
                        "line": {"width": 3, "dash": "dash", "color": col},
                        "marker": {"size": 4, "color": col},
                    }
                )

    if B is not None and B.shape == (3, 3):
        bx, by, bz = _parallelepiped_wireframe(B[:, 0], B[:, 1], B[:, 2])
        traces.append(
            {
                "type": "scatter3d",
                "mode": "lines",
                "name": "Result / Compare Matrix B",
                "x": bx,
                "y": by,
                "z": bz,
                "line": {"width": 2.5, "dash": "dash", "color": "#10b981"},
            }
        )
        for col_idx in range(3):
            vb = B[:, col_idx]
            traces.append(
                {
                    "type": "scatter3d",
                    "mode": "lines+markers",
                    "name": f"B·e{col_idx + 1} = ({vb[0]:.3g}, {vb[1]:.3g}, {vb[2]:.3g})",
                    "x": [0.0, float(vb[0])],
                    "y": [0.0, float(vb[1])],
                    "z": [0.0, float(vb[2])],
                    "hovertext": _vector_hovertext(col_idx, vb, prefix="B"),
                    "hoverinfo": "text",
                    "line": {"width": 4, "dash": "dash", "color": "#f59e0b"},
                    "marker": {"size": [2, 5], "color": "#f59e0b"},
                }
            )

    return {
        "plot_type": "3d",
        "traces": traces,
        "key_points": [],
        "layout": {
            "title": "3D Linear Transformation & Eigenvectors",
            "xaxis_title": "x",
            "yaxis_title": "y",
            "zaxis_title": "z",
        },
        "metadata": {
            "matrix_view": "transform",
            "determinant": round(det, 6),
        },
    }


def _plot_transform_nd_projection(A: np.ndarray) -> dict[str, Any]:
    """Project 4D+ column vectors onto the first 3 dimensions while displaying full coordinates in labels."""
    rows, cols = A.shape
    palette = ["#dc2626", "#059669", "#2563eb", "#d97706", "#7c3aed", "#0891b2"]
    traces: list[dict[str, Any]] = []

    for col_idx in range(cols):
        v = A[:, col_idx]
        x_val = float(v[0])
        y_val = float(v[1]) if rows > 1 else 0.0
        z_val = float(v[2]) if rows > 2 else 0.0
        coord_text = ", ".join(f"{float(c):.3g}" for c in v)
        col = palette[col_idx % len(palette)]
        traces.append(
            {
                "type": "scatter3d",
                "mode": "lines+markers",
                "name": f"A·e{col_idx + 1} = ({coord_text})",
                "x": [0.0, x_val],
                "y": [0.0, y_val],
                "z": [0.0, z_val],
                "hovertext": _vector_hovertext(col_idx, v, is_projected=True),
                "hoverinfo": "text",
                "line": {"width": 5, "color": col},
                "marker": {"size": [3, 6], "color": col},
            }
        )

    return {
        "plot_type": "3d",
        "traces": traces,
        "key_points": [],
        "layout": {
            "title": f"{rows}×{cols} Column Vectors (3D Projection x₁, x₂, x₃)",
            "xaxis_title": "x₁",
            "yaxis_title": "x₂",
            "zaxis_title": "x₃",
        },
        "metadata": {
            "matrix_view": "transform",
            "shape": [rows, cols],
            "projected_from_dim": rows,
        },
    }


def _plot_matrix_surface_3d(A: np.ndarray) -> dict[str, Any]:
    """Render any m×n matrix as an interactive 3D height surface over (Column, Row)."""
    rows, cols = A.shape
    x_cols = list(range(1, cols + 1))
    y_rows = list(range(1, rows + 1))
    z_mat = [[round(float(val), 6) for val in row] for row in A]

    pt_x: list[int] = []
    pt_y: list[int] = []
    pt_z: list[float] = []
    pt_text: list[str] = []
    for r in range(rows):
        for c in range(cols):
            val = round(float(A[r, c]), 6)
            pt_x.append(c + 1)
            pt_y.append(r + 1)
            pt_z.append(val)
            pt_text.append(f"A[{r + 1},{c + 1}] = {val:g}")

    return {
        "plot_type": "3d",
        "traces": [
            {
                "type": "surface",
                "name": f"{rows}×{cols} Height Surface",
                "x": x_cols,
                "y": y_rows,
                "z": z_mat,
                "opacity": 0.85,
                "showlegend": True,
            },
            {
                "type": "scatter3d",
                "mode": "markers",
                "name": "Matrix Entries",
                "x": pt_x,
                "y": pt_y,
                "z": pt_z,
                "text": pt_text,
                "hoverinfo": "text",
                "marker": {"size": 4, "color": "#f59e0b"},
            },
        ],
        "key_points": [],
        "layout": {
            "title": f"{rows}×{cols} Matrix 3D Height Surface",
            "xaxis_title": "Column",
            "yaxis_title": "Row",
            "zaxis_title": "Value",
        },
        "metadata": {
            "matrix_view": "surface",
            "shape": [rows, cols],
        },
    }


def _plot_system_2d(A: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    det = float(np.linalg.det(A))
    has_unique = abs(det) > 1e-9
    sol = np.linalg.solve(A, b) if has_unique else np.array([0.0, 0.0])
    cx, cy = float(sol[0]), float(sol[1])
    span = 6.0
    xs = np.linspace(cx - span, cx + span, 80)

    traces: list[dict[str, Any]] = []
    line_colors = ["#2563eb", "#dc2626"]
    for idx in range(2):
        a1, a2, rhs = float(A[idx, 0]), float(A[idx, 1]), float(b[idx])
        sign2 = "+" if a2 >= 0 else "-"
        label = f"{a1:.3g}x {sign2} {abs(a2):.3g}y = {rhs:.3g}"
        if abs(a2) > 1e-12:
            ys = [(rhs - a1 * float(x)) / a2 for x in xs]
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": label,
                    "x": [round(float(x), 6) for x in xs],
                    "y": [round(float(y), 6) for y in ys],
                    "line": {"color": line_colors[idx], "width": 2.5},
                }
            )
        elif abs(a1) > 1e-12:
            x_const = rhs / a1
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": label,
                    "x": [x_const, x_const],
                    "y": [cy - span, cy + span],
                    "line": {"color": line_colors[idx], "width": 2.5},
                }
            )

    key_points: list[dict[str, Any]] = []
    if has_unique:
        sx, sy = round(cx, 6), round(cy, 6)
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": f"Solution ({sx:g}, {sy:g})",
                "x": [sx],
                "y": [sy],
                "marker": {"size": 10, "color": "#059669"},
            }
        )
        key_points.append(
            {
                "kind": "solution",
                "x": sx,
                "y": sy,
                "label": f"Intersection ({sx:g}, {sy:g})",
            }
        )

    return {
        "plot_type": "2d",
        "traces": traces,
        "key_points": key_points,
        "layout": {
            "title": "2×2 Linear System (Ax = b)",
            "xaxis_title": "x",
            "yaxis_title": "y",
        },
        "metadata": {
            "matrix_view": "system",
            "x_range": [cx - span, cx + span],
        },
    }


def _plot_system_3d(A: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    det = float(np.linalg.det(A))
    has_unique = abs(det) > 1e-9
    sol = np.linalg.solve(A, b) if has_unique else np.array([0.0, 0.0, 0.0])
    cx, cy, cz = float(sol[0]), float(sol[1]), float(sol[2])
    span = 4.0
    xs = np.linspace(cx - span, cx + span, 16)
    ys = np.linspace(cy - span, cy + span, 16)

    traces: list[dict[str, Any]] = []
    plane_colors = ["#2563eb", "#dc2626", "#059669"]
    for idx in range(3):
        a1, a2, a3, rhs = float(A[idx, 0]), float(A[idx, 1]), float(A[idx, 2]), float(b[idx])
        sign2 = "+" if a2 >= 0 else "-"
        sign3 = "+" if a3 >= 0 else "-"
        if abs(a3) > 1e-12:
            z_mat = [
                [round((rhs - a1 * float(x) - a2 * float(y)) / a3, 6) for x in xs]
                for y in ys
            ]
            traces.append(
                {
                    "type": "surface",
                    "name": f"Eq {idx + 1}: {a1:.3g}x {sign2} {abs(a2):.3g}y {sign3} {abs(a3):.3g}z = {rhs:.3g}",
                    "x": [round(float(x), 6) for x in xs],
                    "y": [round(float(y), 6) for y in ys],
                    "z": z_mat,
                    "opacity": 0.45,
                    "showscale": False,
                    "colorscale": [[0, plane_colors[idx]], [1, plane_colors[idx]]],
                    "showlegend": True,
                }
            )

    if has_unique:
        traces.append(
            {
                "type": "scatter3d",
                "mode": "markers",
                "name": f"Solution ({cx:.3g}, {cy:.3g}, {cz:.3g})",
                "x": [round(cx, 6)],
                "y": [round(cy, 6)],
                "z": [round(cz, 6)],
                "marker": {"size": 7, "color": "#f59e0b"},
            }
        )

    return {
        "plot_type": "3d",
        "traces": traces,
        "key_points": [],
        "layout": {
            "title": "3×3 Linear System Planes (Ax = b)",
            "xaxis_title": "x",
            "yaxis_title": "y",
            "zaxis_title": "z",
        },
        "metadata": {
            "matrix_view": "system",
        },
    }


def generate_matrix_visualization_data(
    *,
    matrix: list[list[Any]] | None,
    matrix_b: list[list[Any]] | None = None,
    vector: list[Any] | None = None,
    matrix_view: str = "auto",
    parameters: dict[str, float] | None = None,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate geometric (2D/3D) or heatmap Plotly datasets for matrices and linear systems."""
    A = _parse_numeric_matrix(matrix, parameters, assumptions, label="matrix")
    B = (
        _parse_numeric_matrix(matrix_b, parameters, assumptions, label="matrix_b")
        if matrix_b is not None
        else None
    )

    view = matrix_view.strip().lower()
    if view == "heatmap":
        return _plot_heatmap(A)

    if view == "surface":
        return _plot_matrix_surface_3d(A)

    if view == "system" or (view == "auto" and vector is not None):
        if vector is None:
            raise InvalidExpressionError("Linear system view requires a target 'vector' b.")
        b_vec = _parse_numeric_vector(vector, A.shape[0], parameters, assumptions)
        if A.shape == (2, 2):
            return _plot_system_2d(A, b_vec)
        if A.shape == (3, 3):
            return _plot_system_3d(A, b_vec)
        return _plot_heatmap(A)

    if view in ("auto", "transform"):
        if A.shape == (2, 2):
            return _plot_transform_2d(A, B)
        if A.shape == (3, 3):
            return _plot_transform_3d(A, B)
        if view == "transform" and A.shape[0] >= 3 and A.shape[1] >= 1:
            return _plot_transform_nd_projection(A)
        return _plot_heatmap(A)

    raise InvalidExpressionError(
        "Field 'matrix_view' must be 'auto', 'transform', 'system', 'surface', or 'heatmap'."
    )
