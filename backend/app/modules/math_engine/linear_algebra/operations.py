"""Linear algebra operations."""

from __future__ import annotations

from typing import Any

import sympy as sp

from app.core.exceptions import ComputationLimitError, DomainError, InvalidExpressionError
from app.core.security import MAX_MATRIX_DIM
from app.modules.math_engine.parser.safe_parser import format_sympy_expr, parse_math_expression


def parse_matrix(
    raw_matrix: Any,
    assumptions: dict[str, str] | None = None,
) -> sp.Matrix:
    """Validate and convert a 2D JSON matrix into a SymPy Matrix using the safe parser."""
    if not isinstance(raw_matrix, list) or not raw_matrix:
        raise InvalidExpressionError("Matrix must be a non-empty 2D list.")
    if len(raw_matrix) > MAX_MATRIX_DIM:
        raise ComputationLimitError(f"Matrix row count exceeds maximum of {MAX_MATRIX_DIM}.")

    row_len: int | None = None
    parsed_rows: list[list[sp.Basic]] = []
    for row in raw_matrix:
        if not isinstance(row, list) or not row:
            raise InvalidExpressionError("Each matrix row must be a non-empty list.")
        if len(row) > MAX_MATRIX_DIM:
            raise ComputationLimitError(f"Matrix column count exceeds maximum of {MAX_MATRIX_DIM}.")
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            raise InvalidExpressionError("Matrix rows must all have the same length.")

        parsed_row: list[sp.Basic] = []
        for entry in row:
            if isinstance(entry, bool):
                raise InvalidExpressionError("Matrix entries cannot be booleans.")
            if isinstance(entry, int):
                parsed_row.append(sp.Integer(entry))
            elif isinstance(entry, float):
                parsed_row.append(sp.Float(str(entry)))
            elif isinstance(entry, str):
                parsed_row.append(parse_math_expression(entry, assumptions=assumptions))
            else:
                raise InvalidExpressionError(f"Unsupported matrix entry type: {type(entry).__name__}.")
        parsed_rows.append(parsed_row)

    return sp.Matrix(parsed_rows)


def _matrix_to_nested(mat: sp.Matrix) -> list[list[str]]:
    return [[format_sympy_expr(mat[r, c]) for c in range(mat.cols)] for r in range(mat.rows)]


def _require_square(mat: sp.Matrix, op_name: str) -> None:
    if mat.rows != mat.cols:
        raise DomainError(f"'{op_name}' requires a square matrix, got {mat.rows}x{mat.cols}.")


def matrix_determinant(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute the determinant of a square matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    _require_square(mat, "matrix_determinant")
    det = mat.det()
    return {
        "result": format_sympy_expr(det),
        "latex": sp.latex(det),
        "details": {"method": "matrix_determinant", "shape": [mat.rows, mat.cols]},
    }


def matrix_rank(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute the rank of a matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    rank = int(mat.rank())
    return {
        "result": str(rank),
        "latex": str(rank),
        "details": {"method": "matrix_rank", "rank": rank, "shape": [mat.rows, mat.cols]},
    }


def matrix_transpose(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute the transpose of a matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    transposed = mat.T
    return {
        "result": format_sympy_expr(transposed),
        "latex": sp.latex(transposed),
        "details": {
            "method": "matrix_transpose",
            "matrix": _matrix_to_nested(transposed),
            "shape": [transposed.rows, transposed.cols],
        },
    }


def matrix_inverse(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute the inverse of an invertible square matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    _require_square(mat, "matrix_inverse")
    if mat.det() == 0:
        raise DomainError("Matrix is singular (determinant is 0) and cannot be inverted.")
    inv = mat.inv()
    return {
        "result": format_sympy_expr(inv),
        "latex": sp.latex(inv),
        "details": {
            "method": "matrix_inverse",
            "matrix": _matrix_to_nested(inv),
            "shape": [inv.rows, inv.cols],
        },
    }


def matrix_rref(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute the reduced row echelon form (RREF) of a matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    reduced, pivots = mat.rref()
    return {
        "result": format_sympy_expr(reduced),
        "latex": sp.latex(reduced),
        "details": {
            "method": "matrix_rref",
            "matrix": _matrix_to_nested(reduced),
            "pivots": list(pivots),
            "shape": [reduced.rows, reduced.cols],
        },
    }


def matrix_eigenvalues(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute eigenvalues and algebraic multiplicities of a square matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    _require_square(mat, "matrix_eigenvalues")
    eigenvals = mat.eigenvals()
    items = [
        {"value": format_sympy_expr(val), "latex": sp.latex(val), "multiplicity": int(mult)}
        for val, mult in eigenvals.items()
    ]
    summary = ", ".join(
        f"{item['value']}" if item["multiplicity"] == 1 else f"{item['value']} (mult {item['multiplicity']})"
        for item in items
    )
    return {
        "result": summary,
        "latex": ", ".join(item["latex"] for item in items),
        "details": {
            "method": "matrix_eigenvalues",
            "eigenvalues": items,
            "shape": [mat.rows, mat.cols],
        },
    }


def matrix_eigenvectors(matrix: Any, assumptions: dict[str, str] | None = None) -> dict[str, Any]:
    """Compute eigenvalues, multiplicities, and eigenvectors of a square matrix."""
    mat = parse_matrix(matrix, assumptions=assumptions)
    _require_square(mat, "matrix_eigenvectors")
    eigenvects = mat.eigenvects()
    items = []
    for val, mult, vects in eigenvects:
        items.append(
            {
                "eigenvalue": format_sympy_expr(val),
                "eigenvalue_latex": sp.latex(val),
                "multiplicity": int(mult),
                "vectors": [[format_sympy_expr(v[r, 0]) for r in range(v.rows)] for v in vects],
            }
        )
    return {
        "result": "; ".join(f"lambda={item['eigenvalue']}: {item['vectors']}" for item in items),
        "latex": ", ".join(item["eigenvalue_latex"] for item in items),
        "details": {
            "method": "matrix_eigenvectors",
            "eigensystem": items,
            "shape": [mat.rows, mat.cols],
        },
    }


def matrix_add(
    matrix_a: Any,
    matrix_b: Any,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Add two matrices of identical dimensions."""
    a = parse_matrix(matrix_a, assumptions=assumptions)
    b = parse_matrix(matrix_b, assumptions=assumptions)
    if a.shape != b.shape:
        raise DomainError(f"Matrix dimensions {a.shape} and {b.shape} do not match for addition.")
    summed = a + b
    return {
        "result": format_sympy_expr(summed),
        "latex": sp.latex(summed),
        "details": {
            "method": "matrix_addition",
            "matrix": _matrix_to_nested(summed),
            "shape": [summed.rows, summed.cols],
        },
    }


def matrix_multiply(
    matrix_a: Any,
    matrix_b: Any,
    assumptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Multiply two compatible matrices A * B."""
    a = parse_matrix(matrix_a, assumptions=assumptions)
    b = parse_matrix(matrix_b, assumptions=assumptions)
    if a.cols != b.rows:
        raise DomainError(f"Incompatible shapes for multiplication: {a.shape} and {b.shape}.")
    product = a * b
    return {
        "result": format_sympy_expr(product),
        "latex": sp.latex(product),
        "details": {
            "method": "matrix_multiplication",
            "matrix": _matrix_to_nested(product),
            "shape": [product.rows, product.cols],
        },
    }
