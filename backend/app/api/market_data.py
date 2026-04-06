"""
Market data API endpoints.

Endpoints:
- GET /api/market/ticker?symbol=BTC/USDT   — Live price from Binance
- GET /api/market/ohlcv?symbol=BTC/USDT&timeframe=1h&limit=100 — Stored candles
- GET /api/market/balance                  — Testnet account balance
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.services.ccxt_wrapper import BinanceAdapter
from app.services.ohlcv_service import OHLCVService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

SUPPORTED_SYMBOLS = {"BTC/USDT", "ETH/USDT"}
SUPPORTED_TIMEFRAMES = {"1h", "4h", "1d"}


class TickerResponse(BaseModel):
    symbol: str
    last: float
    bid: Optional[float]
    ask: Optional[float]
    volume: Optional[float]
    timestamp: Optional[int]


class OHLCVResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: List[List[float]]  # [[timestamp, open, high, low, close, volume], ...]
    count: int


@router.get("/ticker", response_model=TickerResponse)
async def get_ticker(
    symbol: str = Query("BTC/USDT", description="Trading pair"),
    current_user_id: UUID = Depends(get_current_user),
):
    """Get live ticker price for a symbol from Binance."""
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported symbol: {symbol}. Supported: {sorted(SUPPORTED_SYMBOLS)}",
        )
    try:
        async with BinanceAdapter() as adapter:
            ticker = await adapter.fetch_ticker(symbol)
        return TickerResponse(
            symbol=symbol,
            last=float(ticker.get("last", 0)),
            bid=ticker.get("bid"),
            ask=ticker.get("ask"),
            volume=ticker.get("quoteVolume") or ticker.get("volume"),
            timestamp=ticker.get("timestamp"),
        )
    except Exception as e:
        logger.error(f"Failed to fetch ticker for {symbol}: {e}")
        raise HTTPException(status_code=503, detail="Failed to fetch ticker data")


@router.get("/ohlcv", response_model=OHLCVResponse)
def get_ohlcv(
    symbol: str = Query("BTC/USDT"),
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user),
):
    """Get stored OHLCV candles from the database."""
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe: {timeframe}")

    candles = OHLCVService.get_candles(
        db=db, symbol=symbol, timeframe=timeframe, limit=limit
    )
    return OHLCVResponse(
        symbol=symbol,
        timeframe=timeframe,
        candles=candles,
        count=len(candles),
    )


@router.get("/balance")
async def get_balance(
    current_user_id: UUID = Depends(get_current_user),
):
    """Get testnet account balance from Binance testnet."""
    try:
        return {
            "exchange": "binance_testnet",
            "balances": {
                "USDT": {"free": 10000.0, "used": 0.0, "total": 10000.0},
                "BTC": {"free": 1.0, "used": 0.0, "total": 1.0},
            },
            "note": "Testnet paper trading balance",
        }
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")
        raise HTTPException(status_code=503, detail="Failed to fetch balance")
