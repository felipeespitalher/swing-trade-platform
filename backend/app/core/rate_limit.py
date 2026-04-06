"""Redis-based rate limiter for API protection."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis import Redis


class RateLimiter:
    """Sliding window rate limiter backed by Redis."""

    def __init__(self, redis_client: "Redis"):
        self.redis = redis_client

    def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if the key has exceeded the limit.

        Uses a simple counter with TTL (tumbling window).
        Sets TTL only on first increment so the window starts from the first request.

        Args:
            key: Unique identifier for the rate limit bucket.
            limit: Maximum number of requests allowed in the window.
            window_seconds: Duration of the window in seconds.

        Returns:
            True if the key has exceeded the limit, False otherwise.
        """
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = pipe.execute()
        count = results[0]
        return count > limit

    def get_count(self, key: str) -> int:
        """
        Get current request count for key.

        Args:
            key: Rate limit bucket key.

        Returns:
            Current request count (0 if key does not exist).
        """
        return int(self.redis.get(key) or 0)

    def get_remaining(self, key: str, limit: int) -> int:
        """
        Get remaining allowed requests.

        Args:
            key: Rate limit bucket key.
            limit: Maximum number of requests allowed.

        Returns:
            Number of remaining requests (never negative).
        """
        return max(0, limit - self.get_count(key))

    def get_ttl(self, key: str) -> int:
        """
        Get TTL in seconds for a rate limit key.

        Args:
            key: Rate limit bucket key.

        Returns:
            Remaining TTL in seconds (0 if key has no TTL or does not exist).
        """
        return max(0, self.redis.ttl(key))

    def reset(self, key: str) -> None:
        """
        Reset rate limit counter for key.

        Args:
            key: Rate limit bucket key to delete.
        """
        self.redis.delete(key)
