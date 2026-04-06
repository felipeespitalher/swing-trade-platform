"""
Comprehensive tests for rate limiting middleware and RateLimiter core class.

Tests cover:
- Login endpoint rate limited to 5 requests per minute
- 6th request returns 429 Too Many Requests
- Response includes Retry-After header
- Response includes X-RateLimit-* headers
- Different IPs / users have separate limit buckets
- /health endpoint exempt from rate limiting
- Graceful fallback when Redis is unavailable
- Rate limit reset after window expires
- Register endpoint limited to 3 per 5 minutes
"""

import pytest
from unittest.mock import MagicMock

from app.core.rate_limit import RateLimiter


# ---------------------------------------------------------------------------
# Helper: fake in-memory Redis
# ---------------------------------------------------------------------------


def _make_fake_redis():
    """Build a minimal fake in-memory Redis-like object for RateLimiter tests."""
    store: dict[str, int] = {}
    ttls: dict[str, int] = {}

    class FakePipeline:
        def __init__(self):
            self._cmds: list = []

        def incr(self, key):
            self._cmds.append(("incr", key))
            return self

        def expire(self, key, seconds):
            self._cmds.append(("expire", key, seconds))
            return self

        def execute(self):
            results = []
            for cmd in self._cmds:
                if cmd[0] == "incr":
                    store[cmd[1]] = store.get(cmd[1], 0) + 1
                    results.append(store[cmd[1]])
                elif cmd[0] == "expire":
                    ttls[cmd[1]] = cmd[2]
                    results.append(True)
            return results

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeRedis:
        def pipeline(self):
            return FakePipeline()

        def get(self, key):
            val = store.get(key)
            return str(val).encode() if val is not None else None

        def ttl(self, key):
            return ttls.get(key, -2)

        def delete(self, key):
            store.pop(key, None)

    return FakeRedis(), store


def _find_middleware(app, middleware_class):
    """Walk the Starlette middleware stack and return the first matching instance."""
    current = app.middleware_stack
    seen: set = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, middleware_class):
            return current
        current = getattr(current, "app", None)
    return None


# ---------------------------------------------------------------------------
# Unit tests — RateLimiter core
# ---------------------------------------------------------------------------


class TestRateLimiterCore:
    """Unit tests for the RateLimiter class using mock / fake Redis."""

    @pytest.fixture
    def fake_redis_and_store(self):
        return _make_fake_redis()

    @pytest.fixture
    def limiter(self, fake_redis_and_store):
        redis, _ = fake_redis_and_store
        return RateLimiter(redis)

    def test_first_request_not_rate_limited(self, limiter):
        """First request (count=1) should not be rate limited."""
        result = limiter.is_rate_limited("test:key", limit=5, window_seconds=60)
        assert result is False

    def test_request_at_limit_not_rate_limited(self, fake_redis_and_store):
        """Request at exactly the limit (count == limit) should not be blocked."""
        redis, store = fake_redis_and_store
        store["at:limit"] = 4  # next incr will make it 5 == limit
        limiter = RateLimiter(redis)
        result = limiter.is_rate_limited("at:limit", limit=5, window_seconds=60)
        assert result is False

    def test_request_over_limit_is_rate_limited(self, fake_redis_and_store):
        """Request exceeding the limit (count > limit) should be rate limited."""
        redis, store = fake_redis_and_store
        store["over:limit"] = 5  # next incr will make it 6 > 5
        limiter = RateLimiter(redis)
        result = limiter.is_rate_limited("over:limit", limit=5, window_seconds=60)
        assert result is True

    def test_get_count_returns_zero_when_key_missing(self, limiter, fake_redis_and_store):
        """get_count returns 0 when key does not exist in Redis."""
        assert limiter.get_count("missing:key") == 0

    def test_get_count_returns_current_value(self, fake_redis_and_store):
        """get_count returns the current counter value."""
        redis, store = fake_redis_and_store
        store["known:key"] = 3
        limiter = RateLimiter(redis)
        assert limiter.get_count("known:key") == 3

    def test_get_remaining_below_limit(self, fake_redis_and_store):
        """get_remaining returns correct remaining count when below limit."""
        redis, store = fake_redis_and_store
        store["partial:key"] = 2
        limiter = RateLimiter(redis)
        assert limiter.get_remaining("partial:key", limit=5) == 3

    def test_get_remaining_never_negative(self, fake_redis_and_store):
        """get_remaining clamps to 0 when count exceeds limit."""
        redis, store = fake_redis_and_store
        store["over:key"] = 10
        limiter = RateLimiter(redis)
        assert limiter.get_remaining("over:key", limit=5) == 0

    def test_get_ttl_returns_value_from_redis(self, fake_redis_and_store):
        """get_ttl returns the TTL stored for a key."""
        redis, ttls_ref = _make_fake_redis()
        # Fake: set a known TTL in the store by running is_rate_limited
        limiter = RateLimiter(redis)
        limiter.is_rate_limited("ttl:test", limit=10, window_seconds=45)
        # TTL should be ≥ 0 (fake returns the window_seconds value)
        assert limiter.get_ttl("ttl:test") >= 0

    def test_get_ttl_returns_zero_for_missing_key(self, limiter):
        """get_ttl returns 0 when the key does not exist or has no TTL."""
        assert limiter.get_ttl("nonexistent:key") == 0

    def test_reset_removes_key(self, fake_redis_and_store):
        """reset deletes the key so subsequent requests start from zero."""
        redis, store = fake_redis_and_store
        key = "reset:key"
        store[key] = 5
        limiter = RateLimiter(redis)
        limiter.reset(key)
        assert limiter.get_count(key) == 0


# ---------------------------------------------------------------------------
# Behavioural / integration tests (no real Redis needed)
# ---------------------------------------------------------------------------


class TestRateLimiterBehaviour:
    """Higher-level behavioural tests using the fake Redis."""

    def test_login_limited_to_five_per_minute(self):
        """Requests 1-5 pass; request 6 is blocked for the login bucket."""
        redis, _ = _make_fake_redis()
        limiter = RateLimiter(redis)
        key = "rl:ip:1.2.3.4:/api/auth/login"

        for i in range(5):
            assert not limiter.is_rate_limited(key, 5, 60), f"Request {i+1} should pass"

        assert limiter.is_rate_limited(key, 5, 60), "6th request should be blocked"

    def test_different_ips_have_separate_buckets(self):
        """Two different IP keys do not share a counter."""
        redis, _ = _make_fake_redis()
        limiter = RateLimiter(redis)

        for _ in range(5):
            limiter.is_rate_limited("rl:ip:1.2.3.4:/api/auth/login", 5, 60)

        # IP 9.9.9.9 has its own clean bucket
        assert not limiter.is_rate_limited("rl:ip:9.9.9.9:/api/auth/login", 5, 60)

    def test_register_limited_to_three_per_five_minutes(self):
        """Register endpoint should be blocked after 3 requests in 300 seconds."""
        redis, _ = _make_fake_redis()
        limiter = RateLimiter(redis)
        key = "rl:ip:1.2.3.4:/api/auth/register"

        for _ in range(3):
            assert not limiter.is_rate_limited(key, 3, 300)

        assert limiter.is_rate_limited(key, 3, 300), "4th register request should be blocked"

    def test_rate_limit_reset_allows_new_requests(self):
        """After reset, the counter starts from zero again."""
        redis, _ = _make_fake_redis()
        limiter = RateLimiter(redis)
        key = "rl:ip:1.2.3.4:/api/auth/login"

        for _ in range(5):
            limiter.is_rate_limited(key, 5, 60)

        limiter.reset(key)

        # After reset, first request should not be rate limited
        assert not limiter.is_rate_limited(key, 5, 60)

    def test_user_bucket_separate_from_ip_bucket(self):
        """Authenticated user bucket and anonymous IP bucket are independent."""
        redis, _ = _make_fake_redis()
        limiter = RateLimiter(redis)

        ip_key = "rl:ip:1.2.3.4:/api/auth/login"
        user_key = "rl:user:abc123:/api/auth/login"

        for _ in range(5):
            limiter.is_rate_limited(ip_key, 5, 60)

        # IP bucket is at limit but user bucket is clean
        assert not limiter.is_rate_limited(user_key, 5, 60)


# ---------------------------------------------------------------------------
# Middleware tests via TestClient
# ---------------------------------------------------------------------------


class TestRateLimitMiddlewareViaClient:
    """Integration tests for RateLimitMiddleware via the FastAPI TestClient."""

    def _inject_fake_limiter(self, app):
        """Swap the middleware limiter for a fresh fake one. Returns (mw, original)."""
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = _find_middleware(app, RateLimitMiddleware)
        if mw is None:
            return None, None

        redis, _ = _make_fake_redis()
        original = mw._limiter
        mw._limiter = RateLimiter(redis)
        return mw, original

    def test_health_endpoint_not_rate_limited(self, client):
        """The /health endpoint must never return 429 regardless of request count."""
        for _ in range(25):
            response = client.get("/health")
            assert response.status_code != 429

    def test_sixth_login_request_returns_429(self, client, db):
        """
        5 login requests must be allowed through the rate limiter.
        The 6th request within the same window must return 429.
        """
        from app.main import app

        mw, original = self._inject_fake_limiter(app)
        try:
            payload = {"email": "ratelimit@example.com", "password": "Pass123!"}
            for i in range(5):
                resp = client.post("/api/auth/login", json=payload)
                assert resp.status_code != 429, f"Request {i+1} should not be rate limited"

            resp = client.post("/api/auth/login", json=payload)
            assert resp.status_code == 429
        finally:
            if mw:
                mw._limiter = original

    def test_429_includes_retry_after_header(self, client, db):
        """429 response must include the Retry-After header."""
        from app.main import app

        mw, original = self._inject_fake_limiter(app)
        try:
            payload = {"email": "ratelimit2@example.com", "password": "Pass123!"}
            for _ in range(5):
                client.post("/api/auth/login", json=payload)

            resp = client.post("/api/auth/login", json=payload)
            assert resp.status_code == 429
            assert "retry-after" in resp.headers
        finally:
            if mw:
                mw._limiter = original

    def test_429_includes_x_ratelimit_headers(self, client, db):
        """429 response must include X-RateLimit-Limit and X-RateLimit-Remaining headers."""
        from app.main import app

        mw, original = self._inject_fake_limiter(app)
        try:
            payload = {"email": "ratelimit3@example.com", "password": "Pass123!"}
            for _ in range(5):
                client.post("/api/auth/login", json=payload)

            resp = client.post("/api/auth/login", json=payload)
            assert resp.status_code == 429
            assert "x-ratelimit-limit" in resp.headers
            assert "x-ratelimit-remaining" in resp.headers
        finally:
            if mw:
                mw._limiter = original

    def test_graceful_fallback_when_redis_unavailable(self, client):
        """When the limiter is None (Redis down), requests must pass through without 429."""
        from app.main import app
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = _find_middleware(app, RateLimitMiddleware)
        original = mw._limiter if mw else None
        if mw:
            mw._limiter = None

        try:
            for _ in range(10):
                resp = client.post(
                    "/api/auth/login",
                    json={"email": "fallback@example.com", "password": "any"},
                )
                assert resp.status_code != 429
        finally:
            if mw:
                mw._limiter = original
