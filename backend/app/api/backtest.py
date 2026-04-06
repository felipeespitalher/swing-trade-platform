"""
Backtest API endpoints.

Endpoints:
- POST /api/backtest/run         — Run a backtest against historical OHLCV data
- GET  /api/backtest/strategies  — List user strategies for backtest form
"""

import logging
import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.strategy import Strategy
from app.services.backtest_engine import BacktestEngine, BacktestRequest
from app.services.ohlcv_service import OHLCVService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    strategy_id: str
    symbol: str = "BTC/USDT"
    start_date: str   # 'YYYY-MM-DD'
    end_date: str     # 'YYYY-MM-DD'
    initial_capital: float = 10000.0


class StrategyItem(BaseModel):
    """Compact strategy representation for the backtest form."""

    id: str
    name: str
    type: str
    symbol: str
    timeframe: str
    config: dict

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_strategy_or_404(strategy_id: str, user_id: UUID, db: Session) -> Strategy:
    """Fetch strategy by ID, verifying ownership."""
    try:
        sid = uuid.UUID(strategy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid strategy ID")

    strategy = (
        db.query(Strategy)
        .filter(Strategy.id == sid, Strategy.user_id == user_id)
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run")
def run_backtest(
    body: BacktestRunRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """
    Run a backtest for the given strategy against historical OHLCV data.

    The strategy's timeframe and config are read from the database.
    Candles are fetched from the OHLCV store (up to 2000 candles).
    """
    strategy = _get_strategy_or_404(body.strategy_id, user_id, db)

    # Extract timeframe and indicator config (symbol/timeframe stored inside config)
    config = strategy.config or {}
    timeframe = config.get("timeframe", "1h")
    # Strip meta-keys that are not indicator params
    indicator_config = {k: v for k, v in config.items() if k not in ("symbol", "timeframe")}

    # Fetch OHLCV candles from the database
    candles = OHLCVService.get_candles(
        db=db,
        symbol=body.symbol,
        timeframe=timeframe,
        limit=2000,
    )

    if not candles:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No OHLCV data found for {body.symbol} ({timeframe}). "
                "Ensure the market data has been synced."
            ),
        )

    # Build the backtest request
    backtest_request = BacktestRequest(
        strategy_id=body.strategy_id,
        strategy_type=strategy.type,
        strategy_config=indicator_config,
        symbol=body.symbol,
        timeframe=timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
    )

    result = BacktestEngine().run(backtest_request, candles)

    return {
        "id": result.id,
        "strategy_id": result.strategy_id,
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "status": result.status,
        "metrics": result.metrics,
        "equity_curve": result.equity_curve,
        "trades": result.trades,
        "error": result.error,
    }


@router.get("/strategies")
def list_strategies_for_backtest(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """
    List all strategies belonging to the current user.

    Intended for populating the backtest form strategy selector.
    """
    strategies = (
        db.query(Strategy)
        .filter(Strategy.user_id == user_id)
        .order_by(Strategy.created_at.desc())
        .all()
    )

    result = []
    for s in strategies:
        config = s.config or {}
        result.append({
            "id": str(s.id),
            "name": s.name,
            "type": s.type,
            "symbol": config.get("symbol", "BTC/USDT"),
            "timeframe": config.get("timeframe", "1h"),
            "config": {k: v for k, v in config.items() if k not in ("symbol", "timeframe")},
        })

    return result
