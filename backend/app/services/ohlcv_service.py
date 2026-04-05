"""
OHLCV data persistence and query service.

Provides:
- OHLCVService.upsert_batch: Persist CCXT candles without duplicate errors
- OHLCVService.get_candles: Query sorted candles with filters
- OHLCVService.get_closes_array: Returns np.ndarray of close prices for TA-Lib
"""

import logging
from decimal import Decimal
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.ohlcv import OHLCV

logger = logging.getLogger(__name__)

# Supported timeframes for Phase 2
SUPPORTED_TIMEFRAMES = {"1h", "4h", "1d"}


class OHLCVService:
    """Service for OHLCV data persistence and queries."""

    @staticmethod
    def upsert_batch(
        db: Session,
        candles: List[list],
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """
        Upsert a batch of OHLCV candles (insert or ignore on conflict).

        Uses ON CONFLICT DO NOTHING to handle duplicate timestamps gracefully.
        CCXT candle format: [timestamp_ms, open, high, low, close, volume]

        Args:
            db: Database session
            candles: List of CCXT-format candles
            exchange: Exchange identifier (e.g., 'binance')
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')

        Returns:
            Number of candles inserted (0 if all duplicates)
        """
        if not candles:
            return 0

        rows = [
            {
                "timestamp": int(c[0]),
                "exchange": exchange.lower(),
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "open": Decimal(str(c[1])),
                "high": Decimal(str(c[2])),
                "low": Decimal(str(c[3])),
                "close": Decimal(str(c[4])),
                "volume": Decimal(str(c[5])),
            }
            for c in candles
        ]

        try:
            # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
            # Falls back to SQLite-compatible approach for testing
            dialect = db.bind.dialect.name if db.bind else "postgresql"

            if dialect == "postgresql":
                stmt = pg_insert(OHLCV).values(rows)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["timestamp", "exchange", "symbol", "timeframe"]
                )
                result = db.execute(stmt)
                db.commit()
                inserted = result.rowcount
            else:
                # SQLite fallback for testing
                inserted = 0
                for row in rows:
                    existing = (
                        db.query(OHLCV)
                        .filter(
                            OHLCV.timestamp == row["timestamp"],
                            OHLCV.exchange == row["exchange"],
                            OHLCV.symbol == row["symbol"],
                            OHLCV.timeframe == row["timeframe"],
                        )
                        .first()
                    )
                    if not existing:
                        db.add(OHLCV(**row))
                        inserted += 1
                db.commit()

            logger.debug(
                f"Upserted {inserted}/{len(candles)} candles for "
                f"{exchange}:{symbol} {timeframe}"
            )
            return inserted

        except Exception as e:
            db.rollback()
            logger.error(f"Error upserting OHLCV batch: {e}")
            raise

    @staticmethod
    def get_candles(
        db: Session,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
        limit: int = 500,
        since_ms: Optional[int] = None,
    ) -> List[list]:
        """
        Query OHLCV candles sorted ascending by timestamp.

        Args:
            db: Database session
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            exchange: Exchange identifier (default: 'binance')
            limit: Maximum number of candles to return
            since_ms: Start timestamp filter (milliseconds, inclusive)

        Returns:
            List of CCXT-format candles [timestamp_ms, open, high, low, close, volume]
            sorted ascending by timestamp
        """
        query = (
            db.query(OHLCV)
            .filter(
                OHLCV.symbol == symbol.upper(),
                OHLCV.timeframe == timeframe,
                OHLCV.exchange == exchange.lower(),
            )
        )

        if since_ms is not None:
            query = query.filter(OHLCV.timestamp >= since_ms)

        candles = (
            query
            .order_by(OHLCV.timestamp.asc())
            .limit(limit)
            .all()
        )

        return [c.to_list() for c in candles]

    @staticmethod
    def get_closes_array(
        db: Session,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
        limit: int = 500,
    ) -> np.ndarray:
        """
        Get close prices as numpy array for TA-Lib calculations.

        Args:
            db: Database session
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            exchange: Exchange identifier (default: 'binance')
            limit: Maximum number of close prices to return

        Returns:
            np.ndarray of float64 close prices, shape (N,)
            Returns empty array if no data found
        """
        query = (
            db.query(OHLCV.close)
            .filter(
                OHLCV.symbol == symbol.upper(),
                OHLCV.timeframe == timeframe,
                OHLCV.exchange == exchange.lower(),
            )
            .order_by(OHLCV.timestamp.asc())
            .limit(limit)
        )

        closes = [float(row.close) for row in query.all()]

        if not closes:
            return np.array([], dtype=np.float64)

        return np.array(closes, dtype=np.float64)

    @staticmethod
    def count_candles(
        db: Session,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
    ) -> int:
        """
        Count stored candles for a symbol/timeframe combination.

        Used by backfill task to check if data already exists.

        Args:
            db: Database session
            symbol: Trading pair
            timeframe: Candlestick timeframe
            exchange: Exchange identifier

        Returns:
            Number of stored candles
        """
        return (
            db.query(OHLCV)
            .filter(
                OHLCV.symbol == symbol.upper(),
                OHLCV.timeframe == timeframe,
                OHLCV.exchange == exchange.lower(),
            )
            .count()
        )
