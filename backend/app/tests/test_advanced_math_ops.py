"""Tests for partial derivatives, Taylor series, ODE solving, and linear systems across M1-M3 & M6."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestPartialDerivative:
    def test_partial_and_mixed_partial_with_verification(self):
        resp = client.post(
            "/api/v1/compute",
            json={
                "operation": "partial_derivative",
                "expression": "x^2 * y + sin(x * y)",
                "variable": "x",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"] == "2*x*y + y*cos(x*y)"
        assert body["reasoning"]["classification"]["problem_type"] == "partial_derivative"
        assert body["verification"]["status"] == "verified"
        assert body["verification"]["verified"] is True

        mixed = client.post(
            "/api/v1/compute",
            json={
                "operation": "partial_derivative",
                "expression": "x^2 * y^3",
                "options": {"variables": ["x", "y"]},
            },
        )
        assert mixed.status_code == 200
        assert mixed.json()["result"] == "6*x*y^2"


class TestTaylorSeries:
    def test_taylor_series_expansion_and_verification(self):
        resp = client.post(
            "/api/v1/compute",
            json={
                "operation": "taylor_series",
                "expression": "sin(x)",
                "variable": "x",
                "options": {"point": 0, "order": 5},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"] == "x^5/120 - x^3/6 + x"
        assert body["reasoning"]["classification"]["problem_type"] == "taylor_series_expansion"
        assert body["verification"]["status"] == "verified"
        assert body["verification"]["verified"] is True

    def test_taylor_rejects_out_of_bounds_order(self):
        resp = client.post(
            "/api/v1/compute",
            json={
                "operation": "taylor_series",
                "expression": "exp(x)",
                "variable": "x",
                "options": {"order": 25},
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_EXPRESSION"


class TestODESolver:
    def test_first_order_ode_with_ics_and_symbolic_verification(self):
        resp = client.post(
            "/api/v1/compute",
            json={
                "operation": "solve_ode",
                "expression": "y' + 2*y = 0",
                "variable": "x",
                "options": {"ics": {"y(0)": 3}},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"] == "y(x) = 3*exp(-2*x)"
        assert body["reasoning"]["classification"]["problem_type"] == "ordinary_differential_equation"
        assert body["verification"]["status"] == "verified"
        assert body["verification"]["verified"] is True

    def test_ode_rejects_malicious_input(self):
        resp = client.post(
            "/api/v1/compute",
            json={
                "operation": "solve_ode",
                "expression": "y' + __import__('os').system('ls') = 0",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_EXPRESSION"


class TestLinearSystemSolver:
    def test_solve_unique_linear_system_and_verify(self):
        resp = client.post(
            "/api/v1/compute",
            json={
                "operation": "linear_system_solve",
                "options": {
                    "matrix": [[2, 1], [1, -1]],
                    "vector": [5, 1],
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"] == "x1 = 2, x2 = 1"
        assert body["reasoning"]["classification"]["problem_type"] == "linear_system_of_equations"
        assert body["verification"]["status"] == "verified"
        assert body["verification"]["verified"] is True

    def test_inconsistent_system_and_dimension_mismatch(self):
        inconsistent = client.post(
            "/api/v1/compute",
            json={
                "operation": "linear_system_solve",
                "options": {"matrix": [[1, 1], [1, 1]], "vector": [2, 5]},
            },
        )
        assert inconsistent.status_code == 200
        assert "No solution" in inconsistent.json()["result"]

        mismatch = client.post(
            "/api/v1/reasoning/analyze",
            json={
                "operation": "linear_system_solve",
                "options": {"matrix": [[1, 2], [3, 4]], "vector": [1, 2, 3]},
            },
        )
        assert mismatch.status_code == 200
        assert mismatch.json()["selection"]["applicable"] is False


class TestNaturalLanguageNewOps:
    def test_nl_taylor_partial_and_ode(self):
        taylor_resp = client.post(
            "/api/v1/ai/explain",
            json={"prompt": "taylor series of cos(x) around 0 order 4"},
        )
        assert taylor_resp.status_code == 200
        assert taylor_resp.json()["operation"] == "taylor_series"
        assert taylor_resp.json()["result"] == "x^4/24 - x^2/2 + 1"

        partial_resp = client.post(
            "/api/v1/ai/explain",
            json={"prompt": "partial derivative of x^2*y with respect to x"},
        )
        assert partial_resp.status_code == 200
        assert partial_resp.json()["result"] == "2*x*y"

        ode_resp = client.post(
            "/api/v1/ai/explain",
            json={"prompt": "solve ode y' - y = 0"},
        )
        assert ode_resp.status_code == 200
        assert "exp(x)" in ode_resp.json()["result"]
