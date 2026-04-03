"""
Health check and metrics API endpoints.

Provides endpoints for:
- GET /health - Basic health status
- GET /metrics - Application metrics
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from app.services.monitoring import MonitoringService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Get application health status.

    Returns:
        Dict[str, Any]: Health status with component statuses

    Example response:
        {
            "status": "healthy",
            "timestamp": "2026-04-02T12:30:45.123456",
            "uptime_seconds": 1234.56,
            "components": {
                "database": "healthy",
                "api": "healthy"
            }
        }
    """
    health = await MonitoringService.get_health_status()
    logger.debug("Health check performed", extra={"status": health["status"]})
    return health


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics() -> Dict[str, Any]:
    """
    Get application metrics.

    Returns:
        Dict[str, Any]: Metrics including uptime, request counts, error rates

    Example response:
        {
            "timestamp": "2026-04-02T12:30:45.123456",
            "uptime": {
                "seconds": 1234.56,
                "minutes": 20.58,
                "hours": 0.34
            },
            "requests": {
                "total": 150,
                "rate_per_minute": 7.29
            },
            "errors": {
                "total": 2,
                "rate": 0.013,
                "last_error": null
            },
            "environment": {
                "app_name": "Swing Trade Automation Platform API",
                "app_version": "0.1.0",
                "environment": "development",
                "debug": true
            }
        }
    """
    metrics = await MonitoringService.get_metrics()
    logger.debug("Metrics requested", extra={"requests": metrics["requests"]["total"]})
    return metrics


@router.get("/metrics/detailed", response_model=Dict[str, Any])
async def get_detailed_metrics() -> Dict[str, Any]:
    """
    Get detailed metrics including health status.

    Returns:
        Dict[str, Any]: Comprehensive metrics with health information

    Includes all metrics from /metrics plus detailed health status.
    """
    detailed_metrics = await MonitoringService.get_detailed_metrics()
    logger.debug("Detailed metrics requested")
    return detailed_metrics


@router.get("/metrics/database", response_model=Dict[str, Any])
async def check_database_health() -> Dict[str, Any]:
    """
    Check database connection and health.

    Returns:
        Dict[str, Any]: Database connection status

    Example response:
        {
            "status": "connected",
            "database_url": "***hidden***",
            "timestamp": "2026-04-02T12:30:45.123456"
        }
    """
    db_status = await MonitoringService.check_database_connection()
    logger.debug(f"Database health check: {db_status['status']}")
    return db_status
