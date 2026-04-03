"""
Row-Level Security (RLS) utilities for multi-tenant data isolation.

This module provides utilities for:
1. Setting user context for RLS policies
2. Creating RLS-aware database sessions
3. Testing RLS policies
4. Documentation of RLS implementation
"""

import logging
from uuid import UUID
from typing import Optional, ContextManager
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def set_user_context(session: Session, user_id: UUID) -> None:
    """
    Set the current user ID for RLS policies in this session.

    This function MUST be called in every database transaction that needs
    RLS enforcement. The user_id is stored in a PostgreSQL local variable
    that RLS policies reference via current_user_id() function.

    Args:
        session: SQLAlchemy session
        user_id: UUID of the current user

    Raises:
        ValueError: If user_id is None or invalid

    Example:
        db = SessionLocal()
        set_user_context(db, user_id)
        # Now queries are automatically filtered by RLS
        keys = db.query(ExchangeKey).all()  # Only user's keys
    """
    if user_id is None:
        raise ValueError("user_id cannot be None")

    user_id_str = str(user_id)

    try:
        # Use SET LOCAL to scope the variable to this transaction
        # This is PostgreSQL-specific and will be reset after COMMIT/ROLLBACK
        session.execute(
            text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": user_id_str}
        )
        logger.debug(f"RLS context set for user_id={user_id}")
    except Exception as e:
        logger.error(f"Failed to set RLS context: {e}")
        raise


def clear_user_context(session: Session) -> None:
    """
    Clear the current user ID for RLS policies.

    This is usually not needed as SET LOCAL is automatically reset
    at transaction end, but provided for explicit cleanup if needed.

    Args:
        session: SQLAlchemy session
    """
    try:
        session.execute(text("RESET app.current_user_id"))
        logger.debug("RLS context cleared")
    except Exception as e:
        logger.warning(f"Failed to clear RLS context (may already be cleared): {e}")


@contextmanager
def user_context(session: Session, user_id: UUID) -> ContextManager:
    """
    Context manager for setting RLS user context.

    Ensures context is properly set for a block of database operations.
    Context is automatically cleared when exiting the block.

    Args:
        session: SQLAlchemy session
        user_id: UUID of the current user

    Yields:
        The session with RLS context set

    Example:
        with user_context(db, user_id) as session:
            keys = session.query(ExchangeKey).all()
            # RLS context is active here
        # RLS context automatically cleared
    """
    set_user_context(session, user_id)
    try:
        yield session
    finally:
        # SET LOCAL is automatically reset at transaction end,
        # but we explicitly clear for safety
        try:
            clear_user_context(session)
        except Exception:
            pass


def verify_rls_enabled(session: Session) -> dict:
    """
    Verify that RLS is enabled on all required tables.

    Returns information about RLS status for each user-owned table.
    This is useful for debugging and verification.

    Args:
        session: SQLAlchemy session (must be connected to PostgreSQL)

    Returns:
        Dictionary with RLS status for each table:
        {
            "table_name": {
                "rls_enabled": bool,
                "policy_count": int,
                "policies": [list of policy names]
            }
        }

    Example:
        status = verify_rls_enabled(db)
        for table, info in status.items():
            if not info["rls_enabled"]:
                print(f"RLS NOT enabled on {table}!")
    """
    tables = ["users", "exchange_keys", "strategies", "trades", "audit_logs"]
    status = {}

    for table in tables:
        try:
            # Check if RLS is enabled
            result = session.execute(
                text(f"""
                SELECT rowsecurity FROM pg_tables
                WHERE tablename = '{table}' AND schemaname = 'public';
                """)
            ).fetchone()

            if result:
                rls_enabled = result[0]
            else:
                rls_enabled = False

            # Get list of policies
            policies = session.execute(
                text(f"""
                SELECT policyname FROM pg_policies
                WHERE tablename = '{table}' AND schemaname = 'public'
                ORDER BY policyname;
                """)
            ).fetchall()

            policy_names = [p[0] for p in policies]

            status[table] = {
                "rls_enabled": rls_enabled,
                "policy_count": len(policy_names),
                "policies": policy_names
            }

        except Exception as e:
            logger.error(f"Failed to check RLS status for {table}: {e}")
            status[table] = {
                "rls_enabled": False,
                "policy_count": 0,
                "policies": [],
                "error": str(e)
            }

    return status


def check_rls_health(session: Session) -> tuple[bool, str]:
    """
    Quick health check for RLS configuration.

    Returns:
        Tuple of (is_healthy: bool, message: str)

    Examples:
        is_healthy, msg = check_rls_health(db)
        if not is_healthy:
            logger.error(f"RLS health check failed: {msg}")
    """
    tables = ["users", "exchange_keys", "strategies", "trades", "audit_logs"]
    status = verify_rls_enabled(session)

    for table in tables:
        if table not in status:
            return False, f"Table {table} status unknown"

        if not status[table].get("rls_enabled"):
            return False, f"RLS not enabled on table: {table}"

        if status[table].get("policy_count") == 0:
            return False, f"No RLS policies found on table: {table}"

    return True, "All RLS policies are correctly configured"


class RLSLogger:
    """
    Logging helper for RLS-related operations.

    Provides consistent logging for:
    - RLS context setup
    - Data access via RLS
    - RLS policy violations (access denied)
    """

    @staticmethod
    def log_data_access(
        table: str,
        operation: str,
        user_id: UUID,
        resource_id: Optional[UUID] = None
    ) -> None:
        """
        Log a data access operation with RLS context.

        Args:
            table: Table name
            operation: SELECT, INSERT, UPDATE, DELETE
            user_id: User performing the operation
            resource_id: ID of the resource being accessed (optional)
        """
        if resource_id:
            logger.debug(
                f"RLS access: {operation} on {table} (user_id={user_id}, "
                f"resource_id={resource_id})"
            )
        else:
            logger.debug(
                f"RLS access: {operation} on {table} (user_id={user_id})"
            )

    @staticmethod
    def log_access_denied(
        table: str,
        operation: str,
        user_id: UUID,
        resource_id: UUID
    ) -> None:
        """
        Log an access denial (RLS policy blocked access).

        Args:
            table: Table name
            operation: SELECT, INSERT, UPDATE, DELETE
            user_id: User who was denied access
            resource_id: ID of the resource
        """
        logger.warning(
            f"RLS access DENIED: {operation} on {table} "
            f"(user_id={user_id}, resource_id={resource_id})"
        )

    @staticmethod
    def log_context_set(user_id: UUID) -> None:
        """Log when RLS context is set for a user."""
        logger.debug(f"RLS context set for user_id={user_id}")

    @staticmethod
    def log_context_error(error: str) -> None:
        """Log RLS context errors."""
        logger.error(f"RLS context error: {error}")


# ============================================================================
# RLS QUERY BUILDERS (Optional - for explicit safety)
# ============================================================================

class RLSQueryBuilder:
    """
    Helper for building RLS-safe queries.

    While RLS handles most filtering at the database level,
    this builder can add explicit application-level filters
    for defense-in-depth and safety during development.
    """

    @staticmethod
    def filter_by_user(query, model_class, user_id: UUID):
        """
        Add user_id filter to a query.

        Works with models that have a 'user_id' column.
        This is redundant with RLS but provides defense-in-depth.

        Args:
            query: SQLAlchemy query object
            model_class: Model class (e.g., ExchangeKey)
            user_id: User ID to filter by

        Returns:
            Filtered query
        """
        if not hasattr(model_class, "user_id"):
            raise ValueError(f"{model_class.__name__} does not have user_id column")

        return query.filter(model_class.user_id == user_id)

    @staticmethod
    def filter_trade_by_user(query, trade_model, user_id: UUID):
        """
        Add user filter to trades via strategy relationship.

        Trades don't have user_id directly; they must be filtered
        through the strategy relationship.

        Args:
            query: SQLAlchemy query object
            trade_model: Trade model class
            user_id: User ID to filter by

        Returns:
            Filtered query
        """
        from app.models.strategy import Strategy

        return query.filter(
            trade_model.strategy_id.in_(
                query.session.query(Strategy.id).filter(Strategy.user_id == user_id)
            )
        )
