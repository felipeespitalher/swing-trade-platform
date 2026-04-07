"""
Fundamental analysis API endpoints.

Endpoints:
- GET /api/fundamentals/{symbol}  - Fetch fundamental data for a ticker symbol
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.services.fundamental_service import FundamentalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])

_fundamental_service = FundamentalService()


class FundamentalsResponse(BaseModel):
    symbol: str
    market_cap: Optional[int] = None
    pe_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    roe: Optional[float] = None
    dividend_yield: Optional[float] = None
    revenue_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    current_price: Optional[float] = None
    score: float


@router.get("/{symbol}", response_model=FundamentalsResponse)
def get_fundamentals(
    symbol: str,
    user_id: UUID = Depends(get_current_user),
):
    """
    Fetch fundamental data and score for the given ticker symbol.

    Results are cached for 1 hour. Supports any Yahoo Finance ticker
    (e.g. 'AAPL', 'PETR4.SA', 'BTC-USD', 'BOVA11.SA').
    """
    symbol = symbol.upper()

    try:
        data = _fundamental_service.get_fundamentals(symbol)
    except Exception as exc:
        logger.error(f"Failed to fetch fundamentals for {symbol}: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch fundamental data for {symbol}",
        )

    return FundamentalsResponse(**data)
