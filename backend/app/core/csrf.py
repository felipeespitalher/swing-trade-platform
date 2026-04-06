"""CSRF token management using Redis for storage."""

from secrets import token_urlsafe
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from redis import Redis


class CSRFManager:
    """One-time CSRF token manager backed by Redis."""

    TOKEN_PREFIX = "csrf:"
    DEFAULT_EXPIRY = 3600  # 1 hour

    def __init__(self, redis_client: "Redis"):
        self.redis = redis_client

    def generate_token(self, session_id: str, expires_in: int = DEFAULT_EXPIRY) -> str:
        """
        Generate a one-time CSRF token for the session.

        Args:
            session_id: Unique identifier for the session (user ID).
            expires_in: Token TTL in seconds.

        Returns:
            Newly generated CSRF token string.
        """
        token = token_urlsafe(32)
        key = f"{self.TOKEN_PREFIX}{session_id}:{token}"
        self.redis.setex(key, expires_in, "1")
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        """
        Validate CSRF token (one-time use — consumed on success).

        Uses an atomic GET + DELETE pipeline so the token cannot be reused
        even under concurrent requests.

        Args:
            session_id: Session identifier used when the token was generated.
            token: The token value from the request header.

        Returns:
            True if the token was valid (and is now consumed), False otherwise.
        """
        if not token or not session_id:
            return False
        key = f"{self.TOKEN_PREFIX}{session_id}:{token}"
        # Atomic check-and-delete
        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = pipe.execute()
        return results[0] is not None
