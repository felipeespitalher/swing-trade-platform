"""
Celery tasks for OHLCV data fetching and historical backfill.

Tasks:
- fetch_and_store_ohlcv: Periodic task to fetch latest candles
- backfill_ohlcv: One-time task to fetch 180 days of historical data
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta

from celery import shared_task

from app.tasks.celery_app import celery_app
from app.services.ccxt_wrapper import BinanceAdapter, fetch_ohlcv_paginated
from app.services.ohlcv_service import OHLCVService
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Default symbols and timeframes for Phase 2
DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT"]
DEFAULT_TIMEFRAMES = ["1h", "4h", "1d"]

# Backfill: 180 days history
BACKFILL_DAYS = 180


@celery_app.task(
    name="app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    retry_backoff_max=300,
    queue="ohlcv",
)
def fetch_and_store_ohlcv(self, symbol: str, timeframe: str) -> dict:
    """
    Fetch the latest OHLCV candles for a symbol/timeframe and store them.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candlestick timeframe (e.g., '1h')

    Returns:
        Dict with inserted count and symbol info
    """
    logger.info(f"Fetching OHLCV for {symbol} {timeframe}")

    async def _fetch():
        async with BinanceAdapter() as adapter:
            candles = await adapter.fetch_ohlcv(symbol, timeframe, limit=100)
            return candles

    candles = asyncio.run(_fetch())

    if not candles:
        logger.warning(f"No candles returned for {symbol} {timeframe}")
        return {"symbol": symbol, "timeframe": timeframe, "inserted": 0}

    db = SessionLocal()
    try:
        inserted = OHLCVService.upsert_batch(
            db=db,
            candles=candles,
            exchange="binance",
            symbol=symbol,
            timeframe=timeframe,
        )
        logger.info(f"Stored {inserted} new candles for {symbol} {timeframe}")
        return {"symbol": symbol, "timeframe": timeframe, "inserted": inserted}
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.ohlcv_tasks.backfill_ohlcv",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    queue="ohlcv",
)
def backfill_ohlcv(self, symbol: str = None, timeframe: str = None) -> dict:
    """
    Backfill 180 days of historical OHLCV data.

    Idempotent: skips if data already exists for the symbol/timeframe.
    Can backfill a single symbol/timeframe or all defaults.

    Args:
        symbol: Trading pair (optional, defaults to all DEFAULT_SYMBOLS)
        timeframe: Timeframe (optional, defaults to all DEFAULT_TIMEFRAMES)

    Returns:
        Dict with total inserted count per symbol/timeframe
    """
    targets = []
    if symbol and timeframe:
        targets = [(symbol, timeframe)]
    else:
        targets = [(s, tf) for s in DEFAULT_SYMBOLS for tf in DEFAULT_TIMEFRAMES]

    results = {}
    since_ms = int(
        (datetime.now(timezone.utc) - timedelta(days=BACKFILL_DAYS)).timestamp() * 1000
    )

    db = SessionLocal()
    try:
        for sym, tf in targets:
            existing_count = OHLCVService.count_candles(db, sym, tf, "binance")

            if existing_count > 0:
                logger.info(
                    f"Skipping backfill for {sym} {tf}: "
                    f"{existing_count} candles already exist"
                )
                results[f"{sym}_{tf}"] = {"skipped": True, "existing": existing_count}
                continue

            logger.info(f"Starting backfill for {sym} {tf} from {since_ms}")

            async def _backfill(s=sym, t=tf):
                async with BinanceAdapter() as adapter:
                    return await fetch_ohlcv_paginated(
                        adapter=adapter,
                        symbol=s,
                        timeframe=t,
                        since_ms=since_ms,
                    )

            candles = asyncio.run(_backfill())

            inserted = OHLCVService.upsert_batch(
                db=db,
                candles=candles,
                exchange="binance",
                symbol=sym,
                timeframe=tf,
            )
            results[f"{sym}_{tf}"] = {"inserted": inserted, "total_fetched": len(candles)}
            logger.info(f"Backfill complete for {sym} {tf}: {inserted} candles inserted")

    finally:
        db.close()

    return results
