"""
Tests for market data API endpoints.

Covers:
- GET /api/market/ticker
- GET /api/market/ohlcv
- GET /api/market/balance
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import User
from app.models.ohlcv import OHLCV
from app.services.ohlcv_service import OHLCVService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(user: User) -> dict:
    """Return Authorization headers for the given user."""
    token = create_access_token(user_id=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _make_ticker_data(symbol: str = "BTC/USDT", last: float = 50000.0) -> dict:
    """Build a minimal CCXT ticker dict."""
    return {
        "symbol": symbol,
        "last": last,
        "bid": last - 10.0,
        "ask": last + 10.0,
        "quoteVolume": 1234567.89,
        "volume": 25.0,
        "timestamp": 1700000000000,
    }


def _insert_candles(db: Session, symbol: str, timeframe: str, count: int = 3) -> None:
    """Insert test OHLCV candles directly into the database."""
    base_ts = 1700000000000
    for i in range(count):
        candle = OHLCV(
            timestamp=base_ts + i * 3600_000,
            exchange="binance",
            symbol=symbol.upper(),
            timeframe=timeframe,
            open=Decimal("50000"),
            high=Decimal("51000"),
            low=Decimal("49000"),
            close=Decimal("50500"),
            volume=Decimal("100"),
        )
        db.add(candle)
    db.commit()


# ---------------------------------------------------------------------------
# Tests: ticker
# ---------------------------------------------------------------------------


class TestGetTicker:
    """Tests for GET /api/market/ticker."""

    def test_market_ticker_returns_price(
        self, client: TestClient, verified_user: User
    ):
        """GET /api/market/ticker returns last price for supported symbol."""
        ticker_data = _make_ticker_data("BTC/USDT", 50000.0)
        mock_adapter = AsyncMock()
        mock_adapter.fetch_ticker = AsyncMock(return_value=ticker_data)
        mock_adapter.__aenter__ = AsyncMock(return_value=mock_adapter)
        mock_adapter.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.market_data.BinanceAdapter",
            return_value=mock_adapter,
        ):
            response = client.get(
                "/api/market/ticker?symbol=BTC/USDT",
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "BTC/USDT"
        assert body["last"] == 50000.0

    def test_market_ticker_price_is_positive_numeric(
        self, client: TestClient, verified_user: User
    ):
        """Ticker response last price is a positive numeric value."""
        ticker_data = _make_ticker_data("ETH/USDT", 3000.0)
        mock_adapter = AsyncMock()
        mock_adapter.fetch_ticker = AsyncMock(return_value=ticker_data)
        mock_adapter.__aenter__ = AsyncMock(return_value=mock_adapter)
        mock_adapter.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.market_data.BinanceAdapter", return_value=mock_adapter):
            response = client.get(
                "/api/market/ticker?symbol=ETH/USDT",
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["last"], (int, float))
        assert body["last"] > 0

    def test_market_ticker_includes_bid_ask(
        self, client: TestClient, verified_user: User
    ):
        """Ticker response includes bid and ask fields."""
        ticker_data = _make_ticker_data("BTC/USDT", 50000.0)
        mock_adapter = AsyncMock()
        mock_adapter.fetch_ticker = AsyncMock(return_value=ticker_data)
        mock_adapter.__aenter__ = AsyncMock(return_value=mock_adapter)
        mock_adapter.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.market_data.BinanceAdapter", return_value=mock_adapter):
            response = client.get(
                "/api/market/ticker?symbol=BTC/USDT",
                headers=_auth_headers(verified_user),
            )

        assert response.status_code == 200
        body = response.json()
        assert "bid" in body
        assert "ask" in body
        assert body["bid"] < body["last"] < body["ask"]

    def test_market_unsupported_symbol_returns_400(
        self, client: TestClient, verified_user: User
    ):
        """GET ticker with unsupported symbol returns 400."""
        response = client.get(
            "/api/market/ticker?symbol=DOGE/USDT",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 400
        assert "Unsupported symbol" in response.json()["detail"]

    def test_market_ticker_unauthenticated_returns_403(self, client: TestClient):
        """GET ticker without JWT returns 403 (HTTPBearer behaviour)."""
        response = client.get("/api/market/ticker?symbol=BTC/USDT")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tests: OHLCV
# ---------------------------------------------------------------------------


class TestGetOHLCV:
    """Tests for GET /api/market/ohlcv."""

    def test_market_ohlcv_returns_candles(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET /api/market/ohlcv returns stored candles."""
        _insert_candles(db, "BTC/USDT", "1h", count=3)

        response = client.get(
            "/api/market/ohlcv?symbol=BTC/USDT&timeframe=1h&limit=10",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "BTC/USDT"
        assert body["timeframe"] == "1h"
        assert body["count"] == 3
        assert len(body["candles"]) == 3

    def test_market_ohlcv_respects_limit_param(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET /api/market/ohlcv?limit=2 returns at most 2 candles."""
        _insert_candles(db, "BTC/USDT", "1h", count=5)

        response = client.get(
            "/api/market/ohlcv?symbol=BTC/USDT&timeframe=1h&limit=2",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["count"] <= 2
        assert len(body["candles"]) <= 2

    def test_market_ohlcv_candles_sorted_ascending_by_timestamp(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """OHLCV candles are returned in ascending chronological order."""
        _insert_candles(db, "ETH/USDT", "4h", count=4)

        response = client.get(
            "/api/market/ohlcv?symbol=ETH/USDT&timeframe=4h&limit=10",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        candles = response.json()["candles"]
        if len(candles) >= 2:
            timestamps = [c[0] for c in candles]
            assert timestamps == sorted(timestamps), "Candles not sorted ascending"

    def test_market_ohlcv_empty_returns_zero_count(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """GET /api/market/ohlcv with no stored data returns count=0."""
        response = client.get(
            "/api/market/ohlcv?symbol=ETH/USDT&timeframe=1d&limit=10",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 0
        assert body["candles"] == []

    def test_market_ohlcv_unsupported_symbol_returns_400(
        self, client: TestClient, verified_user: User
    ):
        """GET /api/market/ohlcv with unsupported symbol returns 400."""
        response = client.get(
            "/api/market/ohlcv?symbol=DOGE/USDT&timeframe=1h",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 400

    def test_market_ohlcv_unsupported_timeframe_returns_400(
        self, client: TestClient, verified_user: User
    ):
        """GET /api/market/ohlcv with unsupported timeframe returns 400."""
        response = client.get(
            "/api/market/ohlcv?symbol=BTC/USDT&timeframe=5m",
            headers=_auth_headers(verified_user),
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: balance
# ---------------------------------------------------------------------------


class TestGetBalance:
    """Tests for GET /api/market/balance."""

    def test_balance_returns_testnet_balances(
        self, client: TestClient, verified_user: User
    ):
        """GET /api/market/balance returns asset balances."""
        response = client.get(
            "/api/market/balance",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert "balances" in body
        assert "exchange" in body

    def test_balance_response_includes_usdt_balance(
        self, client: TestClient, verified_user: User
    ):
        """Balance response includes USDT as primary trading currency."""
        response = client.get(
            "/api/market/balance",
            headers=_auth_headers(verified_user),
        )

        assert response.status_code == 200
        body = response.json()
        assert "USDT" in body["balances"]
        usdt = body["balances"]["USDT"]
        assert "free" in usdt
        assert "total" in usdt
        assert usdt["total"] > 0

    def test_balance_requires_authentication(self, client: TestClient):
        """GET /api/market/balance returns 403 for unauthenticated requests."""
        response = client.get("/api/market/balance")
        assert response.status_code == 403
