"""
Tests for strategy management API endpoints.

Covers:
- List strategies (empty list, only own strategies)
- Create strategy (201, persists to DB)
- Get strategy by ID (200, 404)
- Update strategy (PUT)
- Delete strategy (204, subsequent GET returns 404)
- Enable/disable strategy (PATCH /status)
- Authorization isolation (other users cannot access)
- Unauthenticated access (401)
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.models.strategy import Strategy
from app.core.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user: User) -> dict:
    """Return Authorization headers for the given user."""
    token = create_access_token(user_id=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


VALID_STRATEGY_PAYLOAD = {
    "name": "My RSI Strategy",
    "type": "rsi_only",
    "config": {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70},
    "symbol": "BTC/USDT",
    "timeframe": "1h",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListStrategies:
    """Tests for GET /api/strategies."""

    def test_list_strategies_empty(self, client: TestClient, verified_user: User):
        """New user with no strategies gets an empty list."""
        response = client.get(
            "/api/strategies",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_strategies_returns_only_own_strategies(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """List only returns strategies belonging to the authenticated user."""
        # Create a strategy for verified_user
        client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )

        # Create a second user with their own strategy
        other_user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        client.post(
            "/api/strategies",
            json={**VALID_STRATEGY_PAYLOAD, "name": "Other Strategy"},
            headers=_auth_headers(other_user),
        )

        response = client.get(
            "/api/strategies",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == VALID_STRATEGY_PAYLOAD["name"]

    def test_unauthenticated_list_returns_403(self, client: TestClient):
        """List endpoint requires authentication; HTTPBearer returns 403 when no token."""
        response = client.get("/api/strategies")
        assert response.status_code == 403


class TestCreateStrategy:
    """Tests for POST /api/strategies."""

    def test_create_strategy_returns_201_with_id(
        self, client: TestClient, verified_user: User
    ):
        """Creating a strategy returns 201 and the new strategy's ID."""
        response = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == VALID_STRATEGY_PAYLOAD["name"]
        assert data["type"] == VALID_STRATEGY_PAYLOAD["type"]
        assert data["symbol"] == VALID_STRATEGY_PAYLOAD["symbol"]
        assert data["timeframe"] == VALID_STRATEGY_PAYLOAD["timeframe"]
        assert data["is_active"] is False

    def test_create_strategy_persists_to_database(
        self, client: TestClient, verified_user: User
    ):
        """Created strategy is retrievable via GET."""
        create_response = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        assert create_response.status_code == 201
        strategy_id = create_response.json()["id"]

        get_response = client.get(
            f"/api/strategies/{strategy_id}",
            headers=_auth_headers(verified_user),
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == strategy_id

    def test_create_strategy_invalid_type_returns_422(
        self, client: TestClient, verified_user: User
    ):
        """Creating a strategy with an unsupported type returns 422."""
        payload = {**VALID_STRATEGY_PAYLOAD, "type": "unknown_type"}
        response = client.post(
            "/api/strategies",
            json=payload,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 422

    def test_unauthenticated_create_returns_403(self, client: TestClient):
        """Create endpoint requires authentication; HTTPBearer returns 403 when no token."""
        response = client.post("/api/strategies", json=VALID_STRATEGY_PAYLOAD)
        assert response.status_code == 403


class TestGetStrategy:
    """Tests for GET /api/strategies/{id}."""

    def test_get_strategy_returns_detail(
        self, client: TestClient, verified_user: User
    ):
        """GET by ID returns full strategy details for the owner."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        response = client.get(
            f"/api/strategies/{strategy_id}",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == strategy_id
        assert data["name"] == VALID_STRATEGY_PAYLOAD["name"]
        assert data["type"] == VALID_STRATEGY_PAYLOAD["type"]

    def test_get_strategy_returns_404_for_nonexistent(
        self, client: TestClient, verified_user: User
    ):
        """GET with unknown ID returns 404."""
        random_id = str(uuid.uuid4())
        response = client.get(
            f"/api/strategies/{random_id}",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 404

    def test_unauthenticated_get_returns_403(self, client: TestClient):
        """Get endpoint requires authentication; HTTPBearer returns 403 when no token."""
        response = client.get(f"/api/strategies/{uuid.uuid4()}")
        assert response.status_code == 403


class TestUpdateStrategy:
    """Tests for PUT /api/strategies/{id}."""

    def test_update_strategy_modifies_name(
        self, client: TestClient, verified_user: User
    ):
        """PUT updates the strategy's name."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        update_payload = {"name": "Updated Strategy Name"}
        response = client.put(
            f"/api/strategies/{strategy_id}",
            json=update_payload,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Strategy Name"

    def test_update_strategy_returns_updated_data(
        self, client: TestClient, verified_user: User
    ):
        """PUT response body reflects updated values."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        update_payload = {
            "name": "New Name",
            "config": {"rsi_period": 21, "rsi_oversold": 25, "rsi_overbought": 75},
        }
        response = client.put(
            f"/api/strategies/{strategy_id}",
            json=update_payload,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    def test_cannot_access_other_users_strategy(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """PUT by a different user returns 404 (strategy not found for that user)."""
        # Create strategy for verified_user
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        # Second user attempts to update it
        other_user = User(
            id=uuid.uuid4(),
            email="other2@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        response = client.put(
            f"/api/strategies/{strategy_id}",
            json={"name": "Hacked"},
            headers=_auth_headers(other_user),
        )
        assert response.status_code == 404


class TestDeleteStrategy:
    """Tests for DELETE /api/strategies/{id}."""

    def test_delete_strategy_removes_record(
        self, client: TestClient, verified_user: User
    ):
        """DELETE returns 204; subsequent GET returns 404."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        delete_resp = client.delete(
            f"/api/strategies/{strategy_id}",
            headers=_auth_headers(verified_user),
        )
        assert delete_resp.status_code == 204

        get_resp = client.get(
            f"/api/strategies/{strategy_id}",
            headers=_auth_headers(verified_user),
        )
        assert get_resp.status_code == 404

    def test_other_user_cannot_delete_strategy(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """DELETE by a different user returns 404."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        other_user = User(
            id=uuid.uuid4(),
            email="other3@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        response = client.delete(
            f"/api/strategies/{strategy_id}",
            headers=_auth_headers(other_user),
        )
        assert response.status_code == 404


class TestStrategyStatus:
    """Tests for PATCH /api/strategies/{id}/status."""

    def test_enable_strategy_sets_is_active_true(
        self, client: TestClient, verified_user: User
    ):
        """PATCH /status with 'active' sets is_active=True."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]
        assert create_resp.json()["is_active"] is False

        response = client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "active"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_disable_strategy_sets_is_active_false(
        self, client: TestClient, verified_user: User
    ):
        """PATCH /status with 'inactive' sets is_active=False."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        # Enable first
        client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "active"},
            headers=_auth_headers(verified_user),
        )

        # Now disable
        response = client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "inactive"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_invalid_status_value_returns_422(
        self, client: TestClient, verified_user: User
    ):
        """PATCH /status with invalid value returns 422."""
        create_resp = client.post(
            "/api/strategies",
            json=VALID_STRATEGY_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        strategy_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "enabled"},  # invalid value
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 422

    def test_unauthenticated_status_update_returns_403(self, client: TestClient):
        """Status endpoint requires authentication; HTTPBearer returns 403 when no token."""
        response = client.patch(
            f"/api/strategies/{uuid.uuid4()}/status",
            json={"status": "active"},
        )
        assert response.status_code == 403
