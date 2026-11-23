"""API integration tests for health and computation endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_list_operations_endpoint():
    response = client.get("/api/v1/compute/operations")
    assert response.status_code == 200
    names = {op["name"] for op in response.json()}
    assert {"simplify", "differentiate", "integrate", "solve", "matrix_eigenvalues"} <= names


def test_compute_endpoint_success():
    response = client.post(
        "/api/v1/compute",
        json={"operation": "differentiate", "expression": "x^3 + 2*x"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "differentiate"
    assert body["result"] == "3*x^2 + 2"
    assert body["metadata"]["domain"] == "calculus"


def test_compute_endpoint_rejects_malicious_expression():
    response = client.post(
        "/api/v1/compute",
        json={"operation": "simplify", "expression": "__import__('os').system('ls')"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_EXPRESSION"


def test_compute_endpoint_rejects_unsupported_operation():
    response = client.post(
        "/api/v1/compute",
        json={"operation": "arbitrary_shell", "expression": "1 + 1"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "UNSUPPORTED_OPERATION"
