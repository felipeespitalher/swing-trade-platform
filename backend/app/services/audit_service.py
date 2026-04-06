"""
Audit logging service.

Provides business logic for:
- Creating audit log entries
- Querying audit logs by user, action, date range, or resource
- Ensuring append-only immutability of audit records
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging operations."""

    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[UUID],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            db: Database session
            user_id: ID of user performing the action
            action: Type of action (e.g., 'LOGIN', 'STRATEGY_CREATE', 'EXCHANGE_KEY_ADD')
            resource_type: Type of resource affected (e.g., 'strategy', 'exchange_key')
            resource_id: ID of resource affected
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AuditLog: Created audit log entry
        """
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            db.add(log)
            db.commit()
            db.refresh(log)

            logger.debug(
                f"Audit log created: user={user_id}, action={action}, "
                f"resource={resource_type}/{resource_id}"
            )
            return log

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating audit log: {e}", exc_info=True)
            raise

    @staticmethod
    def get_user_audit_logs(
        db: Session,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        action_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit logs for a specific user.

        Args:
            db: Database session
            user_id: User ID to filter by
            limit: Number of results to return
            offset: Number of results to skip
            action_filter: Optional specific action to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (list of AuditLog entries, total count)
        """
        try:
            # Build query
            query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

            # Apply action filter if provided
            if action_filter:
                query = query.filter(AuditLog.action == action_filter)

            # Apply date range filter if provided
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)

            # Get total count
            total = query.count()

            # Order by most recent first and apply pagination
            logs = (
                query.order_by(desc(AuditLog.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return logs, total

        except Exception as e:
            logger.error(f"Error retrieving user audit logs: {e}", exc_info=True)
            raise

    @staticmethod
    def get_resource_audit_history(
        db: Session,
        resource_type: str,
        resource_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit history for a specific resource.

        Args:
            db: Database session
            resource_type: Type of resource
            resource_id: ID of resource
            limit: Number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of AuditLog entries, total count)
        """
        try:
            query = db.query(AuditLog).filter(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
            )

            # Get total count
            total = query.count()

            # Order by most recent first and apply pagination
            logs = (
                query.order_by(desc(AuditLog.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return logs, total

        except Exception as e:
            logger.error(f"Error retrieving resource audit history: {e}", exc_info=True)
            raise

    @staticmethod
    def get_audit_logs_by_action(
        db: Session,
        action: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit logs filtered by action type.

        Args:
            db: Database session
            action: Action type to filter by
            limit: Number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of AuditLog entries, total count)
        """
        try:
            query = db.query(AuditLog).filter(AuditLog.action == action)

            # Get total count
            total = query.count()

            # Order by most recent first and apply pagination
            logs = (
                query.order_by(desc(AuditLog.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return logs, total

        except Exception as e:
            logger.error(f"Error retrieving audit logs by action: {e}", exc_info=True)
            raise

    @staticmethod
    def get_audit_logs_by_date_range(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[UUID] = None,
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit logs within a date range.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range
            limit: Number of results to return
            offset: Number of results to skip
            user_id: Optional user ID to filter by

        Returns:
            Tuple of (list of AuditLog entries, total count)
        """
        try:
            query = db.query(AuditLog).filter(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                )
            )

            # Apply user filter if provided
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            # Get total count
            total = query.count()

            # Order by most recent first and apply pagination
            logs = (
                query.order_by(desc(AuditLog.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return logs, total

        except Exception as e:
            logger.error(f"Error retrieving audit logs by date range: {e}", exc_info=True)
            raise

    @staticmethod
    def get_recent_user_actions(
        db: Session,
        user_id: UUID,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get a user's audit logs from the past N hours.

        Args:
            db: Database session
            user_id: User ID
            hours: Number of hours to look back (default 24)
            limit: Maximum number of results

        Returns:
            List of AuditLog entries
        """
        try:
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            logs = (
                db.query(AuditLog)
                .filter(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.created_at >= start_time,
                    )
                )
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
                .all()
            )

            return logs

        except Exception as e:
            logger.error(f"Error retrieving recent user actions: {e}", exc_info=True)
            raise
