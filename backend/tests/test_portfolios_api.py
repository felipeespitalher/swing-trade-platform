"""
Tests for portfolio management API endpoints.

Covers:
- List portfolios (empty list, only own portfolios returned)
- Create portfolio (paper/live modes, invalid mode, invalid risk_profile, unauthenticated)
- Get portfolio by ID (200, 404, other user returns 404)
- Update portfolio (name, capital_allocation, mode, partial updates)
- Delete portfolio (204, subsequent GET returns 404)
- Portfolio strategies (list empty, assign via PATCH, list returns them)
- Market status (binance is 24/7, always open)
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.models.portfolio import Portfolio
from app.models.strategy import Strategy
from app.core.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user: User) -> dict:
    """Return Authorization headers for the given user."""
    token = create_access_token(user_id=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


VALID_PORTFOLIO_PAYLOAD = {
    "name": "Carteira Teste",
    "description": "Para testes",
    "capital_allocation": 10000.0,
    "risk_profile": "moderado",
    "mode": "paper",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListPortfolios:
    """Tests for GET /api/portfolios."""

    def test_list_portfolios_empty(self, client: TestClient, verified_user: User):
        """New user with no portfolios gets an empty list."""
        response = client.get(
            "/api/portfolios",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_portfolios_returns_only_own_portfolios(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """List only returns portfolios belonging to the authenticated user."""
        # Create a portfolio for verified_user
        client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )

        # Create a second user with their own portfolio
        other_user = User(
            id=uuid.uuid4(),
            email="other_portfolio@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        client.post(
            "/api/portfolios",
            json={**VALID_PORTFOLIO_PAYLOAD, "name": "Carteira do Outro"},
            headers=_auth_headers(other_user),
        )

        response = client.get(
            "/api/portfolios",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == VALID_PORTFOLIO_PAYLOAD["name"]

    def test_unauthenticated_list_returns_403(self, client: TestClient):
        """List endpoint requires authentication; HTTPBearer returns 403 when no token."""
        response = client.get("/api/portfolios")
        assert response.status_code == 403


class TestCreatePortfolio:
    """Tests for POST /api/portfolios."""

    def test_create_portfolio_paper_mode_returns_201(
        self, client: TestClient, verified_user: User
    ):
        """Creating a portfolio in paper mode returns 201 with the new portfolio data."""
        response = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == VALID_PORTFOLIO_PAYLOAD["name"]
        assert data["mode"] == "paper"
        assert data["risk_profile"] == "moderado"
        assert data["is_active"] is True

    def test_create_portfolio_live_mode_returns_201(
        self, client: TestClient, verified_user: User
    ):
        """Creating a portfolio in live mode returns 201."""
        payload = {**VALID_PORTFOLIO_PAYLOAD, "mode": "live"}
        response = client.post(
            "/api/portfolios",
            json=payload,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 201
        assert response.json()["mode"] == "live"

    def test_create_portfolio_invalid_mode_returns_422(
        self, client: TestClient, verified_user: User
    ):
        """Creating a portfolio with an unsupported mode returns 422."""
        payload = {**VALID_PORTFOLIO_PAYLOAD, "mode": "simulated"}
        response = client.post(
            "/api/portfolios",
            json=payload,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 422

    def test_create_portfolio_invalid_risk_profile_returns_422(
        self, client: TestClient, verified_user: User
    ):
        """Creating a portfolio with an unsupported risk_profile returns 422."""
        payload = {**VALID_PORTFOLIO_PAYLOAD, "risk_profile": "extremo"}
        response = client.post(
            "/api/portfolios",
            json=payload,
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 422

    def test_unauthenticated_create_returns_403(self, client: TestClient):
        """Create endpoint requires authentication; HTTPBearer returns 403 when no token."""
        response = client.post("/api/portfolios", json=VALID_PORTFOLIO_PAYLOAD)
        assert response.status_code == 403

    def test_create_portfolio_persists_to_database(
        self, client: TestClient, verified_user: User
    ):
        """Created portfolio is retrievable via GET."""
        create_response = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        assert create_response.status_code == 201
        portfolio_id = create_response.json()["id"]

        get_response = client.get(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(verified_user),
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == portfolio_id


class TestGetPortfolio:
    """Tests for GET /api/portfolios/{id}."""

    def test_get_own_portfolio_returns_200(
        self, client: TestClient, verified_user: User
    ):
        """GET by ID returns full portfolio details for the owner."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.get(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == portfolio_id
        assert data["name"] == VALID_PORTFOLIO_PAYLOAD["name"]
        assert data["capital_allocation"] == VALID_PORTFOLIO_PAYLOAD["capital_allocation"]

    def test_get_nonexistent_portfolio_returns_404(
        self, client: TestClient, verified_user: User
    ):
        """GET with unknown ID returns 404."""
        random_id = str(uuid.uuid4())
        response = client.get(
            f"/api/portfolios/{random_id}",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 404

    def test_other_user_cannot_get_portfolio(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET by a different user returns 404 (portfolio not found for that user)."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        other_user = User(
            id=uuid.uuid4(),
            email="other_get@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        response = client.get(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(other_user),
        )
        assert response.status_code == 404


class TestUpdatePortfolio:
    """Tests for PUT /api/portfolios/{id}."""

    def test_update_portfolio_name(
        self, client: TestClient, verified_user: User
    ):
        """PUT updates the portfolio's name."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.put(
            f"/api/portfolios/{portfolio_id}",
            json={"name": "Carteira Atualizada"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Carteira Atualizada"

    def test_update_portfolio_capital_allocation(
        self, client: TestClient, verified_user: User
    ):
        """PUT updates capital_allocation."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.put(
            f"/api/portfolios/{portfolio_id}",
            json={"capital_allocation": 25000.0},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["capital_allocation"] == 25000.0

    def test_update_portfolio_mode(
        self, client: TestClient, verified_user: User
    ):
        """PUT updates mode from paper to live."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.put(
            f"/api/portfolios/{portfolio_id}",
            json={"mode": "live"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "live"

    def test_partial_update_preserves_other_fields(
        self, client: TestClient, verified_user: User
    ):
        """Partial update (only name) preserves all other fields unchanged."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.put(
            f"/api/portfolios/{portfolio_id}",
            json={"name": "Novo Nome"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Novo Nome"
        assert data["mode"] == VALID_PORTFOLIO_PAYLOAD["mode"]
        assert data["risk_profile"] == VALID_PORTFOLIO_PAYLOAD["risk_profile"]

    def test_update_nonexistent_portfolio_returns_404(
        self, client: TestClient, verified_user: User
    ):
        """PUT on a non-existent portfolio returns 404."""
        response = client.put(
            f"/api/portfolios/{uuid.uuid4()}",
            json={"name": "Qualquer"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 404


class TestDeletePortfolio:
    """Tests for DELETE /api/portfolios/{id}."""

    def test_delete_portfolio_returns_204(
        self, client: TestClient, verified_user: User
    ):
        """DELETE returns 204 on success."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.delete(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 204

    def test_delete_portfolio_subsequent_get_returns_404(
        self, client: TestClient, verified_user: User
    ):
        """After DELETE, subsequent GET returns 404."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        client.delete(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(verified_user),
        )

        get_resp = client.get(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(verified_user),
        )
        assert get_resp.status_code == 404

    def test_delete_nonexistent_portfolio_returns_404(
        self, client: TestClient, verified_user: User
    ):
        """DELETE on a non-existent portfolio returns 404."""
        response = client.delete(
            f"/api/portfolios/{uuid.uuid4()}",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 404

    def test_other_user_cannot_delete_portfolio(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """DELETE by a different user returns 404."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        other_user = User(
            id=uuid.uuid4(),
            email="other_delete@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        response = client.delete(
            f"/api/portfolios/{portfolio_id}",
            headers=_auth_headers(other_user),
        )
        assert response.status_code == 404


class TestPortfolioStrategies:
    """Tests for GET/PATCH /api/portfolios/{id}/strategies."""

    def test_list_strategies_empty_when_none_assigned(
        self, client: TestClient, verified_user: User
    ):
        """Newly created portfolio has no strategies."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.get(
            f"/api/portfolios/{portfolio_id}/strategies",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_assign_strategies_via_patch(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """PATCH /strategies assigns the given strategy IDs to the portfolio."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        strategy = Strategy(
            id=uuid.uuid4(),
            user_id=verified_user.id,
            name="Test Strategy",
            type="rsi_only",
            config={"symbol": "BTC/USDT", "timeframe": "1h"},
            is_active=False,
        )
        db.add(strategy)
        db.commit()

        response = client.patch(
            f"/api/portfolios/{portfolio_id}/strategies",
            json={"strategy_ids": [str(strategy.id)]},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assigned = response.json()
        assert str(strategy.id) in assigned

    def test_list_strategies_returns_assigned(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """After PATCH, GET /strategies returns the assigned strategies."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        strategy = Strategy(
            id=uuid.uuid4(),
            user_id=verified_user.id,
            name="Test Strategy For List",
            type="rsi_only",
            config={"symbol": "ETH/USDT", "timeframe": "4h"},
            is_active=False,
        )
        db.add(strategy)
        db.commit()

        client.patch(
            f"/api/portfolios/{portfolio_id}/strategies",
            json={"strategy_ids": [str(strategy.id)]},
            headers=_auth_headers(verified_user),
        )

        list_resp = client.get(
            f"/api/portfolios/{portfolio_id}/strategies",
            headers=_auth_headers(verified_user),
        )
        assert list_resp.status_code == 200
        strategies = list_resp.json()
        assert len(strategies) == 1
        assert strategies[0]["name"] == "Test Strategy For List"

    def test_assign_empty_list_unlinks_all_strategies(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """PATCH with empty strategy_ids removes all assignments."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        strategy = Strategy(
            id=uuid.uuid4(),
            user_id=verified_user.id,
            name="Strategy To Unlink",
            type="rsi_only",
            config={"symbol": "BTC/USDT", "timeframe": "1d"},
            is_active=False,
        )
        db.add(strategy)
        db.commit()

        # First assign
        client.patch(
            f"/api/portfolios/{portfolio_id}/strategies",
            json={"strategy_ids": [str(strategy.id)]},
            headers=_auth_headers(verified_user),
        )

        # Then unlink all
        client.patch(
            f"/api/portfolios/{portfolio_id}/strategies",
            json={"strategy_ids": []},
            headers=_auth_headers(verified_user),
        )

        list_resp = client.get(
            f"/api/portfolios/{portfolio_id}/strategies",
            headers=_auth_headers(verified_user),
        )
        assert list_resp.status_code == 200
        assert list_resp.json() == []

    def test_cannot_assign_other_users_strategy(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Strategies belonging to another user are ignored during PATCH assignment."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        other_user = User(
            id=uuid.uuid4(),
            email="other_strat@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_strategy = Strategy(
            id=uuid.uuid4(),
            user_id=other_user.id,
            name="Other User Strategy",
            type="rsi_only",
            config={"symbol": "BTC/USDT", "timeframe": "1h"},
            is_active=False,
        )
        db.add(other_strategy)
        db.commit()

        response = client.patch(
            f"/api/portfolios/{portfolio_id}/strategies",
            json={"strategy_ids": [str(other_strategy.id)]},
            headers=_auth_headers(verified_user),
        )
        # Request succeeds but strategy is not assigned (ignored silently)
        assert response.status_code == 200
        assert response.json() == []


class TestMarketStatus:
    """Tests for GET /api/portfolios/{id}/market-status."""

    def test_binance_market_status_is_always_open(
        self, client: TestClient, verified_user: User
    ):
        """Binance is a 24/7 exchange; market-status returns is_open=True at any time."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.get(
            f"/api/portfolios/{portfolio_id}/market-status?exchange=binance",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_open"] is True

    def test_market_status_requires_authentication(self, client: TestClient):
        """market-status endpoint requires authentication."""
        response = client.get(
            f"/api/portfolios/{uuid.uuid4()}/market-status?exchange=binance",
        )
        assert response.status_code == 403

    def test_market_status_returns_404_for_nonexistent_portfolio(
        self, client: TestClient, verified_user: User
    ):
        """market-status returns 404 when portfolio does not exist."""
        response = client.get(
            f"/api/portfolios/{uuid.uuid4()}/market-status?exchange=binance",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 404

    def test_market_status_binance_reason_is_24h_market(
        self, client: TestClient, verified_user: User
    ):
        """Binance market-status response includes reason='24h_market'."""
        create_resp = client.post(
            "/api/portfolios",
            json=VALID_PORTFOLIO_PAYLOAD,
            headers=_auth_headers(verified_user),
        )
        portfolio_id = create_resp.json()["id"]

        response = client.get(
            f"/api/portfolios/{portfolio_id}/market-status?exchange=binance",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 200
        assert response.json()["reason"] == "24h_market"
