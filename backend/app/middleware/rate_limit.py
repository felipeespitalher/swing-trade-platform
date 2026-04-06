"""Rate limiting middleware for API protection."""

import logging
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Endpoint-specific rate limits: (max_requests, window_seconds)
DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    "/api/auth/login": (5, 60),       # 5 per 60 s
    "/api/auth/register": (3, 300),   # 3 per 5 min
    "/api/auth/": (10, 60),           # 10 per min for any auth endpoint
    "/": (100, 60),                   # 100 per min default
}

# Paths that bypass rate limiting entirely
EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi")


def _resolve_limit(path: str) -> tuple[int, int]:
    """
    Resolve rate limit tuple for a given path.

    More specific patterns take precedence over catch-all patterns.

    Args:
        path: Request URL path.

    Returns:
        Tuple of (limit, window_seconds).
    """
    # Exact matches first, then prefix matches longest-first, then default
    for pattern in sorted(DEFAULT_LIMITS.keys(), key=len, reverse=True):
        if pattern == "/":
            continue
        if path == pattern or path.startswith(pattern):
            return DEFAULT_LIMITS[pattern]
    return DEFAULT_LIMITS["/"]


def _get_client_ip(request: Request) -> str:
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_user_id(request: Request) -> Optional[str]:
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-endpoint rate limits using Redis.

    - Authenticated requests are bucketed by user_id + path.
    - Anonymous requests are bucketed by client IP + path.
    - Falls back gracefully when Redis is unavailable.
    - Adds X-RateLimit-* headers to all non-exempt responses.
    - Returns 429 with Retry-After header when limit exceeded.
    """

    def __init__(self, app: ASGIApp, redis_url: Optional[str] = None):
        super().__init__(app)
        self._redis_url = redis_url
        self._limiter = None
        self._init_limiter()

    def _init_limiter(self) -> None:
        try:
            from redis import Redis
            from app.core.rate_limit import RateLimiter

            url = self._redis_url
            if url is None:
                from app.core.config import settings

                url = settings.redis_url
            client = Redis.from_url(url, socket_connect_timeout=2, decode_responses=True)
            self._limiter = RateLimiter(client)
        except Exception as exc:
            logger.warning(f"Rate limiter unavailable (Redis init failed): {exc}")
            self._limiter = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Exempt health/docs paths
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return await call_next(request)

        limit, window = _resolve_limit(path)

        # Build rate limit key
        user_id = _extract_user_id(request)
        if user_id:
            bucket = f"rl:user:{user_id}:{path}"
        else:
            ip = _get_client_ip(request)
            bucket = f"rl:ip:{ip}:{path}"

        # Attempt rate limit check
        if self._limiter is not None:
            try:
                limited = self._limiter.is_rate_limited(bucket, limit, window)
                remaining = self._limiter.get_remaining(bucket, limit)
                ttl = self._limiter.get_ttl(bucket)

                if limited:
                    logger.warning(
                        f"Rate limit exceeded: bucket={bucket} limit={limit} window={window}"
                    )
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please slow down."},
                        headers={
                            "Retry-After": str(ttl),
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(ttl),
                        },
                    )

                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(ttl)
                return response

            except Exception as exc:
                # Graceful degradation: allow request if Redis is down
                logger.warning(f"Rate limiter check failed (allowing request): {exc}")
                self._limiter = None

        # Fallback: Redis unavailable — pass through
        return await call_next(request)
