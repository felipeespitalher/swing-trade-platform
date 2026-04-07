"""
Portfolio model for SQLAlchemy ORM.

Portfolios group strategies together with a unified paper/live mode.
Each portfolio has its own capital allocation and risk profile.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Index, CheckConstraint
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models.user import Base


class Portfolio(Base):
    """Portfolio model grouping strategies with paper/live trading mode."""

    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    capital_allocation = Column(Numeric(20, 2), nullable=False, default=0)
    risk_profile = Column(String(50), nullable=False, default="moderado")
    mode = Column(String(20), nullable=False, default="paper")  # 'paper' | 'live'
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="portfolios")
    strategies = relationship("Strategy", back_populates="portfolio")

    __table_args__ = (
        CheckConstraint("mode IN ('paper', 'live')", name="ck_portfolio_mode"),
        CheckConstraint(
            "risk_profile IN ('conservador', 'moderado', 'agressivo')",
            name="ck_portfolio_risk_profile",
        ),
        Index("idx_portfolios_user", "user_id"),
        Index("idx_portfolios_user_active", "user_id", "is_active"),
        Index("idx_portfolios_mode", "user_id", "mode"),
    )

    def __repr__(self) -> str:
        return (
            f"<Portfolio(id={self.id}, user_id={self.user_id}, "
            f"name={self.name}, mode={self.mode})>"
        )
