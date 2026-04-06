"""
Paper trading control API endpoints.

Endpoints:
- POST /api/paper-trading/start   — Start a paper trading session
- POST /api/paper-trading/stop    — Stop a paper trading session
- GET  /api/paper-trading/status  — Get portfolio state + open trades
- GET  /api/paper-trading/history — Get closed trade history
"""

import logging
import uuid
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.strategy import Strategy
from app.services.paper_trading_session import PaperTradingSessionManager
from app.services.trade_service import TradeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paper-trading", tags=["paper-trading"])
session_manager = PaperTradingSessionManager()


class StartSessionRequest(BaseModel):
    strategy_id: str
    initial_balance: float = 10000.0


class StopSessionRequest(BaseModel):
    strategy_id: str


class SessionStatusResponse(BaseModel):
    strategy_id: str
    active: bool
    current_balance: Optional[float] = None
    initial_balance: Optional[float] = None
    realized_pnl: Optional[float] = None
    trade_count: Optional[int] = None
    open_positions: Optional[int] = None


def _get_strategy_for_user(db: Session, strategy_id_str: str, user_id: UUID) -> Strategy:
    """
    Look up a strategy by ID that belongs to the given user.

    Raises HTTPException 400 if strategy_id is invalid UUID,
    HTTPException 404 if strategy not found or belongs to another user.
    """
    try:
        sid = uuid.UUID(strategy_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid strategy_id")

    strategy = (
        db.query(Strategy)
        .filter(
            Strategy.id == sid,
            Strategy.user_id == user_id,
        )
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return strategy


@router.post("/start")
def start_session(
    data: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user),
):
    """Start a paper trading session for a strategy."""
    _get_strategy_for_user(db, data.strategy_id, current_user_id)

    try:
        portfolio = session_manager.start_session(
            strategy_id=data.strategy_id,
            user_id=str(current_user_id),
            initial_balance=Decimal(str(data.initial_balance)),
        )
        return {
            "message": "Paper trading session started",
            "strategy_id": data.strategy_id,
            "initial_balance": float(portfolio.initial_balance),
        }
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start session")


@router.post("/stop")
def stop_session(
    data: StopSessionRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user),
):
    """Stop a paper trading session."""
    _get_strategy_for_user(db, data.strategy_id, current_user_id)

    summary = session_manager.stop_session(
        strategy_id=data.strategy_id,
        db=db,
    )

    if summary is None:
        raise HTTPException(
            status_code=404, detail="No active session for this strategy"
        )

    return {
        "message": "Paper trading session stopped",
        **summary,
    }


@router.get("/status", response_model=SessionStatusResponse)
def get_status(
    strategy_id: str = Query(..., description="Strategy UUID"),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user),
):
    """Get current portfolio state for an active paper trading session."""
    _get_strategy_for_user(db, strategy_id, current_user_id)

    portfolio = session_manager.get_session(strategy_id)

    if portfolio is None:
        return SessionStatusResponse(
            strategy_id=strategy_id,
            active=False,
        )

    return SessionStatusResponse(
        strategy_id=strategy_id,
        active=True,
        current_balance=float(portfolio.current_balance),
        initial_balance=float(portfolio.initial_balance),
        realized_pnl=float(portfolio.realized_pnl),
        trade_count=portfolio.trade_count,
        open_positions=len(portfolio.open_positions),
    )


@router.get("/history")
def get_history(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy UUID"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user),
):
    """
    Get closed paper trade history.

    If strategy_id is provided, verifies ownership before querying.
    Without strategy_id, returns all closed trades for strategies owned
    by the current user.
    """
    if strategy_id is not None:
        # Ownership check — raises 400/404 if strategy_id is invalid or not owned
        _get_strategy_for_user(db, strategy_id, current_user_id)
        trades = TradeService.get_closed_trades(
            db=db,
            strategy_id=strategy_id,
            limit=limit,
        )
    else:
        # Return trades for all strategies owned by this user
        user_strategy_ids = [
            str(s.id)
            for s in db.query(Strategy.id)
            .filter(Strategy.user_id == current_user_id)
            .all()
        ]
        if not user_strategy_ids:
            return {"trades": [], "total": 0}

        # Collect trades across owned strategies (limited total)
        from app.models.trade import Trade

        trades = (
            db.query(Trade)
            .filter(
                Trade.is_paper_trade == True,
                Trade.exit_date != None,
                Trade.strategy_id.in_(
                    [uuid.UUID(sid) for sid in user_strategy_ids]
                ),
            )
            .order_by(Trade.exit_date.desc())
            .limit(limit)
            .all()
        )

    return {
        "trades": [
            {
                "id": str(t.id),
                "symbol": t.symbol,
                "entry_price": float(t.entry_price) if t.entry_price else None,
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "pnl": float(t.pnl) if t.pnl else None,
                "entry_date": t.entry_date.isoformat() if t.entry_date else None,
                "exit_date": t.exit_date.isoformat() if t.exit_date else None,
            }
            for t in trades
        ],
        "total": len(trades),
    }
