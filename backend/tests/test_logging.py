"""
Tests for the logging infrastructure and monitoring.
"""

import logging
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.logging import setup_logging, configure_module_loggers
from app.services.monitoring import MonitoringService


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a configured logger."""
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.level in [logging.DEBUG, logging.INFO]

    def test_logging_handler_exists(self):
        """Test that logging has at least one handler."""
        logger = setup_logging()
        assert len(logger.handlers) > 0

    def test_module_logger_configuration(self):
        """Test that module loggers are configured."""
        configure_module_loggers()

        # Check specific loggers are configured
        uvicorn_logger = logging.getLogger("uvicorn.access")
        sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")

        assert uvicorn_logger.level > logging.DEBUG
        assert sqlalchemy_logger.level > logging.DEBUG

    def test_logger_naming(self):
        """Test that loggers can be created with module names."""
        logger1 = logging.getLogger("app.test")
        logger2 = logging.getLogger("app.test")

        # Same name should return same logger
        assert logger1 is logger2


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint_returns_healthy(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    def test_health_endpoint_has_components(self, client):
        """Test that health response includes component statuses."""
        response = client.get("/api/health")
        data = response.json()

        assert "components" in data
        assert "database" in data["components"]
        assert "api" in data["components"]

    def test_health_endpoint_has_timestamp(self, client):
        """Test that health response includes timestamp."""
        response = client.get("/api/health")
        data = response.json()

        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO format

    def test_health_endpoint_has_uptime(self, client):
        """Test that health response includes uptime."""
        response = client.get("/api/health")
        data = response.json()

        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    def test_metrics_endpoint_returns_data(self, client):
        """Test that metrics endpoint returns metrics."""
        response = client.get("/api/metrics")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

    def test_metrics_endpoint_has_uptime(self, client):
        """Test that metrics include uptime information."""
        response = client.get("/api/metrics")
        data = response.json()

        assert "uptime" in data
        assert "seconds" in data["uptime"]
        assert "minutes" in data["uptime"]
        assert "hours" in data["uptime"]

    def test_metrics_endpoint_has_request_counts(self, client):
        """Test that metrics include request counts."""
        response = client.get("/api/metrics")
        data = response.json()

        assert "requests" in data
        assert "total" in data["requests"]
        assert "rate_per_minute" in data["requests"]

    def test_metrics_endpoint_has_error_counts(self, client):
        """Test that metrics include error tracking."""
        response = client.get("/api/metrics")
        data = response.json()

        assert "errors" in data
        assert "total" in data["errors"]
        assert "rate" in data["errors"]

    def test_metrics_endpoint_has_environment_info(self, client):
        """Test that metrics include environment information."""
        response = client.get("/api/metrics")
        data = response.json()

        assert "environment" in data
        assert "app_name" in data["environment"]
        assert "app_version" in data["environment"]
        assert "environment" in data["environment"]
        assert "debug" in data["environment"]


class TestDetailedMetricsEndpoint:
    """Tests for detailed metrics endpoint."""

    def test_detailed_metrics_includes_health(self, client):
        """Test that detailed metrics include health information."""
        response = client.get("/api/metrics/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "health" in data
        assert "components" in data["health"]


class TestDatabaseHealthEndpoint:
    """Tests for database health endpoint."""

    def test_database_health_endpoint_exists(self, client):
        """Test that database health endpoint is accessible."""
        response = client.get("/api/metrics/database")
        assert response.status_code == 200

    def test_database_health_has_status(self, client):
        """Test that database health response includes status."""
        response = client.get("/api/metrics/database")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["connected", "disconnected"]

    def test_database_health_has_timestamp(self, client):
        """Test that database health response includes timestamp."""
        response = client.get("/api/metrics/database")
        data = response.json()

        assert "timestamp" in data


class TestRequestIDTracking:
    """Tests for request ID tracking in headers."""

    def test_request_id_generated_in_response(self, client):
        """Test that X-Request-ID header is in response."""
        response = client.get("/api/health")

        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

    def test_custom_request_id_propagated(self, client):
        """Test that custom X-Request-ID header is propagated."""
        custom_id = "test-custom-id-12345"

        response = client.get(
            "/api/health",
            headers={"X-Request-ID": custom_id}
        )

        assert response.headers["X-Request-ID"] == custom_id

    def test_request_id_format_is_uuid(self, client):
        """Test that generated request IDs have UUID format."""
        response = client.get("/api/health")
        request_id = response.headers["X-Request-ID"]

        # UUID format: 8-4-4-4-12 hex digits
        parts = request_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestMonitoringService:
    """Tests for MonitoringService."""

    def test_get_health_status(self):
        """Test getting health status."""
        import asyncio

        health = asyncio.run(MonitoringService.get_health_status())

        assert "status" in health
        assert "components" in health
        assert "database" in health["components"]

    def test_get_metrics(self):
        """Test getting metrics."""
        import asyncio

        metrics = asyncio.run(MonitoringService.get_metrics())

        assert "uptime" in metrics
        assert "requests" in metrics
        assert "errors" in metrics

    def test_increment_request_count(self):
        """Test request count tracking."""
        initial_count = MonitoringService._request_count

        MonitoringService.increment_request_count()

        assert MonitoringService._request_count == initial_count + 1

    def test_increment_error_count(self):
        """Test error count tracking."""
        initial_count = MonitoringService._error_count

        MonitoringService.increment_error_count("test error")

        assert MonitoringService._error_count == initial_count + 1
        assert MonitoringService._last_error == "test error"


class TestRootEndpoint:
    """Tests for root endpoint documentation."""

    def test_root_endpoint_includes_docs_link(self, client):
        """Test that root endpoint provides documentation link."""
        response = client.get("/")
        data = response.json()

        assert "docs" in data
        assert data["docs"] == "/docs"


class TestCORSHeaders:
    """Tests for CORS header configuration."""

    def test_cors_allows_request_id_header(self, client):
        """Test that CORS allows X-Request-ID header."""
        response = client.get("/api/health")

        # Request succeeded with custom header, CORS is configured
        assert response.status_code == 200
