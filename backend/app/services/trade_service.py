"""
Trade persistence service.

Handles creating and closing paper trades in the database.

Note: The Trade model does not have user_id or direction columns — trades are
associated to users via strategy_id (strategies belong to users). The `reason`
column on the model maps to the exit_reason concept used here.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.trade import Trade

logger = logging.getLogger(__name__)


class TradeService:
    """Service for paper trade persistence."""

    @staticmethod
    def create_paper_trade(
        db: Session,
        strategy_id: str,
        trade_dict: dict,
    ) -> Trade:
        """
        Persist a paper trade entry (open position).

        Args:
            db: Database session
            strategy_id: Strategy UUID as string
            trade_dict: Trade data from PaperTradingEngine.simulate_entry result

        Returns:
            Created Trade object
        """
        trade = Trade(
            id=uuid.uuid4(),
            strategy_id=uuid.UUID(str(strategy_id)),
            symbol=trade_dict["symbol"],
            entry_price=Decimal(str(trade_dict["entry_price"])),
            quantity=Decimal(str(trade_dict["quantity"])),
            is_paper_trade=True,
            entry_date=datetime.now(timezone.utc),
            # exit_date=NULL indicates open position
        )

        db.add(trade)
        db.commit()
        db.refresh(trade)

        logger.info(f"Created paper trade {trade.id} for {trade.symbol}")
        return trade

    @staticmethod
    def close_paper_trade(
        db: Session,
        trade_id: str,
        exit_price: Decimal,
        pnl: Decimal,
        pnl_pct: Optional[Decimal] = None,
        reason: str = "signal",
    ) -> Optional[Trade]:
        """
        Close an open paper trade with exit details.

        Args:
            db: Database session
            trade_id: Trade UUID as string
            exit_price: Exit fill price
            pnl: Realized profit/loss
            pnl_pct: PnL as percentage of cost basis
            reason: Exit reason ('signal', 'stop_loss', 'take_profit', 'manual')

        Returns:
            Updated Trade object, or None if not found
        """
        trade = db.query(Trade).filter(
            Trade.id == uuid.UUID(str(trade_id)),
            Trade.is_paper_trade == True,
            Trade.exit_date == None,
        ).first()

        if not trade:
            logger.warning(f"Paper trade {trade_id} not found or already closed")
            return None

        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_pct = pnl_pct
        trade.exit_date = datetime.now(timezone.utc)
        trade.reason = reason

        db.commit()
        db.refresh(trade)

        logger.info(f"Closed paper trade {trade.id}: pnl={pnl}")
        return trade

    @staticmethod
    def get_open_trades(
        db: Session,
        strategy_id: Optional[str] = None,
    ) -> List[Trade]:
        """Get all open paper trades (exit_date IS NULL)."""
        query = db.query(Trade).filter(
            Trade.is_paper_trade == True,
            Trade.exit_date == None,
        )
        if strategy_id:
            query = query.filter(Trade.strategy_id == uuid.UUID(str(strategy_id)))
        return query.order_by(Trade.entry_date.desc()).all()

    @staticmethod
    def get_closed_trades(
        db: Session,
        strategy_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Trade]:
        """Get closed paper trades, most recent first."""
        query = db.query(Trade).filter(
            Trade.is_paper_trade == True,
            Trade.exit_date != None,
        )
        if strategy_id:
            query = query.filter(Trade.strategy_id == uuid.UUID(str(strategy_id)))
        return query.order_by(Trade.exit_date.desc()).limit(limit).all()
