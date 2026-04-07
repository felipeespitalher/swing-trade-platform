"""
Portfolio management API endpoints.

Endpoints:
- GET    /api/portfolios                    - List user's portfolios
- POST   /api/portfolios                    - Create portfolio
- GET    /api/portfolios/{id}               - Get portfolio by ID
- PUT    /api/portfolios/{id}               - Update portfolio
- DELETE /api/portfolios/{id}               - Delete portfolio
- GET    /api/portfolios/{id}/strategies    - List strategies in portfolio
- PATCH  /api/portfolios/{id}/strategies    - Assign/remove strategies
- GET    /api/portfolios/{id}/market-status - Check if portfolio's market is open
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.strategy import Strategy
from app.models.trade import Trade
from app.services.market_hours import MarketHoursService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])

VALID_MODES = {"paper", "live"}
VALID_RISK_PROFILES = {"conservador", "moderado", "agressivo"}


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capital_allocation: float = 0.0
    risk_profile: str = "moderado"
    mode: str = "paper"

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}")
        return v

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, v):
        if v not in VALID_RISK_PROFILES:
            raise ValueError(f"risk_profile must be one of {VALID_RISK_PROFILES}")
        return v


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capital_allocation: Optional[float] = None
    risk_profile: Optional[str] = None
    mode: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v is not None and v not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}")
        return v

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, v):
        if v is not None and v not in VALID_RISK_PROFILES:
            raise ValueError(f"risk_profile must be one of {VALID_RISK_PROFILES}")
        return v


class StrategyAssignment(BaseModel):
    strategy_ids: List[str]


class PortfolioStrategyResponse(BaseModel):
    id: str
    name: str
    type: str
    is_active: bool
    symbol: str
    timeframe: str
    win_rate: Optional[float] = None
    total_trades: int = 0

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    capital_allocation: float
    risk_profile: str
    mode: str
    is_active: bool
    strategy_count: int = 0
    total_pnl: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @classmethod
    def from_portfolio(
        cls,
        portfolio: Portfolio,
        strategy_count: int = 0,
        total_pnl: Optional[float] = None,
    ) -> "PortfolioResponse":
        return cls(
            id=str(portfolio.id),
            name=portfolio.name,
            description=portfolio.description,
            capital_allocation=float(portfolio.capital_allocation),
            risk_profile=portfolio.risk_profile,
            mode=portfolio.mode,
            is_active=portfolio.is_active,
            strategy_count=strategy_count,
            total_pnl=total_pnl,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_portfolio_or_404(portfolio_id: str, user_id: UUID, db: Session) -> Portfolio:
    try:
        pid = uuid.UUID(portfolio_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid portfolio ID")

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == pid, Portfolio.user_id == user_id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


def _portfolio_stats(db: Session, portfolio_id: UUID) -> dict:
    """Compute aggregated stats for a portfolio."""
    strategy_count = (
        db.query(func.count(Strategy.id))
        .filter(Strategy.portfolio_id == portfolio_id)
        .scalar()
    ) or 0

    # Aggregate PnL from all trades of strategies in this portfolio
    pnl_row = (
        db.query(func.sum(Trade.pnl))
        .join(Strategy, Trade.strategy_id == Strategy.id)
        .filter(
            Strategy.portfolio_id == portfolio_id,
            Trade.exit_date.isnot(None),
        )
        .scalar()
    )

    return {
        "strategy_count": strategy_count,
        "total_pnl": float(pnl_row) if pnl_row is not None else None,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[PortfolioResponse])
def list_portfolios(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """List all portfolios for the current user."""
    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at.desc())
        .all()
    )
    result = []
    for p in portfolios:
        stats = _portfolio_stats(db, p.id)
        result.append(PortfolioResponse.from_portfolio(p, **stats))
    return result


@router.post("", response_model=PortfolioResponse, status_code=201)
def create_portfolio(
    data: PortfolioCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Create a new portfolio."""
    portfolio = Portfolio(
        id=uuid.uuid4(),
        user_id=user_id,
        name=data.name,
        description=data.description,
        capital_allocation=Decimal(str(data.capital_allocation)),
        risk_profile=data.risk_profile,
        mode=data.mode,
        is_active=True,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    try:
        AuditService.log_action(
            db=db,
            user_id=user_id,
            action="portfolio_created",
            resource_type="portfolio",
            resource_id=portfolio.id,
            new_values={"name": data.name, "mode": data.mode},
        )
    except Exception as exc:
        logger.warning(f"Audit log failed: {exc}")

    return PortfolioResponse.from_portfolio(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get a specific portfolio by ID."""
    portfolio = _get_portfolio_or_404(portfolio_id, user_id, db)
    stats = _portfolio_stats(db, portfolio.id)
    return PortfolioResponse.from_portfolio(portfolio, **stats)


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: str,
    data: PortfolioUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Update a portfolio."""
    portfolio = _get_portfolio_or_404(portfolio_id, user_id, db)

    if data.name is not None:
        portfolio.name = data.name
    if data.description is not None:
        portfolio.description = data.description
    if data.capital_allocation is not None:
        portfolio.capital_allocation = Decimal(str(data.capital_allocation))
    if data.risk_profile is not None:
        portfolio.risk_profile = data.risk_profile
    if data.mode is not None:
        portfolio.mode = data.mode
    if data.is_active is not None:
        portfolio.is_active = data.is_active

    portfolio.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(portfolio)

    stats = _portfolio_stats(db, portfolio.id)
    return PortfolioResponse.from_portfolio(portfolio, **stats)


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Delete a portfolio. Strategies are unlinked (portfolio_id set to NULL)."""
    portfolio = _get_portfolio_or_404(portfolio_id, user_id, db)

    # Unlink strategies before deleting (ON DELETE SET NULL handles this in DB too)
    db.query(Strategy).filter(Strategy.portfolio_id == portfolio.id).update(
        {"portfolio_id": None}, synchronize_session=False
    )

    db.delete(portfolio)
    db.commit()


@router.get("/{portfolio_id}/strategies", response_model=List[PortfolioStrategyResponse])
def list_portfolio_strategies(
    portfolio_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """List all strategies assigned to this portfolio."""
    portfolio = _get_portfolio_or_404(portfolio_id, user_id, db)

    strategies = (
        db.query(Strategy)
        .filter(Strategy.portfolio_id == portfolio.id, Strategy.user_id == user_id)
        .all()
    )

    result = []
    for s in strategies:
        config = s.config or {}

        # Get trade stats
        row = (
            db.query(
                func.count(Trade.id).label("total"),
                func.sum(case((Trade.pnl > 0, 1), else_=0)).label("wins"),
            )
            .filter(Trade.strategy_id == s.id, Trade.exit_date.isnot(None))
            .first()
        )
        total = row.total or 0
        wins = int(row.wins or 0)

        result.append(PortfolioStrategyResponse(
            id=str(s.id),
            name=s.name,
            type=s.type,
            is_active=s.is_active,
            symbol=config.get("symbol", ""),
            timeframe=config.get("timeframe", ""),
            win_rate=round(wins / total, 4) if total > 0 else None,
            total_trades=total,
        ))

    return result


@router.patch("/{portfolio_id}/strategies", response_model=List[str])
def assign_strategies(
    portfolio_id: str,
    data: StrategyAssignment,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """
    Assign strategies to this portfolio.
    Replaces the current assignment — pass empty list to unlink all.
    """
    portfolio = _get_portfolio_or_404(portfolio_id, user_id, db)
    pid = portfolio.id

    # Unlink all current strategies from this portfolio
    db.query(Strategy).filter(
        Strategy.portfolio_id == pid, Strategy.user_id == user_id
    ).update({"portfolio_id": None}, synchronize_session=False)

    # Link new strategies
    assigned_ids = []
    for sid_str in data.strategy_ids:
        try:
            sid = uuid.UUID(sid_str)
        except ValueError:
            continue

        strategy = (
            db.query(Strategy)
            .filter(Strategy.id == sid, Strategy.user_id == user_id)
            .first()
        )
        if strategy:
            strategy.portfolio_id = pid
            assigned_ids.append(str(strategy.id))

    db.commit()
    return assigned_ids


@router.get("/{portfolio_id}/market-status")
def get_market_status(
    portfolio_id: str,
    exchange: str = "b3",
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """
    Check if the market for this portfolio is currently open.

    exchange: 'b3', 'binance', 'clear_xp', 'profit_pro', etc.
    """
    # Validate portfolio ownership
    _get_portfolio_or_404(portfolio_id, user_id, db)

    market_status = MarketHoursService.get_market_status(exchange)
    return market_status


@router.get("/market-hours/{exchange}")
def get_market_hours(
    exchange: str,
    user_id: UUID = Depends(get_current_user),
):
    """Get market hours and current open/close status for any exchange."""
    market_status = MarketHoursService.get_market_status(exchange)
    return market_status
