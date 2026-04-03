"""
Tests for the FastAPI main application.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """
    FastAPI test client.
    """
    return TestClient(app)


def test_health_check(client):
    """
    Test the health check endpoint.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert "components" in data
    assert "database" in data["components"]


def test_root_endpoint(client):
    """
    Test the root endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data


def test_health_check_endpoint_exists(client):
    """
    Test that health check endpoint is accessible without errors.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_metrics_endpoint(client):
    """
    Test the metrics endpoint.
    """
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "uptime" in data
    assert "requests" in data
    assert "errors" in data
    assert "environment" in data


def test_request_id_header(client):
    """
    Test that request ID is added to response headers.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
