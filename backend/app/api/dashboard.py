"""
Dashboard API endpoints.

Endpoints:
- GET /api/dashboard/metrics        — Portfolio summary metrics
- GET /api/dashboard/equity-curve   — Portfolio equity over time
- GET /api/dashboard/monthly-returns — P&L by month
- GET /api/dashboard/recent-trades  — Last 20 closed trades
"""

import logging
from datetime import date, datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.strategy import Strategy
from app.models.trade import Trade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

INITIAL_BALANCE = 10000.0

PT_MONTHS = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DashboardMetrics(BaseModel):
    portfolio_value: float
    portfolio_change_pct: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    monthly_pnl: float
    monthly_pnl_pct: float
    active_trades: int


class EquityPoint(BaseModel):
    date: str
    value: float


class MonthlyReturn(BaseModel):
    month: str
    return_: float

    model_config = {"populate_by_name": True}

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        # Rename return_ → return for JSON output
        d["return"] = d.pop("return_")
        return d


class RecentTrade(BaseModel):
    id: str
    symbol: str
    entry_date: str
    entry_price: float
    exit_price: float | None
    pnl_pct: float | None
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_strategy_subquery(user_id: UUID, db: Session):
    """Return a subquery of strategy IDs belonging to the given user."""
    return db.query(Strategy.id).filter(Strategy.user_id == user_id).subquery()


def _closed_trades(user_id: UUID, db: Session) -> List[Trade]:
    """Return all closed paper trades for the user's strategies, ordered by entry_date ASC."""
    user_strategy_ids = _user_strategy_subquery(user_id, db)
    return (
        db.query(Trade)
        .filter(
            Trade.strategy_id.in_(user_strategy_ids),
            Trade.is_paper_trade == True,
            Trade.exit_date.isnot(None),
        )
        .order_by(Trade.entry_date.asc())
        .all()
    )


def _calculate_max_drawdown(trades: List[Trade]) -> float:
    """Calculate maximum drawdown from a list of trades sorted by entry_date ASC."""
    if not trades:
        return 0.0

    balance = INITIAL_BALANCE
    peak = INITIAL_BALANCE
    max_dd = 0.0

    for trade in trades:
        balance += float(trade.pnl or 0)
        if balance > peak:
            peak = balance
        if peak > 0:
            drawdown = (balance - peak) / peak * 100
            if drawdown < max_dd:
                max_dd = drawdown

    return round(max_dd, 2)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=DashboardMetrics)
def get_metrics(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Return portfolio summary metrics for the current user's paper trades."""
    user_strategy_ids = _user_strategy_subquery(user_id, db)

    closed = (
        db.query(Trade)
        .filter(
            Trade.strategy_id.in_(user_strategy_ids),
            Trade.is_paper_trade == True,
            Trade.exit_date.isnot(None),
        )
        .all()
    )

    active_count = (
        db.query(Trade)
        .filter(
            Trade.strategy_id.in_(user_strategy_ids),
            Trade.is_paper_trade == True,
            Trade.exit_date.is_(None),
        )
        .count()
    )

    total = len(closed)
    pnl_values = [float(t.pnl or 0) for t in closed]
    total_pnl = sum(pnl_values)
    portfolio_value = INITIAL_BALANCE + total_pnl
    portfolio_change_pct = ((portfolio_value - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    if total > 0:
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]
        win_rate = len(wins) / total
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
    else:
        win_rate = 0.0
        profit_factor = 0.0

    # Monthly P&L (trades closed this calendar month)
    now = datetime.now(timezone.utc)
    monthly_trades = [
        t for t in closed
        if t.exit_date and t.exit_date.year == now.year and t.exit_date.month == now.month
    ]
    monthly_pnl = sum(float(t.pnl or 0) for t in monthly_trades)
    monthly_pnl_pct = (monthly_pnl / INITIAL_BALANCE) * 100

    # Max drawdown (sorted by entry_date)
    sorted_closed = sorted(closed, key=lambda t: t.entry_date)
    max_drawdown = _calculate_max_drawdown(sorted_closed)

    return DashboardMetrics(
        portfolio_value=round(portfolio_value, 2),
        portfolio_change_pct=round(portfolio_change_pct, 2),
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        max_drawdown=max_drawdown,
        monthly_pnl=round(monthly_pnl, 2),
        monthly_pnl_pct=round(monthly_pnl_pct, 2),
        active_trades=active_count,
    )


@router.get("/equity-curve", response_model=List[EquityPoint])
def get_equity_curve(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Return portfolio equity over time for closed paper trades."""
    trades = _closed_trades(user_id, db)

    today_str = date.today().isoformat()
    start_str = trades[0].entry_date.strftime("%Y-%m-%d") if trades else today_str

    points: List[EquityPoint] = [EquityPoint(date=start_str, value=INITIAL_BALANCE)]
    balance = INITIAL_BALANCE

    for trade in trades:
        balance += float(trade.pnl or 0)
        points.append(
            EquityPoint(
                date=trade.exit_date.strftime("%Y-%m-%d"),
                value=round(balance, 2),
            )
        )

    return points


@router.get("/monthly-returns")
def get_monthly_returns(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Return monthly P&L as percentage of initial balance for last 12 months."""
    trades = _closed_trades(user_id, db)

    # Aggregate P&L by (year, month)
    monthly: dict[tuple[int, int], float] = {}
    for trade in trades:
        if trade.exit_date:
            key = (trade.exit_date.year, trade.exit_date.month)
            monthly[key] = monthly.get(key, 0.0) + float(trade.pnl or 0)

    # Build the last 12 calendar months ending this month
    now = datetime.now(timezone.utc)
    result = []
    for i in range(11, -1, -1):
        # Walk back i months from the current month
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        pnl = monthly.get((year, month), 0.0)
        pct = (pnl / INITIAL_BALANCE) * 100
        result.append({"month": PT_MONTHS[month - 1], "return": round(pct, 2)})

    return result


@router.get("/recent-trades", response_model=List[RecentTrade])
def get_recent_trades(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Return last 20 closed paper trades for the current user."""
    user_strategy_ids = _user_strategy_subquery(user_id, db)

    trades = (
        db.query(Trade)
        .filter(
            Trade.strategy_id.in_(user_strategy_ids),
            Trade.is_paper_trade == True,
            Trade.exit_date.isnot(None),
        )
        .order_by(Trade.exit_date.desc())
        .limit(20)
        .all()
    )

    return [
        RecentTrade(
            id=str(t.id),
            symbol=t.symbol,
            entry_date=t.entry_date.isoformat(),
            entry_price=float(t.entry_price),
            exit_price=float(t.exit_price) if t.exit_price is not None else None,
            pnl_pct=float(t.pnl_pct) if t.pnl_pct is not None else None,
            status="closed",
        )
        for t in trades
    ]
