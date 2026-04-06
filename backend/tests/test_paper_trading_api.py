"""
Tests for paper trading API endpoints.

Covers:
- POST /api/paper-trading/start
- POST /api/paper-trading/stop
- GET  /api/paper-trading/status
- GET  /api/paper-trading/history
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import User
from app.models.strategy import Strategy
from app.models.trade import Trade
from app.services.paper_trading_engine import PaperPortfolio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(user: User) -> dict:
    """Return Authorization headers for the given user."""
    token = create_access_token(user_id=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _make_strategy(db: Session, user: User, name: str = "Test Strategy") -> Strategy:
    """Create and persist a test strategy belonging to user."""
    strategy = Strategy(
        id=uuid.uuid4(),
        user_id=user.id,
        name=name,
        type="rsi_only",
        config={"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70},
        is_active=False,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def _make_portfolio(strategy_id: uuid.UUID, balance: float = 10000.0) -> PaperPortfolio:
    """Create a mock PaperPortfolio for testing."""
    portfolio = PaperPortfolio(
        strategy_id=strategy_id,
        initial_balance=Decimal(str(balance)),
    )
    return portfolio


def _make_closed_trade(
    db: Session,
    strategy: Strategy,
    symbol: str = "BTC/USDT",
    entry_price: float = 50000.0,
    exit_price: float = 55000.0,
    pnl: float = 500.0,
) -> Trade:
    """Create and persist a closed paper trade."""
    trade = Trade(
        id=uuid.uuid4(),
        strategy_id=strategy.id,
        symbol=symbol,
        entry_price=Decimal(str(entry_price)),
        exit_price=Decimal(str(exit_price)),
        quantity=Decimal("0.1"),
        pnl=Decimal(str(pnl)),
        pnl_pct=Decimal("1.0"),
        is_paper_trade=True,
        entry_date=datetime.now(timezone.utc),
        exit_date=datetime.now(timezone.utc),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


# ---------------------------------------------------------------------------
# Tests: start session
# ---------------------------------------------------------------------------


class TestStartSession:
    """Tests for POST /api/paper-trading/start."""

    def test_start_session_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """POST start with valid strategy_id returns 200 and session info."""
        strategy = _make_strategy(db, verified_user)
        portfolio = _make_portfolio(strategy.id)

        with patch(
            "app.api.paper_trading.session_manager.start_session",
            return_value=portfolio,
        ):
            response = client.post(
                "/api/paper-trading/start",
                json={
                    "strategy_id": str(strategy.id),
                    "initial_balance": 10000.0,
                },
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["strategy_id"] == str(strategy.id)
        assert body["initial_balance"] == 10000.0
        assert "message" in body

    def test_start_session_invalid_strategy(
        self, client: TestClient, verified_user: User
    ):
        """POST start with unknown strategy_id returns 404."""
        with patch(
            "app.api.paper_trading.session_manager.start_session",
        ):
            response = client.post(
                "/api/paper-trading/start",
                json={
                    "strategy_id": str(uuid.uuid4()),
                    "initial_balance": 10000.0,
                },
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 404

    def test_start_session_other_user_strategy_returns_404(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Cannot start session for a strategy belonging to another user."""
        other_user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        other_strategy = _make_strategy(db, other_user, "Other Strategy")

        with patch("app.api.paper_trading.session_manager.start_session"):
            response = client.post(
                "/api/paper-trading/start",
                json={"strategy_id": str(other_strategy.id)},
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 404

    def test_start_session_invalid_uuid_returns_400(
        self, client: TestClient, verified_user: User
    ):
        """POST start with malformed strategy_id returns 400."""
        response = client.post(
            "/api/paper-trading/start",
            json={"strategy_id": "not-a-uuid"},
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 400

    def test_start_session_unauthenticated_returns_401(self, client: TestClient):
        """POST start without JWT returns 401."""
        response = client.post(
            "/api/paper-trading/start",
            json={"strategy_id": str(uuid.uuid4())},
        )
        assert response.status_code == 403  # HTTPBearer returns 403 when missing


# ---------------------------------------------------------------------------
# Tests: stop session
# ---------------------------------------------------------------------------


class TestStopSession:
    """Tests for POST /api/paper-trading/stop."""

    def test_stop_session_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """POST stop returns session summary."""
        strategy = _make_strategy(db, verified_user)
        summary = {
            "strategy_id": str(strategy.id),
            "initial_balance": 10000.0,
            "final_balance": 10500.0,
            "realized_pnl": 500.0,
            "trade_count": 2,
            "open_positions": 0,
        }

        with patch(
            "app.api.paper_trading.session_manager.stop_session",
            return_value=summary,
        ):
            response = client.post(
                "/api/paper-trading/stop",
                json={"strategy_id": str(strategy.id)},
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Paper trading session stopped"
        assert body["realized_pnl"] == 500.0
        assert body["trade_count"] == 2

    def test_stop_session_no_active_session_returns_404(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """POST stop with no active session returns 404."""
        strategy = _make_strategy(db, verified_user)

        with patch(
            "app.api.paper_trading.session_manager.stop_session",
            return_value=None,
        ):
            response = client.post(
                "/api/paper-trading/stop",
                json={"strategy_id": str(strategy.id)},
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 404
        assert "No active session" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: status
# ---------------------------------------------------------------------------


class TestGetStatus:
    """Tests for GET /api/paper-trading/status."""

    def test_get_status_no_session_returns_active_false(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET status when no session exists returns active=False."""
        strategy = _make_strategy(db, verified_user)

        with patch(
            "app.api.paper_trading.session_manager.get_session",
            return_value=None,
        ):
            response = client.get(
                f"/api/paper-trading/status?strategy_id={strategy.id}",
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["active"] is False
        assert body["strategy_id"] == str(strategy.id)

    def test_get_status_active_session_returns_portfolio_data(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET status when session active returns balance and trade count."""
        strategy = _make_strategy(db, verified_user)
        portfolio = _make_portfolio(strategy.id, balance=12000.0)
        portfolio.realized_pnl = Decimal("2000.0")
        portfolio.trade_count = 5

        with patch(
            "app.api.paper_trading.session_manager.get_session",
            return_value=portfolio,
        ):
            response = client.get(
                f"/api/paper-trading/status?strategy_id={strategy.id}",
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["active"] is True
        assert body["current_balance"] == 12000.0
        assert body["initial_balance"] == 12000.0
        assert body["realized_pnl"] == 2000.0
        assert body["trade_count"] == 5
        assert body["open_positions"] == 0


# ---------------------------------------------------------------------------
# Tests: history
# ---------------------------------------------------------------------------


class TestGetHistory:
    """Tests for GET /api/paper-trading/history."""

    def test_get_history_empty(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET history for strategy with no closed trades returns empty list."""
        strategy = _make_strategy(db, verified_user)

        response = client.get(
            f"/api/paper-trading/history?strategy_id={strategy.id}",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["trades"] == []
        assert body["total"] == 0

    def test_get_history_returns_closed_trades(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET history returns closed paper trades for the strategy."""
        strategy = _make_strategy(db, verified_user)
        _make_closed_trade(db, strategy, pnl=500.0)
        _make_closed_trade(db, strategy, symbol="ETH/USDT", pnl=200.0)

        response = client.get(
            f"/api/paper-trading/history?strategy_id={strategy.id}",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert len(body["trades"]) == 2

    def test_get_history_includes_pnl_per_trade(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Each trade record includes pnl field."""
        strategy = _make_strategy(db, verified_user)
        _make_closed_trade(db, strategy, pnl=750.0)

        response = client.get(
            f"/api/paper-trading/history?strategy_id={strategy.id}",
            headers=_auth_headers(verified_user),
        )

        body = response.json()
        trade = body["trades"][0]
        assert "pnl" in trade
        assert trade["pnl"] == 750.0
        assert "entry_price" in trade
        assert "exit_price" in trade

    def test_get_history_isolated_per_user(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """User1 cannot query User2's trades via history endpoint."""
        other_user = User(
            id=uuid.uuid4(),
            email="other2@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()
        other_strategy = _make_strategy(db, other_user, "Other Strategy 2")
        _make_closed_trade(db, other_strategy, pnl=9999.0)

        # verified_user tries to query other_user's strategy
        response = client.get(
            f"/api/paper-trading/history?strategy_id={other_strategy.id}",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 404

    def test_get_history_without_strategy_id_returns_all_own_trades(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET history without strategy_id returns all closed trades for user."""
        strategy1 = _make_strategy(db, verified_user, "Strategy A")
        strategy2 = _make_strategy(db, verified_user, "Strategy B")
        _make_closed_trade(db, strategy1, pnl=100.0)
        _make_closed_trade(db, strategy2, pnl=200.0)

        response = client.get(
            "/api/paper-trading/history",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
