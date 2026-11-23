"""Unit and security tests for the M1 Mathematical Computation Engine."""

import pytest

from app.core.exceptions import (
    ComputationLimitError,
    DomainError,
    InvalidExpressionError,
    UnsupportedOperationError,
)
from app.modules.math_engine.registry.registry import OPERATION_REGISTRY


def _exec(op: str, **kwargs):
    return OPERATION_REGISTRY.execute(op, kwargs)


class TestAlgebraOperations:
    def test_simplify_and_complex(self):
        res = _exec("simplify", expression="(x^2 - 1)/(x - 1)")
        assert res["result"] == "x + 1"

        complex_res = _exec("simplify", expression="(1 + i)*(1 - i)")
        assert complex_res["result"] == "2"

    def test_expand_and_factor(self):
        expanded = _exec("expand", expression="(x + 2)*(x - 3)")
        assert expanded["result"] == "x^2 - x - 6"

        factored = _exec("factor", expression="x^2 - 5*x + 6")
        assert factored["result"] == "(x - 3)*(x - 2)"

    def test_solve_quadratic(self):
        solved = _exec("solve", expression="x^2 - 5*x + 6 = 0")
        assert solved["result"] == "x = 2, 3"

    def test_implicit_multiplication(self):
        res = _exec("simplify", expression="2x + 3(x + 1)")
        assert res["result"] == "5*x + 3"


class TestCalculusOperations:
    def test_differentiate(self):
        res = _exec("differentiate", expression="x^3 + 2*x")
        assert res["result"] == "3*x^2 + 2"

    def test_integrate_indefinite(self):
        res = _exec("integrate", expression="2*x")
        assert res["result"] == "x^2 + C"

    def test_integrate_definite(self):
        res = _exec("integrate", expression="x^2", variable="x", options={"lower": 0, "upper": 3})
        assert res["result"] == "9"

    def test_limit(self):
        res = _exec("limit", expression="sin(x)/x", variable="x", options={"point": 0})
        assert res["result"] == "1"


class TestLinearAlgebraOperations:
    def test_determinant_and_rank(self):
        matrix = [[1, 2], [3, 4]]
        det = _exec("matrix_determinant", options={"matrix": matrix})
        assert det["result"] == "-2"

        rank = _exec("matrix_rank", options={"matrix": [[1, 2], [2, 4]]})
        assert rank["result"] == "1"

    def test_inverse_and_transpose(self):
        matrix = [[4, 7], [2, 6]]
        inv = _exec("matrix_inverse", options={"matrix": matrix})
        assert inv["details"]["matrix"] == [["3/5", "-7/10"], ["-1/5", "2/5"]]

        tr = _exec("matrix_transpose", options={"matrix": [[1, 2, 3], [4, 5, 6]]})
        assert tr["details"]["shape"] == [3, 2]

    def test_eigenvalues_and_eigenvectors(self):
        matrix = [[2, 0], [0, 3]]
        eigs = _exec("matrix_eigenvalues", options={"matrix": matrix})
        values = {item["value"] for item in eigs["details"]["eigenvalues"]}
        assert values == {"2", "3"}

        vects = _exec("matrix_eigenvectors", options={"matrix": matrix})
        assert len(vects["details"]["eigensystem"]) == 2

    def test_singular_matrix_inverse_rejected(self):
        with pytest.raises(DomainError):
            _exec("matrix_inverse", options={"matrix": [[1, 2], [2, 4]]})


class TestNumericalOperations:
    def test_numerical_eval(self):
        res = _exec("numerical_eval", expression="pi", options={"precision": 6})
        assert res["result"].startswith("3.14159")

    def test_root_find_bracket(self):
        res = _exec("root_find", expression="x^2 - 2", variable="x", options={"bracket": [1, 2]})
        assert abs(res["details"]["root"] - 1.41421356237) < 1e-8

    def test_numerical_integrate(self):
        res = _exec(
            "numerical_integrate",
            expression="exp(-x^2)",
            variable="x",
            options={"lower": 0, "upper": 1},
        )
        assert abs(res["details"]["value"] - 0.7468241328) < 1e-8


class TestSecurityAndValidation:
    @pytest.mark.parametrize(
        "malicious_expr",
        [
            "__import__('os').system('echo pwned')",
            "eval('1 + 1')",
            "open('secret.txt').read()",
            "(lambda x: x + 1)(2)",
            "x.__class__",
            "1; import sys",
        ],
    )
    def test_reject_arbitrary_python_execution(self, malicious_expr: str):
        with pytest.raises(InvalidExpressionError):
            _exec("simplify", expression=malicious_expr)

    def test_reject_unsupported_operation(self):
        with pytest.raises(UnsupportedOperationError):
            _exec("exec_python", expression="1 + 1")

    def test_enforce_expression_length_and_exponent_limits(self):
        with pytest.raises(ComputationLimitError):
            _exec("simplify", expression="x + " * 200 + "1")

        with pytest.raises(ComputationLimitError):
            _exec("simplify", expression="2^100000")
