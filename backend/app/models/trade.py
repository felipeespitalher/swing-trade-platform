"""
Trade model for SQLAlchemy ORM.

Defines the Trade entity for historical trades and paper trading records.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Boolean, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.user import Base


class Trade(Base):
    """Trade model representing a historical or paper trade."""

    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symbol = Column(String(20), nullable=False)
    entry_date = Column(DateTime(timezone=True), nullable=False)
    exit_date = Column(DateTime(timezone=True), nullable=True)
    entry_price = Column(Numeric(20, 8), nullable=False)
    exit_price = Column(Numeric(20, 8), nullable=True)
    quantity = Column(Numeric(20, 8), nullable=False)
    pnl = Column(Numeric(20, 8), nullable=True)
    pnl_pct = Column(Numeric(10, 4), nullable=True)
    reason = Column(String(100), nullable=True)
    is_paper_trade = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationship to Strategy
    strategy = relationship("Strategy", back_populates="trades")

    __table_args__ = (
        Index("idx_trades_strategy", "strategy_id"),
        Index("idx_trades_symbol_date", "symbol", "entry_date"),
        Index("idx_trades_entry_date", "entry_date"),
        CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
    )

    def __repr__(self) -> str:
        """String representation of Trade."""
        return (
            f"<Trade(id={self.id}, symbol={self.symbol}, "
            f"entry_date={self.entry_date}, quantity={self.quantity})>"
        )
