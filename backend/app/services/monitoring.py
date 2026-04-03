"""
Application monitoring service.

Tracks application health, metrics, and performance indicators.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for application monitoring and health checks."""

    # Class-level metrics storage
    _start_time = time.time()
    _request_count = 0
    _error_count = 0
    _last_error: Optional[str] = None

    @classmethod
    def increment_request_count(cls) -> None:
        """Increment total request count."""
        cls._request_count += 1

    @classmethod
    def increment_error_count(cls, error: str = "") -> None:
        """Increment error count and store last error."""
        cls._error_count += 1
        if error:
            cls._last_error = error

    @classmethod
    async def get_health_status(cls) -> Dict[str, Any]:
        """
        Get application health status.

        Checks:
        - Application is running
        - Database connectivity
        - Basic system status

        Returns:
            Dict[str, Any]: Health status object with component statuses
        """
        checks = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": round(time.time() - cls._start_time, 2),
            "components": {
                "database": "unknown",
                "api": "healthy",
            },
        }

        # Check database connectivity
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            checks["components"]["database"] = "healthy"
            logger.debug("Database health check passed")
        except Exception as exc:
            checks["components"]["database"] = "unhealthy"
            checks["status"] = "unhealthy"
            logger.warning(f"Database health check failed: {exc}")

        return checks

    @classmethod
    async def get_metrics(cls) -> Dict[str, Any]:
        """
        Get application metrics.

        Includes:
        - Request counts and rates
        - Error counts and rates
        - Uptime
        - Performance indicators

        Returns:
            Dict[str, Any]: Metrics object
        """
        uptime = time.time() - cls._start_time
        uptime_minutes = uptime / 60

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": {
                "seconds": round(uptime, 2),
                "minutes": round(uptime_minutes, 2),
                "hours": round(uptime_minutes / 60, 2),
            },
            "requests": {
                "total": cls._request_count,
                "rate_per_minute": (
                    round(cls._request_count / uptime_minutes, 2)
                    if uptime_minutes > 0
                    else 0
                ),
            },
            "errors": {
                "total": cls._error_count,
                "rate": (
                    round(cls._error_count / cls._request_count, 3)
                    if cls._request_count > 0
                    else 0
                ),
                "last_error": cls._last_error,
            },
            "environment": {
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug,
            },
        }

        return metrics

    @classmethod
    async def get_detailed_metrics(cls) -> Dict[str, Any]:
        """
        Get detailed metrics including database status.

        Returns:
            Dict[str, Any]: Detailed metrics object
        """
        basic_metrics = await cls.get_metrics()
        health_status = await cls.get_health_status()

        return {
            **basic_metrics,
            "health": health_status,
        }

    @classmethod
    async def check_database_connection(cls) -> Dict[str, Any]:
        """
        Check database connection and basic connectivity.

        Returns:
            Dict[str, Any]: Database health information
        """
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()

            return {
                "status": "connected",
                "database_url": (
                    "***hidden***"
                    if not settings.debug
                    else settings.database_url
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error(f"Database connection check failed: {exc}", exc_info=True)
            return {
                "status": "disconnected",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }
