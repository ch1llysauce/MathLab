"""Approved mathematical operation registry and dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.exceptions import InvalidExpressionError, UnsupportedOperationError
from app.core.security import run_with_timeout
from app.modules.math_engine.algebra.operations import (
    expand_expr,
    factor_expr,
    simplify_expr,
    solve_equation,
)
from app.modules.math_engine.calculus.operations import (
    differentiate_expr,
    integrate_expr,
    limit_expr,
    partial_derivative_expr,
    solve_ode_expr,
    taylor_series_expr,
)
from app.modules.math_engine.linear_algebra.operations import (
    linear_system_solve,
    matrix_add,
    matrix_determinant,
    matrix_eigenvalues,
    matrix_eigenvectors,
    matrix_inverse,
    matrix_multiply,
    matrix_rank,
    matrix_rref,
    matrix_transpose,
)
from app.modules.math_engine.numerical.operations import (
    numerical_eval,
    numerical_integrate,
    root_find,
)


@dataclass(frozen=True)
class OperationSpec:
    """Metadata and handler for a whitelisted mathematical operation."""

    name: str
    domain: str
    description: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    aliases: tuple[str, ...] = ()


def _require_str(payload: dict[str, Any], field: str) -> str:
    val = payload.get(field)
    if not isinstance(val, str) or not val.strip():
        raise InvalidExpressionError(f"Field '{field}' is required and must be a non-empty string.")
    return val


def _handle_simplify(p: dict[str, Any]) -> dict[str, Any]:
    return simplify_expr(_require_str(p, "expression"), assumptions=p.get("assumptions"))


def _handle_expand(p: dict[str, Any]) -> dict[str, Any]:
    return expand_expr(_require_str(p, "expression"), assumptions=p.get("assumptions"))


def _handle_factor(p: dict[str, Any]) -> dict[str, Any]:
    return factor_expr(_require_str(p, "expression"), assumptions=p.get("assumptions"))


def _handle_solve(p: dict[str, Any]) -> dict[str, Any]:
    return solve_equation(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        assumptions=p.get("assumptions"),
    )


def _handle_differentiate(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return differentiate_expr(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        order=opts.get("order", 1),
        assumptions=p.get("assumptions"),
    )


def _handle_integrate(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return integrate_expr(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        lower=opts.get("lower"),
        upper=opts.get("upper"),
        assumptions=p.get("assumptions"),
    )


def _handle_limit(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return limit_expr(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        point=opts.get("point", "0"),
        direction=opts.get("direction", "+-"),
        assumptions=p.get("assumptions"),
    )


def _handle_partial_derivative(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return partial_derivative_expr(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        variables=opts.get("variables"),
        order=opts.get("order", 1),
        assumptions=p.get("assumptions"),
    )


def _handle_taylor_series(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return taylor_series_expr(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        point=opts.get("point", "0"),
        order=opts.get("order", 5),
        assumptions=p.get("assumptions"),
    )


def _handle_solve_ode(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return solve_ode_expr(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        dependent=opts.get("dependent"),
        ics=opts.get("ics"),
        assumptions=p.get("assumptions"),
    )


def _handle_linear_system(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    matrix = opts.get("matrix")
    vector = opts.get("vector")
    if matrix is None or vector is None:
        raise InvalidExpressionError("Fields 'options.matrix' and 'options.vector' are required.")
    return linear_system_solve(matrix, vector, assumptions=p.get("assumptions"))


def _handle_matrix_op(fn: Callable[..., dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _runner(p: dict[str, Any]) -> dict[str, Any]:
        opts = p.get("options") or {}
        matrix = opts.get("matrix")
        if matrix is None:
            raise InvalidExpressionError("Field 'options.matrix' is required for matrix operations.")
        return fn(matrix, assumptions=p.get("assumptions"))

    return _runner


def _handle_binary_matrix_op(fn: Callable[..., dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _runner(p: dict[str, Any]) -> dict[str, Any]:
        opts = p.get("options") or {}
        matrix_a = opts.get("matrix_a") or opts.get("matrix")
        matrix_b = opts.get("matrix_b")
        if matrix_a is None or matrix_b is None:
            raise InvalidExpressionError("Fields 'options.matrix_a' and 'options.matrix_b' are required.")
        return fn(matrix_a, matrix_b, assumptions=p.get("assumptions"))

    return _runner


def _handle_numerical_eval(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return numerical_eval(
        _require_str(p, "expression"),
        precision=opts.get("precision", 15),
        substitutions=opts.get("substitutions"),
        assumptions=p.get("assumptions"),
    )


def _handle_root_find(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    return root_find(
        _require_str(p, "expression"),
        variable=p.get("variable"),
        initial_guess=opts.get("initial_guess"),
        bracket=opts.get("bracket"),
        assumptions=p.get("assumptions"),
    )


def _handle_numerical_integrate(p: dict[str, Any]) -> dict[str, Any]:
    opts = p.get("options") or {}
    if opts.get("lower") is None or opts.get("upper") is None:
        raise InvalidExpressionError("Fields 'options.lower' and 'options.upper' are required.")
    return numerical_integrate(
        _require_str(p, "expression"),
        lower=opts["lower"],
        upper=opts["upper"],
        variable=p.get("variable"),
        assumptions=p.get("assumptions"),
    )


class OperationRegistry:
    """Registry of approved mathematical operations."""

    def __init__(self, specs: list[OperationSpec]) -> None:
        self._specs: dict[str, OperationSpec] = {}
        self._aliases: dict[str, str] = {}
        for spec in specs:
            self._specs[spec.name] = spec
            self._aliases[spec.name] = spec.name
            for alias in spec.aliases:
                self._aliases[alias] = spec.name

    def resolve(self, operation_name: str) -> OperationSpec:
        key = operation_name.strip().lower()
        canonical = self._aliases.get(key)
        if not canonical:
            raise UnsupportedOperationError(
                f"Operation '{operation_name}' is not in the approved mathematical registry.",
                details={"supported_operations": sorted(self._specs.keys())},
            )
        return self._specs[canonical]

    def list_operations(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "domain": spec.domain,
                "description": spec.description,
                "aliases": list(spec.aliases),
            }
            for spec in self._specs.values()
        ]

    def execute(self, operation_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        spec = self.resolve(operation_name)
        output = run_with_timeout(spec.handler, payload)
        return {"canonical_operation": spec.name, "domain": spec.domain, **output}


OPERATION_REGISTRY = OperationRegistry(
    [
        OperationSpec("simplify", "algebra", "Symbolically simplify an expression.", _handle_simplify),
        OperationSpec("expand", "algebra", "Algebraically expand an expression.", _handle_expand),
        OperationSpec("factor", "algebra", "Factor an algebraic expression.", _handle_factor),
        OperationSpec("solve", "algebra", "Solve an algebraic equation or expression.", _handle_solve),
        OperationSpec(
            "differentiate",
            "calculus",
            "Compute the symbolic derivative.",
            _handle_differentiate,
            aliases=("diff", "derivative"),
        ),
        OperationSpec(
            "integrate",
            "calculus",
            "Compute a symbolic indefinite or definite integral.",
            _handle_integrate,
            aliases=("int", "integral"),
        ),
        OperationSpec("limit", "calculus", "Compute a symbolic limit.", _handle_limit),
        OperationSpec(
            "partial_derivative",
            "calculus",
            "Compute a partial or mixed partial derivative.",
            _handle_partial_derivative,
            aliases=("partial", "pdiff"),
        ),
        OperationSpec(
            "taylor_series",
            "calculus",
            "Compute a Taylor polynomial expansion.",
            _handle_taylor_series,
            aliases=("taylor", "series"),
        ),
        OperationSpec(
            "solve_ode",
            "calculus",
            "Solve a 1st or 2nd order ordinary differential equation.",
            _handle_solve_ode,
            aliases=("ode", "dsolve"),
        ),
        OperationSpec(
            "linear_system_solve",
            "linear_algebra",
            "Solve a linear system Ax = b.",
            _handle_linear_system,
            aliases=("solve_system", "linsolve"),
        ),
        OperationSpec(
            "matrix_determinant",
            "linear_algebra",
            "Compute the determinant of a square matrix.",
            _handle_matrix_op(matrix_determinant),
            aliases=("det", "determinant"),
        ),
        OperationSpec(
            "matrix_rank",
            "linear_algebra",
            "Compute the rank of a matrix.",
            _handle_matrix_op(matrix_rank),
            aliases=("rank",),
        ),
        OperationSpec(
            "matrix_transpose",
            "linear_algebra",
            "Compute the transpose of a matrix.",
            _handle_matrix_op(matrix_transpose),
            aliases=("transpose",),
        ),
        OperationSpec(
            "matrix_inverse",
            "linear_algebra",
            "Compute the inverse of a square matrix.",
            _handle_matrix_op(matrix_inverse),
            aliases=("inverse", "inv"),
        ),
        OperationSpec(
            "matrix_rref",
            "linear_algebra",
            "Compute the reduced row echelon form (RREF).",
            _handle_matrix_op(matrix_rref),
            aliases=("rref",),
        ),
        OperationSpec(
            "matrix_eigenvalues",
            "linear_algebra",
            "Compute eigenvalues of a square matrix.",
            _handle_matrix_op(matrix_eigenvalues),
            aliases=("eigenvalues",),
        ),
        OperationSpec(
            "matrix_eigenvectors",
            "linear_algebra",
            "Compute eigenvalues and eigenvectors of a square matrix.",
            _handle_matrix_op(matrix_eigenvectors),
            aliases=("eigenvectors",),
        ),
        OperationSpec(
            "matrix_add",
            "linear_algebra",
            "Add two matrices.",
            _handle_binary_matrix_op(matrix_add),
        ),
        OperationSpec(
            "matrix_multiply",
            "linear_algebra",
            "Multiply two matrices.",
            _handle_binary_matrix_op(matrix_multiply),
        ),
        OperationSpec(
            "numerical_eval",
            "numerical",
            "Evaluate an expression numerically.",
            _handle_numerical_eval,
            aliases=("evalf", "evaluate"),
        ),
        OperationSpec(
            "root_find",
            "numerical",
            "Find a numerical root using Brent's method or nsolve.",
            _handle_root_find,
            aliases=("nsolve",),
        ),
        OperationSpec(
            "numerical_integrate",
            "numerical",
            "Compute a definite numerical integral using adaptive quadrature.",
            _handle_numerical_integrate,
            aliases=("quad",),
        ),
    ]
)
