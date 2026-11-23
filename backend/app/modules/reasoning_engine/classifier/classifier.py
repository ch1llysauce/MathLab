"""Deterministic mathematical problem classifier."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from app.modules.math_engine.linear_algebra.operations import parse_matrix
from app.modules.math_engine.parser.safe_parser import (
    parse_math_expression,
    parse_math_input,
    parse_symbol,
)

TRANSCENDENTAL_FUNCS = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.asin, sp.acos, sp.atan, sp.exp, sp.log, sp.sinh, sp.cosh, sp.tanh)

OPERATION_DOMAIN_MAP = {
    "simplify": "algebra",
    "expand": "algebra",
    "factor": "algebra",
    "solve": "algebra",
    "differentiate": "calculus",
    "diff": "calculus",
    "derivative": "calculus",
    "integrate": "calculus",
    "int": "calculus",
    "integral": "calculus",
    "limit": "calculus",
    "matrix_determinant": "linear_algebra",
    "det": "linear_algebra",
    "determinant": "linear_algebra",
    "matrix_rank": "linear_algebra",
    "rank": "linear_algebra",
    "matrix_transpose": "linear_algebra",
    "transpose": "linear_algebra",
    "matrix_inverse": "linear_algebra",
    "inverse": "linear_algebra",
    "inv": "linear_algebra",
    "matrix_rref": "linear_algebra",
    "rref": "linear_algebra",
    "matrix_eigenvalues": "linear_algebra",
    "eigenvalues": "linear_algebra",
    "matrix_eigenvectors": "linear_algebra",
    "eigenvectors": "linear_algebra",
    "matrix_add": "linear_algebra",
    "matrix_multiply": "linear_algebra",
    "numerical_eval": "numerical",
    "evalf": "numerical",
    "evaluate": "numerical",
    "root_find": "numerical",
    "nsolve": "numerical",
    "numerical_integrate": "numerical",
    "quad": "numerical",
}


@dataclass
class ClassificationResult:
    """Structured problem classification output."""

    domain: str
    problem_type: str
    variables: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    parsed_expr: sp.Basic | sp.Eq | None = None
    parsed_matrix: sp.Matrix | None = None
    parsed_matrix_b: sp.Matrix | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "problem_type": self.problem_type,
            "variables": list(self.variables),
            "features": dict(self.features),
        }


def _classify_algebra_expr(expr: sp.Basic | sp.Eq, target_var: str | None) -> tuple[str, dict[str, Any]]:
    is_eq = isinstance(expr, sp.Eq)
    body = (expr.lhs - expr.rhs) if is_eq else expr
    free_syms = sorted(body.free_symbols, key=lambda s: s.name)
    has_transcendental = any(body.has(fn) for fn in TRANSCENDENTAL_FUNCS)
    has_complex = bool(body.has(sp.I))

    poly_degree: int | None = None
    var_sym = parse_symbol(target_var) if target_var else (free_syms[0] if len(free_syms) == 1 else None)
    if var_sym is not None and not has_transcendental:
        try:
            poly = sp.Poly(sp.together(body), var_sym)
            if poly.is_univariate:
                poly_degree = int(poly.degree())
        except Exception:
            poly_degree = None

    features = {
        "is_equation": is_eq,
        "has_transcendental_functions": has_transcendental,
        "has_complex_constants": has_complex,
        "polynomial_degree": poly_degree,
    }

    if is_eq:
        if has_transcendental:
            return "transcendental_equation", features
        if poly_degree == 1:
            return "linear_equation", features
        if poly_degree == 2:
            return "quadratic_equation", features
        if poly_degree is not None and poly_degree > 2:
            return "polynomial_equation", features
        return "algebraic_equation", features

    if has_complex:
        return "complex_expression", features
    _, denom = sp.fraction(sp.together(body))
    if denom != 1:
        return "rational_expression", features
    if poly_degree is not None:
        return "polynomial_expression", features
    return "algebraic_expression", features


def classify_problem(
    operation: str | None,
    expression: str | None,
    variable: str | None = None,
    options: dict[str, Any] | None = None,
    assumptions: dict[str, str] | None = None,
) -> ClassificationResult:
    """Deterministically classify a mathematical request into domain, problem type, and features."""
    opts = options or {}
    op_key = operation.strip().lower() if operation else None
    domain = OPERATION_DOMAIN_MAP.get(op_key or "", "")

    # Matrix / Linear Algebra classification
    raw_matrix = opts.get("matrix_a") if opts.get("matrix_a") is not None else opts.get("matrix")
    raw_matrix_b = opts.get("matrix_b")
    if domain == "linear_algebra" or raw_matrix is not None:
        mat_a = parse_matrix(raw_matrix, assumptions=assumptions) if raw_matrix is not None else None
        mat_b = parse_matrix(raw_matrix_b, assumptions=assumptions) if raw_matrix_b is not None else None
        features: dict[str, Any] = {}
        if mat_a is not None:
            features["matrix_shape"] = [mat_a.rows, mat_a.cols]
            features["is_square"] = mat_a.rows == mat_a.cols
        if mat_b is not None:
            features["matrix_b_shape"] = [mat_b.rows, mat_b.cols]

        if mat_b is not None:
            ptype = "binary_matrix_operation"
        elif mat_a is not None and mat_a.rows == mat_a.cols:
            ptype = "square_matrix_analysis"
        else:
            ptype = "rectangular_matrix_analysis"

        return ClassificationResult(
            domain="linear_algebra",
            problem_type=ptype,
            features=features,
            parsed_matrix=mat_a,
            parsed_matrix_b=mat_b,
        )

    # Expression-based classification
    parsed: sp.Basic | sp.Eq | None = None
    if expression and expression.strip():
        if op_key in ("solve", "root_find", "nsolve") or (not op_key and "=" in expression):
            parsed = parse_math_input(expression, assumptions=assumptions)
        else:
            parsed = parse_math_expression(expression, assumptions=assumptions)

    if parsed is None:
        return ClassificationResult(domain=domain or "unknown", problem_type="unspecified_problem")

    free_vars = sorted(s.name for s in parsed.free_symbols)

    if not domain:
        domain = "algebra"

    if domain == "calculus":
        if op_key in ("differentiate", "diff", "derivative"):
            order = opts.get("order", 1)
            ptype = "higher_order_derivative" if isinstance(order, int) and order > 1 else "symbolic_derivative"
        elif op_key in ("integrate", "int", "integral"):
            has_bounds = opts.get("lower") is not None and opts.get("upper") is not None
            ptype = "definite_integral" if has_bounds else "indefinite_integral"
        elif op_key == "limit":
            ptype = "symbolic_limit"
        else:
            ptype = "calculus_problem"
        return ClassificationResult(
            domain="calculus",
            problem_type=ptype,
            variables=free_vars,
            features={"has_transcendental_functions": any(parsed.has(fn) for fn in TRANSCENDENTAL_FUNCS)},
            parsed_expr=parsed,
        )

    if domain == "numerical":
        if op_key in ("root_find", "nsolve"):
            ptype = "numerical_root_finding"
        elif op_key in ("numerical_integrate", "quad"):
            ptype = "numerical_quadrature"
        else:
            ptype = "numerical_evaluation"
        return ClassificationResult(
            domain="numerical",
            problem_type=ptype,
            variables=free_vars,
            features={"is_equation": isinstance(parsed, sp.Eq)},
            parsed_expr=parsed,
        )

    ptype, alg_features = _classify_algebra_expr(parsed, variable)
    return ClassificationResult(
        domain="algebra",
        problem_type=ptype,
        variables=free_vars,
        features=alg_features,
        parsed_expr=parsed,
    )
