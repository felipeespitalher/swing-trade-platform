"""
Strategy management API endpoints.

Endpoints:
- GET    /api/strategies         - List user's strategies
- POST   /api/strategies         - Create strategy
- GET    /api/strategies/{id}    - Get strategy by ID
- PUT    /api/strategies/{id}    - Update strategy
- DELETE /api/strategies/{id}    - Delete strategy
- PATCH  /api/strategies/{id}/status - Enable/disable strategy
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.strategy import Strategy
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

SUPPORTED_STRATEGY_TYPES = {"rsi_only", "macd_only", "rsi_macd"}
SUPPORTED_TIMEFRAMES = {"1h", "4h", "1d"}


class StrategyCreate(BaseModel):
    name: str
    type: str  # 'rsi_only', 'macd_only', 'rsi_macd'
    config: dict
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in SUPPORTED_STRATEGY_TYPES:
            raise ValueError(
                f"Unsupported strategy type: {v}. Must be one of {SUPPORTED_STRATEGY_TYPES}"
            )
        return v

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v):
        if v not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {v}. Must be one of {SUPPORTED_TIMEFRAMES}"
            )
        return v


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v):
        if v is not None and v not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {v}. Must be one of {SUPPORTED_TIMEFRAMES}"
            )
        return v


class StrategyStatusUpdate(BaseModel):
    status: str  # 'active' | 'inactive'

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in {"active", "inactive"}:
            raise ValueError("status must be 'active' or 'inactive'")
        return v


class StrategyResponse(BaseModel):
    id: str
    name: str
    type: str
    config: dict
    symbol: str
    timeframe: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @classmethod
    def from_strategy(cls, strategy: Strategy) -> "StrategyResponse":
        """Build response from Strategy ORM object, extracting symbol/timeframe from config."""
        config = strategy.config or {}
        return cls(
            id=str(strategy.id),
            name=strategy.name,
            type=strategy.type,
            config={k: v for k, v in config.items() if k not in ("symbol", "timeframe")},
            symbol=config.get("symbol", "BTC/USDT"),
            timeframe=config.get("timeframe", "1h"),
            is_active=strategy.is_active,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
        )


def _get_strategy_or_404(strategy_id: str, user_id: UUID, db: Session) -> Strategy:
    """Get strategy by ID, ensuring it belongs to the current user."""
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


@router.get("", response_model=List[StrategyResponse])
def list_strategies(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """List all strategies for the current user."""
    strategies = (
        db.query(Strategy)
        .filter(Strategy.user_id == user_id)
        .order_by(Strategy.created_at.desc())
        .all()
    )
    return [StrategyResponse.from_strategy(s) for s in strategies]


@router.post("", response_model=StrategyResponse, status_code=201)
def create_strategy(
    data: StrategyCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Create a new strategy."""
    # Store symbol and timeframe in config dict since the model doesn't have those columns
    merged_config = dict(data.config)
    merged_config["symbol"] = data.symbol
    merged_config["timeframe"] = data.timeframe

    strategy = Strategy(
        id=uuid.uuid4(),
        user_id=user_id,
        name=data.name,
        type=data.type,
        config=merged_config,
        is_active=False,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return StrategyResponse.from_strategy(strategy)


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get a specific strategy by ID."""
    strategy = _get_strategy_or_404(strategy_id, user_id, db)
    return StrategyResponse.from_strategy(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: str,
    data: StrategyUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Update a strategy's name, config, symbol, or timeframe."""
    strategy = _get_strategy_or_404(strategy_id, user_id, db)

    if data.name is not None:
        strategy.name = data.name

    # Merge symbol/timeframe updates into config
    if data.config is not None or data.symbol is not None or data.timeframe is not None:
        current_config = dict(strategy.config or {})
        if data.config is not None:
            # Replace indicator params but preserve symbol/timeframe keys
            for k, v in data.config.items():
                current_config[k] = v
        if data.symbol is not None:
            current_config["symbol"] = data.symbol
        if data.timeframe is not None:
            current_config["timeframe"] = data.timeframe
        strategy.config = current_config

    strategy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(strategy)
    return StrategyResponse.from_strategy(strategy)


@router.delete("/{strategy_id}", status_code=204)
def delete_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Delete a strategy."""
    strategy = _get_strategy_or_404(strategy_id, user_id, db)
    db.delete(strategy)
    db.commit()


@router.patch("/{strategy_id}/status", response_model=StrategyResponse)
def update_strategy_status(
    strategy_id: str,
    data: StrategyStatusUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Enable or disable a strategy."""
    strategy = _get_strategy_or_404(strategy_id, user_id, db)

    strategy.is_active = data.status == "active"
    strategy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(strategy)

    # Audit log (best-effort, do not fail on errors)
    try:
        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=f"strategy_{data.status}",
            resource_type="strategy",
            resource_id=strategy.id,
            new_values={"strategy_name": strategy.name, "new_status": data.status},
        )
    except Exception as exc:
        logger.warning(f"Audit log failed for strategy status change: {exc}")

    return StrategyResponse.from_strategy(strategy)
