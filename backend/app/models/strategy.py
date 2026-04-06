"""
Strategy model for SQLAlchemy ORM.

Defines the Strategy entity for trading strategies with JSON configuration.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Integer, Index
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models.user import Base


class Strategy(Base):
    """Strategy model representing a trading strategy."""

    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationship to User
    user = relationship("User", back_populates="strategies")

    # Relationship to Trades
    trades = relationship(
        "Trade", back_populates="strategy", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_strategies_user", "user_id"),
        Index("idx_strategies_user_active", "user_id", "is_active"),
        Index("idx_strategies_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of Strategy."""
        return (
            f"<Strategy(id={self.id}, user_id={self.user_id}, "
            f"name={self.name}, type={self.type}, is_active={self.is_active})>"
        )
