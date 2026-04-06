"""
Paper trading session management using Redis.

Session state is stored in Redis for fast access and survives
FastAPI worker restarts. On stop, open positions are flushed to DB.

Redis key format: paper:session:{strategy_id}
"""

import json
import logging
import os
from decimal import Decimal
from typing import Optional
import uuid

import redis

from app.services.paper_trading_engine import PaperPortfolio, PaperTradingEngine

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_KEY_PREFIX = "paper:session:"
SESSION_TTL_SECONDS = 86400 * 7  # 7 days


def _get_redis_client() -> redis.Redis:
    """Get Redis client (synchronous for simplicity)."""
    return redis.from_url(REDIS_URL, decode_responses=True)


class PaperTradingSessionManager:
    """Manages paper trading sessions in Redis."""

    def start_session(
        self,
        strategy_id: str,
        user_id: str,
        initial_balance: Decimal = Decimal("10000"),
        testnet: bool = True,
    ) -> PaperPortfolio:
        """
        Start a new paper trading session.

        Creates a fresh PaperPortfolio and stores it in Redis.
        If a session already exists for this strategy, returns the existing one.

        Args:
            strategy_id: Strategy UUID as string
            user_id: User UUID as string
            initial_balance: Starting USDT balance
            testnet: If True, use Binance testnet (always True for Phase 2)

        Returns:
            PaperPortfolio instance
        """
        redis_client = _get_redis_client()
        key = f"{SESSION_KEY_PREFIX}{strategy_id}"

        # Check for existing session
        existing = redis_client.get(key)
        if existing:
            logger.info(f"Resuming existing session for strategy {strategy_id}")
            return PaperPortfolio.from_dict(json.loads(existing))

        # Create new portfolio
        portfolio = PaperPortfolio(
            strategy_id=uuid.UUID(strategy_id),
            initial_balance=initial_balance,
        )

        # Store in Redis
        redis_client.setex(
            key,
            SESSION_TTL_SECONDS,
            json.dumps(portfolio.to_dict()),
        )

        logger.info(
            f"Started paper session for strategy {strategy_id} "
            f"with balance={initial_balance}"
        )
        return portfolio

    def get_session(self, strategy_id: str) -> Optional[PaperPortfolio]:
        """
        Retrieve a paper trading session from Redis.

        Args:
            strategy_id: Strategy UUID as string

        Returns:
            PaperPortfolio if session exists, None otherwise
        """
        redis_client = _get_redis_client()
        key = f"{SESSION_KEY_PREFIX}{strategy_id}"

        data = redis_client.get(key)
        if not data:
            return None

        return PaperPortfolio.from_dict(json.loads(data))

    def save_session(self, portfolio: PaperPortfolio) -> None:
        """
        Persist portfolio state to Redis.

        Call after each trade to ensure session survives restarts.
        """
        redis_client = _get_redis_client()
        key = f"{SESSION_KEY_PREFIX}{str(portfolio.strategy_id)}"

        redis_client.setex(
            key,
            SESSION_TTL_SECONDS,
            json.dumps(portfolio.to_dict()),
        )

    def stop_session(
        self,
        strategy_id: str,
        db,
    ) -> Optional[dict]:
        """
        Stop a paper trading session.

        Flushes open positions summary and removes session from Redis.

        Args:
            strategy_id: Strategy UUID as string
            db: Database session (for future use when flushing open trades)

        Returns:
            Final portfolio summary dict, or None if no active session
        """
        redis_client = _get_redis_client()
        key = f"{SESSION_KEY_PREFIX}{strategy_id}"

        data = redis_client.get(key)
        if not data:
            logger.warning(f"No active session found for strategy {strategy_id}")
            return None

        portfolio = PaperPortfolio.from_dict(json.loads(data))

        summary = {
            "strategy_id": strategy_id,
            "initial_balance": float(portfolio.initial_balance),
            "final_balance": float(portfolio.current_balance),
            "realized_pnl": float(portfolio.realized_pnl),
            "trade_count": portfolio.trade_count,
            "open_positions": len(portfolio.open_positions),
        }

        # Remove session from Redis
        redis_client.delete(key)
        logger.info(f"Stopped paper session for strategy {strategy_id}: {summary}")

        return summary

    def session_exists(self, strategy_id: str) -> bool:
        """Check if an active session exists for a strategy."""
        redis_client = _get_redis_client()
        return bool(redis_client.exists(f"{SESSION_KEY_PREFIX}{strategy_id}"))
