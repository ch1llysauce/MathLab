"""Unit, integration, LLM-guardrail, and security tests for the M6 AI Engine."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.ai_engine.explainer import generate_grounded_explanation
from app.modules.ai_engine.nl_parser import interpret_natural_language

client = TestClient(app)


class TestNaturalLanguageInterpretation:
    def test_interprets_calculus_and_algebra_prompts(self):
        diff_req = interpret_natural_language("differentiate x^3 + 2*x")
        assert diff_req["operation"] == "differentiate"
        assert diff_req["expression"] == "x^3 + 2*x"

        int_req = interpret_natural_language("integrate x^2 from 0 to 3")
        assert int_req["operation"] == "integrate"
        assert int_req["options"] == {"lower": "0", "upper": "3"}

        solve_req = interpret_natural_language("solve x^2 - 5*x + 6 = 0")
        assert solve_req["operation"] == "solve"
        assert solve_req["expression"] == "x^2 - 5*x + 6 = 0"

        leibniz_req = interpret_natural_language("d/dx (x^3 + 2*x)")
        assert leibniz_req["operation"] == "differentiate"
        assert leibniz_req["variable"] == "x"

        dx_req = interpret_natural_language("integrate x^2 dx")
        assert dx_req["operation"] == "integrate"
        assert dx_req["expression"] == "x^2"
        assert dx_req["variable"] == "x"

        mac_req = interpret_natural_language("maclaurin series of sin(x) order 5")
        assert mac_req["operation"] == "taylor_series"
        assert mac_req["options"] == {"point": "0", "order": 5}

        lim_req = interpret_natural_language("limit as x -> 1 of (x^2 - 1)/(x - 1)")
        assert lim_req["operation"] == "limit"
        assert lim_req["variable"] == "x"
        assert lim_req["options"] == {"point": "1"}

    def test_llm_translation_validates_against_whitelist_and_parser(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_api_key", "test-key")

        # Valid JSON returned by LLM for an unrecognized phrasing
        with patch(
            "app.modules.ai_engine.nl_parser.call_llm_chat",
            return_value='{"operation": "factor", "expression": "x^2 - 9", "variable": null, "options": {}}',
        ):
            parsed = interpret_natural_language("please break apart x^2 - 9 into factors")
            assert parsed["operation"] == "factor"
            assert parsed["interpretation_source"] == "llm_translated"

        # Malicious LLM-proposed operation must be rejected
        with patch(
            "app.modules.ai_engine.nl_parser.call_llm_chat",
            return_value='{"operation": "exec_shell", "expression": "1+1"}',
        ):
            response = client.post(
                "/api/v1/ai/explain",
                json={"prompt": "do something weird with 1+1"},
            )
            assert response.status_code == 400
            assert response.json()["error"]["code"] == "UNSUPPORTED_OPERATION"


class TestGroundedExplanationAndModes:
    def test_grounded_explanation_computational_vs_learning_modes(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "none")
        comp = generate_grounded_explanation(
            prompt="differentiate x^3 + 2*x",
            mode="computational",
        )
        learn = generate_grounded_explanation(
            prompt="differentiate x^3 + 2*x",
            mode="learning",
        )
        assert comp["result"] == "3*x^2 + 2"
        assert learn["result"] == "3*x^2 + 2"
        assert comp["verification"]["verified"] is True
        assert learn["verification"]["verified"] is True
        assert len(learn["steps"]) == 5
        assert comp["summary"] != learn["summary"]

    def test_llm_explainer_receives_grounded_result(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "ollama")
        with patch(
            "app.modules.ai_engine.explainer.call_llm_chat",
            return_value="Grounded walkthrough: the quadratic solutions are x = 2, 3.",
        ) as mock_chat:
            res = generate_grounded_explanation(
                prompt="solve x^2 - 5*x + 6 = 0",
                mode="learning",
            )
            assert res["explanation_source"] == "llm_grounded"
            assert res["result"] == "x = 2, 3"
            assert "x = 2, 3" in mock_chat.call_args.args[1]

    def test_llm_explainer_parses_structured_math_steps_and_options(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "openai_compatible")
        monkeypatch.setattr(settings, "llm_api_key", "test-key")
        structured = (
            '{"steps": ['
            '{"title": "Check continuity", "content": "x^3 + 2*x is a polynomial, so substitute x = 5 directly."},'
            '{"title": "Substitute x = 5", "content": "5^3 + 2(5) = 125 + 10 = 135."}'
            '], "summary": "Because polynomials are continuous everywhere, the limit equals f(5) = 135."}'
        )
        with patch("app.modules.ai_engine.explainer.call_llm_chat", return_value=structured) as mock_chat:
            res = generate_grounded_explanation(
                operation="limit",
                expression="x^3 + 2*x",
                variable="x",
                options={"point": "5"},
                mode="learning",
            )
            assert res["explanation_source"] == "llm_grounded"
            assert len(res["steps"]) == 2
            assert res["steps"][0]["title"] == "Check continuity"
            assert "point" in mock_chat.call_args.args[1]
            assert '"5"' in mock_chat.call_args.args[1]


class TestAIEndpointsAndSecurity:
    def test_explain_and_examples_endpoints(self):
        examples_resp = client.get("/api/v1/ai/examples")
        assert examples_resp.status_code == 200
        examples = examples_resp.json()
        assert len(examples) >= 8

        explain_resp = client.post(
            "/api/v1/ai/explain",
            json={"prompt": "integrate x^2 from 0 to 3", "mode": "learning"},
        )
        assert explain_resp.status_code == 200
        body = explain_resp.json()
        assert body["result"] == "9"
        assert body["options"] == {"lower": "0", "upper": "3"}
        assert body["verification"]["status"] == "verified"

    def test_rejects_malicious_prompt(self):
        resp = client.post(
            "/api/v1/ai/explain",
            json={"prompt": "simplify __import__('os').system('ls')"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_EXPRESSION"
