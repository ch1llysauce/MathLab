"""Unit, integration, and security tests for the M2 Intelligent Mathematical Reasoning Engine."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.reasoning_engine.analyzer import analyze_mathematical_problem

client = TestClient(app)


class TestProblemClassification:
    def test_classify_quadratic_equation(self):
        analysis = analyze_mathematical_problem(
            operation="solve",
            expression="x^2 - 5*x + 6 = 0",
        )
        assert analysis["classification"]["domain"] == "algebra"
        assert analysis["classification"]["problem_type"] == "quadratic_equation"
        assert analysis["classification"]["features"]["polynomial_degree"] == 2
        assert analysis["selection"]["recommended_method"] == "symbolic_solve"
        assert analysis["selection"]["applicable"] is True

    def test_classify_transcendental_equation_with_fallback_candidate(self):
        analysis = analyze_mathematical_problem(
            operation="solve",
            expression="cos(x) - x = 0",
        )
        assert analysis["classification"]["problem_type"] == "transcendental_equation"
        candidates = {c["operation"] for c in analysis["selection"]["candidates"]}
        assert {"solve", "root_find"} <= candidates

    def test_classify_definite_vs_indefinite_integral(self):
        indef = analyze_mathematical_problem(operation="integrate", expression="2*x")
        assert indef["classification"]["problem_type"] == "indefinite_integral"
        assert indef["selection"]["recommended_method"] == "symbolic_indefinite_integration"

        definite = analyze_mathematical_problem(
            operation="integrate",
            expression="x^2",
            options={"lower": 0, "upper": 3},
        )
        assert definite["classification"]["problem_type"] == "definite_integral"
        assert definite["selection"]["recommended_method"] == "symbolic_definite_integration"


class TestRuleEvaluationAndMethodSelection:
    def test_non_elementary_definite_integral_falls_back_to_quadrature(self):
        analysis = analyze_mathematical_problem(
            operation="integrate",
            expression="exp(cos(x))",
            variable="x",
            options={"lower": 0, "upper": 1},
        )
        assert analysis["selection"]["applicable"] is True
        assert analysis["selection"]["recommended_operation"] == "numerical_integrate"
        assert analysis["selection"]["recommended_method"] == "scipy_quad"

    def test_singular_matrix_inverse_flagged_inapplicable(self):
        analysis = analyze_mathematical_problem(
            operation="matrix_inverse",
            options={"matrix": [[1, 2], [2, 4]]},
        )
        assert analysis["selection"]["applicable"] is False
        failed_ids = {r["rule_id"] for r in analysis["rules"] if not r["passed"]}
        assert "nonsingular_matrix_required" in failed_ids

    def test_nonsquare_matrix_determinant_flagged_inapplicable(self):
        analysis = analyze_mathematical_problem(
            operation="matrix_determinant",
            options={"matrix": [[1, 2, 3], [4, 5, 6]]},
        )
        assert analysis["selection"]["applicable"] is False
        failed_ids = {r["rule_id"] for r in analysis["rules"] if not r["passed"]}
        assert "square_matrix_required" in failed_ids

    def test_root_find_bracket_sign_change_check(self):
        valid = analyze_mathematical_problem(
            operation="root_find",
            expression="x^2 - 2",
            options={"bracket": [1, 2]},
        )
        assert valid["selection"]["applicable"] is True
        assert valid["selection"]["recommended_method"] == "scipy_brentq"

        invalid = analyze_mathematical_problem(
            operation="root_find",
            expression="x^2 - 2",
            options={"bracket": [2, 3]},
        )
        assert invalid["selection"]["applicable"] is False
        failed_ids = {r["rule_id"] for r in invalid["rules"] if not r["passed"]}
        assert "bracket_sign_change" in failed_ids


class TestAssumptionsAndConstraints:
    def test_extracts_denominator_sqrt_and_log_constraints(self):
        analysis = analyze_mathematical_problem(
            operation="simplify",
            expression="log(x) + sqrt(x + 1)/(x - 2)",
            assumptions={"x": "real"},
        )
        assert analysis["assumptions"]["declared"] == {"x": "real"}
        conditions = {c["condition"] for c in analysis["assumptions"]["constraints"]}
        assert "x - 2 != 0" in conditions
        assert "x > 0 (over reals)" in conditions
        assert "x + 1 >= 0 (over reals)" in conditions


class TestReasoningAPI:
    def test_reasoning_analyze_endpoint(self):
        response = client.post(
            "/api/v1/reasoning/analyze",
            json={
                "operation": "integrate",
                "expression": "exp(cos(x))",
                "variable": "x",
                "options": {"lower": 0, "upper": 1},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["classification"]["domain"] == "calculus"
        assert body["selection"]["recommended_operation"] == "numerical_integrate"
        assert body["selection"]["recommended_method"] == "scipy_quad"

    def test_reasoning_endpoint_rejects_malicious_input(self):
        response = client.post(
            "/api/v1/reasoning/analyze",
            json={"operation": "simplify", "expression": "__import__('os').system('ls')"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_EXPRESSION"

    def test_compute_endpoint_includes_reasoning_metadata(self):
        response = client.post(
            "/api/v1/compute",
            json={"operation": "solve", "expression": "x^2 - 5*x + 6 = 0"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result"] == "x = 2, 3"
        assert body["reasoning"]["classification"]["problem_type"] == "quadratic_equation"
        assert body["reasoning"]["selection"]["recommended_method"] == "symbolic_solve"
