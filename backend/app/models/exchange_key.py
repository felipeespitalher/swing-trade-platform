"""
Exchange API Key model for SQLAlchemy ORM.

Defines the ExchangeKey entity for storing encrypted API credentials.
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.user import Base


class ExchangeKey(Base):
    """ExchangeKey model representing encrypted API credentials for trading exchanges."""

    __tablename__ = "exchange_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exchange = Column(String(50), nullable=False)
    api_key_encrypted = Column(String, nullable=False)
    api_secret_encrypted = Column(String, nullable=False)
    encryption_iv = Column(String(50), default="v1")
    is_testnet = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to User
    user = relationship("User", back_populates="exchange_keys")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "exchange", "is_testnet", name="uq_user_exchange_testnet"
        ),
        Index("idx_exchange_keys_user", "user_id"),
        Index("idx_exchange_keys_active", "is_active"),
        Index("idx_exchange_keys_exchange", "exchange"),
    )

    def __repr__(self) -> str:
        """String representation of ExchangeKey."""
        return (
            f"<ExchangeKey(id={self.id}, user_id={self.user_id}, "
            f"exchange={self.exchange}, is_testnet={self.is_testnet}, "
            f"is_active={self.is_active})>"
        )
