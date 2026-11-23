"""Unit, API, and security tests for the M3 Verification and Analysis Engine."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.verification_engine.verifier import verify_computation

client = TestClient(app)


class TestSymbolicVerification:
    def test_verify_simplify_and_factor_equivalent(self):
        res = verify_computation(
            operation="factor",
            expression="x^2 - 5*x + 6",
            result="(x - 3)*(x - 2)",
        )
        assert res["status"] == "verified"
        assert res["verified"] is True
        assert res["discrepancy_detected"] is False

    def test_verify_indefinite_integral_via_differentiation(self):
        res = verify_computation(
            operation="integrate",
            expression="2*x",
            result="x^2 + C",
            variable="x",
        )
        assert res["status"] == "verified"
        assert res["verified"] is True

    def test_verify_solve_all_roots(self):
        res = verify_computation(
            operation="solve",
            expression="x^2 - 5*x + 6 = 0",
            result="x = 2, 3",
            variable="x",
        )
        assert res["status"] == "verified"
        assert res["verified"] is True

    def test_verify_matrix_inverse_and_eigenvalues(self):
        inv = verify_computation(
            operation="matrix_inverse",
            result="[[3/5, -7/10], [-1/5, 2/5]]",
            options={
                "matrix": [[4, 7], [2, 6]],
                "result_matrix": [["3/5", "-7/10"], ["-1/5", "2/5"]],
            },
        )
        assert inv["status"] == "verified"
        assert inv["verified"] is True

        eigs = verify_computation(
            operation="matrix_eigenvalues",
            result="2, 3",
            options={
                "matrix": [[2, 0], [0, 3]],
                "details": {"eigenvalues": [{"value": "2"}, {"value": "3"}]},
            },
        )
        assert eigs["status"] == "verified"
        assert eigs["verified"] is True


class TestNumericalAndCrossMethodVerification:
    def test_verify_differentiate_via_finite_difference(self):
        res = verify_computation(
            operation="differentiate",
            expression="x^3 + 2*x",
            result="3*x^2 + 2",
            variable="x",
        )
        assert res["status"] == "verified"
        assert res["verified"] is True

    def test_verify_definite_integral_cross_method(self):
        res = verify_computation(
            operation="integrate",
            expression="x^2",
            result="9",
            variable="x",
            options={"lower": 0, "upper": 3},
        )
        assert res["status"] == "verified"
        assert any(c["name"] == "definite_integral_quadrature_cross_check" and c["passed"] for c in res["checks"])

    def test_verify_numerical_quadrature_returns_numerical_support(self):
        res = verify_computation(
            operation="numerical_integrate",
            expression="exp(-x^2)",
            result="0.746824132812",
            variable="x",
            options={"lower": 0, "upper": 1},
        )
        assert res["status"] == "numerical_support"
        assert res["verified"] is True

    def test_verify_root_find_residual_returns_numerical_support(self):
        res = verify_computation(
            operation="root_find",
            expression="x^2 - 2",
            result="x = 1.41421356237",
            variable="x",
        )
        assert res["status"] == "numerical_support"
        assert res["verified"] is True


class TestDiscrepancyAndPartialDetection:
    def test_refutes_wrong_derivative(self):
        res = verify_computation(
            operation="differentiate",
            expression="x^3 + 2*x",
            result="3*x^2",
            variable="x",
        )
        assert res["verified"] is False
        assert res["discrepancy_detected"] is True
        assert res["status"] == "inconclusive"

    def test_partial_when_one_root_valid_and_one_invalid(self):
        res = verify_computation(
            operation="solve",
            expression="x^2 - 5*x + 6 = 0",
            result="x = 2, 99",
            variable="x",
        )
        assert res["status"] == "partial"
        assert res["verified"] is False
        assert res["discrepancy_detected"] is True


class TestVerificationAPI:
    def test_verification_endpoint_success(self):
        response = client.post(
            "/api/v1/verification/check",
            json={
                "operation": "integrate",
                "expression": "2*x",
                "result": "x^2 + C",
                "variable": "x",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "verified"
        assert body["verified"] is True

    def test_verification_endpoint_rejects_malicious_input(self):
        response = client.post(
            "/api/v1/verification/check",
            json={
                "operation": "simplify",
                "expression": "__import__('os').system('ls')",
                "result": "1",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_EXPRESSION"

    def test_compute_endpoint_includes_verification_summary(self):
        response = client.post(
            "/api/v1/compute",
            json={"operation": "matrix_inverse", "options": {"matrix": [[4, 7], [2, 6]]}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["verification"]["status"] == "verified"
        assert body["verification"]["verified"] is True
