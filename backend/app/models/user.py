"""
User model for SQLAlchemy ORM.

Defines the User entity with all authentication and profile fields.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model representing a user account in the system."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    timezone = Column(String(50), default="UTC")
    risk_limit_pct = Column(Numeric(5, 2), default=2.0)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exchange_keys = relationship(
        "ExchangeKey", back_populates="user", cascade="all, delete-orphan"
    )
    strategies = relationship(
        "Strategy", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email={self.email}, verified={self.is_email_verified})>"
