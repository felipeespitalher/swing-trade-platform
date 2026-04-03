"""
HTTP request/response logging middleware.

Logs all HTTP requests and responses with timing information,
request IDs for trace correlation, and user identification.
"""

import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Features:
    - Generates/propagates request IDs for trace correlation
    - Logs request details (method, path, query params)
    - Tracks request duration
    - Logs response status and duration
    - Includes user ID from JWT when authenticated
    """

    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request/response with logging.

        Args:
            request: The incoming HTTP request
            call_next: Callable to process the request

        Returns:
            Response: The HTTP response
        """
        # Generate or retrieve request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Extract user ID from token if authenticated
        user_id = self._extract_user_id(request)

        # Start timing
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query if request.url.query else None,
                "user_id": user_id,
                "client_ip": self._get_client_ip(request),
            },
        )

        try:
            # Process request
            response = await call_next(request)
            duration = time.time() - start_time

            # Log successful response
            logger.info(
                f"Request completed: {request.method} {request.url.path} {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 3),
                    "duration_ms": round(duration * 1000, 2),
                    "user_id": user_id,
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "duration_seconds": round(duration, 3),
                    "duration_ms": round(duration * 1000, 2),
                    "user_id": user_id,
                },
                exc_info=True,
            )

            raise

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extract client IP from request.

        Checks X-Forwarded-For header for proxied requests.

        Args:
            request: The HTTP request

        Returns:
            str: Client IP address
        """
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _extract_user_id(request: Request) -> Optional[str]:
        """
        Extract user ID from JWT token in Authorization header.

        Args:
            request: The HTTP request

        Returns:
            Optional[str]: User ID if authenticated, None otherwise
        """
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return None

        try:
            # Import here to avoid circular imports
            from app.core.security import decode_token

            token = auth_header.replace("Bearer ", "").strip()
            payload = decode_token(token)
            return payload.get("sub")
        except Exception:
            # Invalid or expired token
            return None
