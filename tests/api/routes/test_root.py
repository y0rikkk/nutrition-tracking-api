"""Tests for root API endpoints."""

from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    """Test GET / returns {"project": "nutrition_tracking_api"}."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"project": "nutrition_tracking_api"}


def test_healthz_returns_ok(client: TestClient) -> None:
    """Test GET /healthz returns 200 with status ok."""
    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_readyz_returns_ok(client: TestClient) -> None:
    """Test GET /readyz returns 200 with status ok."""
    response = client.get("/readyz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_metrics_endpoint_exists(client: TestClient) -> None:
    """Test GET /metrics returns Prometheus metrics."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
