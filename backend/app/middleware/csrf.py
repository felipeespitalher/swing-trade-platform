"""CSRF protection middleware."""

import logging
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# HTTP methods that do NOT require CSRF validation
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Public endpoints that bypass CSRF (they use other protections, e.g. password / JWT)
PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",   # Protected by the refresh token itself
    "/health",
}


def _extract_user_id(request: Request) -> Optional[str]:
    """Extract user ID (used as session_id) from JWT in Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        from app.core.security import verify_token

        token = auth_header.replace("Bearer ", "").strip()
        payload = verify_token(token)
        return payload.sub if payload else None
    except Exception:
        return None


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates CSRF tokens on state-changing requests.

    - Skips GET, HEAD, OPTIONS.
    - Skips public endpoints (login, register, health).
    - Reads the CSRF token from the X-CSRF-Token request header.
    - Uses the authenticated user_id as the session identifier.
    - Falls back gracefully when Redis is unavailable (allows request, logs warning).
    """

    def __init__(self, app: ASGIApp, redis_url: Optional[str] = None):
        super().__init__(app)
        self._redis_url = redis_url
        self._csrf_manager = None
        self._init_csrf_manager()

    def _init_csrf_manager(self) -> None:
        try:
            from redis import Redis
            from app.core.csrf import CSRFManager

            url = self._redis_url
            if url is None:
                from app.core.config import settings

                url = settings.redis_url
            client = Redis.from_url(url, socket_connect_timeout=2, decode_responses=True)
            self._csrf_manager = CSRFManager(client)
        except Exception as exc:
            logger.warning(f"CSRF manager unavailable (Redis init failed): {exc}")
            self._csrf_manager = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Safe methods skip CSRF validation
        if request.method in SAFE_METHODS:
            return await call_next(request)

        # Public endpoints skip CSRF validation
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # If Redis is unavailable fall through gracefully
        if self._csrf_manager is None:
            logger.warning("CSRF manager unavailable — skipping CSRF check")
            return await call_next(request)

        token = request.headers.get("X-CSRF-Token", "")
        session_id = _extract_user_id(request)

        try:
            valid = self._csrf_manager.validate_token(session_id or "", token)
        except Exception as exc:
            logger.warning(f"CSRF validation failed (allowing request): {exc}")
            return await call_next(request)

        if not valid:
            logger.warning(
                f"CSRF token invalid or missing: path={request.url.path} "
                f"session_id={session_id}"
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token invalid or missing."},
            )

        return await call_next(request)
