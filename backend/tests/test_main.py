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
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    response = client.get("/health")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
