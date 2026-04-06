"""
Comprehensive tests for CSRF token management and middleware.

Tests cover:
- CSRF token generation
- Valid token accepted (consumed on success)
- Invalid token rejected with 403
- One-time use: token is consumed after first use
- GET requests skip CSRF validation
- Expired / missing tokens are rejected
- Public endpoints bypass CSRF validation
"""

import pytest
from unittest.mock import MagicMock

from app.core.csrf import CSRFManager


# ---------------------------------------------------------------------------
# Helper: fake Redis for CSRFManager tests
# ---------------------------------------------------------------------------


def _make_csrf_redis(expired: bool = False, unavailable: bool = False):
    """
    Build a minimal fake Redis object for CSRFManager unit tests.

    Args:
        expired: When True, GET returns None (simulating expired key).
        unavailable: When True, every call raises ConnectionError.
    """
    store: dict = {}

    class FakePipeline:
        def __init__(self):
            self._cmds = []

        def get(self, key):
            self._cmds.append(("get", key))
            return self

        def delete(self, key):
            self._cmds.append(("delete", key))
            return self

        def execute(self):
            results = []
            for cmd in self._cmds:
                if cmd[0] == "get":
                    if unavailable:
                        raise ConnectionError("Redis unavailable")
                    val = None if expired else store.get(cmd[1])
                    results.append(val)
                elif cmd[0] == "delete":
                    if unavailable:
                        raise ConnectionError("Redis unavailable")
                    store.pop(cmd[1], None)
                    results.append(1)
            return results

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeRedis:
        def pipeline(self):
            return FakePipeline()

        def setex(self, key, seconds, value):
            if unavailable:
                raise ConnectionError("Redis unavailable")
            store[key] = value

    return FakeRedis(), store


# ---------------------------------------------------------------------------
# Unit tests — CSRFManager
# ---------------------------------------------------------------------------


class TestCSRFManager:
    """Unit tests for CSRFManager using fake Redis."""

    @pytest.fixture
    def redis_and_store(self):
        return _make_csrf_redis()

    @pytest.fixture
    def manager(self, redis_and_store):
        redis, _ = redis_and_store
        return CSRFManager(redis)

    def test_generate_token_returns_nonempty_string(self, manager):
        """generate_token must return a non-empty string."""
        token = manager.generate_token("session-abc")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_is_unique_per_call(self, manager):
        """Each call to generate_token must produce a different token."""
        token1 = manager.generate_token("session-abc")
        token2 = manager.generate_token("session-abc")
        assert token1 != token2

    def test_valid_token_accepted(self, manager, redis_and_store):
        """A freshly generated token must be validated successfully."""
        token = manager.generate_token("user-123")
        result = manager.validate_token("user-123", token)
        assert result is True

    def test_invalid_token_rejected(self, manager):
        """An arbitrary string that was never generated must be rejected."""
        result = manager.validate_token("user-123", "bogus-token-value")
        assert result is False

    def test_token_is_one_time_use(self, manager):
        """A token consumed once must not be accepted a second time."""
        token = manager.generate_token("user-123")
        first = manager.validate_token("user-123", token)
        second = manager.validate_token("user-123", token)
        assert first is True
        assert second is False

    def test_expired_token_rejected(self):
        """A token that has expired (key no longer in Redis) is rejected."""
        redis, _ = _make_csrf_redis(expired=True)
        manager = CSRFManager(redis)
        # Even if we "generate" a token, the GET will return None (expired simulation)
        token = manager.generate_token("user-abc")
        result = manager.validate_token("user-abc", token)
        assert result is False

    def test_empty_token_rejected(self, manager):
        """validate_token must reject an empty token string."""
        result = manager.validate_token("user-123", "")
        assert result is False

    def test_empty_session_id_rejected(self, manager):
        """validate_token must reject when session_id is empty."""
        token = manager.generate_token("user-123")
        result = manager.validate_token("", token)
        assert result is False

    def test_token_stored_with_correct_prefix(self, redis_and_store):
        """Generated token key must start with csrf: prefix."""
        redis, store = redis_and_store
        manager = CSRFManager(redis)
        token = manager.generate_token("my-session")
        # Store should contain exactly one key with the csrf: prefix
        keys = list(store.keys())
        assert len(keys) == 1
        assert keys[0].startswith("csrf:")
        assert "my-session" in keys[0]
        assert token in keys[0]


# ---------------------------------------------------------------------------
# Integration-style tests — CSRF middleware via TestClient
# ---------------------------------------------------------------------------


class TestCSRFMiddlewareIntegration:
    """Integration tests for CSRFMiddleware behaviour via the test client."""

    def test_get_request_skips_csrf_validation(self, client):
        """GET requests must pass through even without a CSRF token."""
        response = client.get("/health")
        assert response.status_code != 403

    def test_options_request_skips_csrf_validation(self, client):
        """OPTIONS requests are safe methods and bypass CSRF."""
        response = client.options("/api/auth/login")
        # Any status code other than 403 is acceptable here
        assert response.status_code != 403

    def test_public_login_endpoint_bypasses_csrf(self, client):
        """POST /api/auth/login must not require a CSRF token."""
        payload = {"email": "no@user.com", "password": "wrong"}
        response = client.post("/api/auth/login", json=payload)
        # May be 401 (wrong credentials) but must NOT be 403 CSRF rejection
        assert response.status_code != 403

    def test_public_register_endpoint_bypasses_csrf(self, client):
        """POST /api/auth/register must not require a CSRF token."""
        payload = {
            "email": "new@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code != 403

    def test_protected_endpoint_without_csrf_token_returns_403(self, client, verified_user):
        """POST to a protected endpoint without X-CSRF-Token must return 403."""
        from app.core.security import create_access_token
        from app.middleware.csrf import CSRFMiddleware
        from app.main import app

        # Ensure CSRFMiddleware has an active manager
        fake_redis, store = _make_csrf_redis()
        csrf_mw = None
        current = app.middleware_stack
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, CSRFMiddleware):
                csrf_mw = current
                break
            current = getattr(current, "app", None)

        if csrf_mw is None:
            pytest.skip("CSRFMiddleware not found in stack — skipping integration test")

        from app.core.csrf import CSRFManager

        original_manager = csrf_mw._csrf_manager
        csrf_mw._csrf_manager = CSRFManager(fake_redis)

        try:
            token = create_access_token(str(verified_user.id), verified_user.email)
            # PATCH to a non-public endpoint without CSRF header
            response = client.patch(
                "/api/users/me",
                json={"timezone": "UTC"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403
        finally:
            csrf_mw._csrf_manager = original_manager

    def test_protected_endpoint_with_valid_csrf_token_passes(self, client, verified_user):
        """POST to a protected endpoint with a valid CSRF token must not return 403."""
        from app.core.security import create_access_token
        from app.middleware.csrf import CSRFMiddleware
        from app.core.csrf import CSRFManager
        from app.main import app

        fake_redis, _ = _make_csrf_redis()
        csrf_mw = None
        current = app.middleware_stack
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, CSRFMiddleware):
                csrf_mw = current
                break
            current = getattr(current, "app", None)

        if csrf_mw is None:
            pytest.skip("CSRFMiddleware not found in stack — skipping integration test")

        original_manager = csrf_mw._csrf_manager
        manager = CSRFManager(fake_redis)
        csrf_mw._csrf_manager = manager

        try:
            access_token = create_access_token(str(verified_user.id), verified_user.email)
            csrf_token = manager.generate_token(str(verified_user.id))

            response = client.patch(
                "/api/users/me",
                json={"timezone": "UTC"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-CSRF-Token": csrf_token,
                },
            )
            # Should not be 403 (CSRF) — may be 200 if update succeeds
            assert response.status_code != 403
        finally:
            csrf_mw._csrf_manager = original_manager

    def test_csrf_fallback_when_redis_unavailable(self, client, verified_user):
        """When Redis is unavailable the middleware allows the request through."""
        from app.core.security import create_access_token
        from app.middleware.csrf import CSRFMiddleware
        from app.main import app

        csrf_mw = None
        current = app.middleware_stack
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, CSRFMiddleware):
                csrf_mw = current
                break
            current = getattr(current, "app", None)

        if csrf_mw is None:
            pytest.skip("CSRFMiddleware not found in stack — skipping integration test")

        original_manager = csrf_mw._csrf_manager
        csrf_mw._csrf_manager = None  # Simulate unavailable Redis

        try:
            access_token = create_access_token(str(verified_user.id), verified_user.email)
            response = client.patch(
                "/api/users/me",
                json={"timezone": "UTC"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            # Should pass CSRF check (fallback) — may fail for other reasons (200/401)
            assert response.status_code != 403
        finally:
            csrf_mw._csrf_manager = original_manager
