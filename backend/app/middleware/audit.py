"""
Audit logging middleware.

Automatically logs POST, PATCH, DELETE requests for audit trail tracking.
Captures user ID, IP address, user agent, and request/response details.
"""

import logging
import json
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.services.audit_service import AuditService
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatically logging audit events.

    Logs POST, PATCH, DELETE requests with:
    - User ID from JWT token
    - IP address from request
    - User agent from request headers
    - Request path and method
    - Response status code
    """

    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request/response with audit logging.

        Args:
            request: The incoming HTTP request
            call_next: Callable to process the request

        Returns:
            Response: The HTTP response
        """
        # Only audit mutating operations
        if request.method not in ["POST", "PATCH", "DELETE"]:
            return await call_next(request)

        # Extract user ID from token
        user_id = self._extract_user_id(request)

        # Get client IP and user agent
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        # Process request
        response = await call_next(request)

        # Only log successful requests (2xx status codes)
        if response.status_code < 400 and user_id:
            try:
                # Determine action from method
                action = f"{request.method}:{request.url.path}"

                # Extract resource type and ID from path if possible
                resource_type, resource_id = self._extract_resource_info(
                    request.url.path, request.method
                )

                # Log the action
                db = SessionLocal()
                try:
                    AuditService.log_action(
                        db=db,
                        user_id=UUID(user_id) if user_id else None,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Error logging audit event: {e}", exc_info=True)

        return response

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
            from app.core.security import decode_token

            token = auth_header.replace("Bearer ", "").strip()
            payload = decode_token(token)
            return payload.get("sub")
        except Exception:
            # Invalid or expired token
            return None

    @staticmethod
    def _extract_resource_info(path: str, method: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract resource type and ID from request path.

        Args:
            path: Request path
            method: HTTP method

        Returns:
            Tuple of (resource_type, resource_id)
        """
        # Simple path pattern matching for common resource endpoints
        # /api/strategies/{id} -> (strategy, id)
        # /api/exchange-keys/{id} -> (exchange_key, id)
        # /api/users/{id} -> (user, id)

        parts = path.strip("/").split("/")

        # Match patterns like /api/{resource}/{id}
        if len(parts) >= 3 and parts[0] == "api":
            resource_type = parts[1]
            if len(parts) > 2 and parts[2]:
                # Check if it looks like a UUID
                try:
                    resource_id = parts[2]
                    # Basic UUID validation (36 chars with hyphens)
                    if len(resource_id) == 36 and resource_id.count("-") == 4:
                        return (resource_type.rstrip("s"), resource_id)
                except Exception:
                    pass

        return None, None
