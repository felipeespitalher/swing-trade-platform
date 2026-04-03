"""
Audit logging API endpoints.

Provides endpoints for:
- Getting current user's audit logs
- Filtering by action type
- Filtering by date range
- Viewing resource change history
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, status, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID

from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.models.audit_log import AuditLog
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])


async def get_current_user_dependency(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Dependency to extract and validate current user from JWT token.

    Args:
        authorization: Authorization header (Bearer <token>)
        db: Database session

    Returns:
        User object if valid token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    user, error = AuthService.get_current_user(db, token)

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


class AuditLogResponse:
    """Response model for audit logs."""

    def __init__(self, log: AuditLog):
        """Initialize from AuditLog model."""
        self.id = str(log.id)
        self.user_id = str(log.user_id) if log.user_id else None
        self.action = log.action
        self.resource_type = log.resource_type
        self.resource_id = str(log.resource_id) if log.resource_id else None
        self.old_values = log.old_values
        self.new_values = log.new_values
        self.ip_address = str(log.ip_address) if log.ip_address else None
        self.user_agent = log.user_agent
        self.created_at = log.created_at.isoformat()

    def dict(self):
        """Return as dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at,
        }


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get Current User's Audit Logs",
    description="Get the authenticated user's complete audit trail",
)
async def get_my_audit_logs(
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get current user's audit logs.

    Query Parameters:
        - **limit**: Number of results to return (default: 100, max: 500)
        - **offset**: Number of results to skip for pagination (default: 0)

    Returns:
        - **logs**: List of audit log entries
        - **total**: Total number of entries for this user
        - **limit**: Limit used in query
        - **offset**: Offset used in query
    """
    try:
        logs, total = AuditService.get_user_audit_logs(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        return {
            "logs": [AuditLogResponse(log).dict() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error retrieving audit logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs",
        )


@router.get(
    "/me/actions",
    status_code=status.HTTP_200_OK,
    summary="Get Audit Logs by Action Type",
    description="Get the authenticated user's audit logs filtered by action type",
)
async def get_my_audit_by_action(
    action: str = Query(..., description="Action type to filter by"),
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get current user's audit logs filtered by action type.

    Query Parameters:
        - **action**: Action type to filter by (e.g., 'LOGIN', 'STRATEGY_CREATE')
        - **limit**: Number of results to return (default: 100, max: 500)
        - **offset**: Number of results to skip for pagination (default: 0)

    Returns:
        - **logs**: List of audit log entries
        - **total**: Total number of entries for this action
        - **action**: Action filter used
        - **limit**: Limit used in query
        - **offset**: Offset used in query
    """
    try:
        logs, total = AuditService.get_user_audit_logs(
            db=db,
            user_id=current_user.id,
            action_filter=action,
            limit=limit,
            offset=offset,
        )

        return {
            "logs": [AuditLogResponse(log).dict() for log in logs],
            "total": total,
            "action": action,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error retrieving audit logs by action: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs",
        )


@router.get(
    "/me/date-range",
    status_code=status.HTTP_200_OK,
    summary="Get Audit Logs by Date Range",
    description="Get the authenticated user's audit logs within a date range",
)
async def get_my_audit_by_date_range(
    start_date: str = Query(..., description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (ISO format: YYYY-MM-DD)"),
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get current user's audit logs within a date range.

    Query Parameters:
        - **start_date**: Start date in ISO format (YYYY-MM-DD)
        - **end_date**: End date in ISO format (YYYY-MM-DD)
        - **limit**: Number of results to return (default: 100, max: 500)
        - **offset**: Number of results to skip for pagination (default: 0)

    Returns:
        - **logs**: List of audit log entries
        - **total**: Total number of entries in date range
        - **start_date**: Start date filter used
        - **end_date**: End date filter used
        - **limit**: Limit used in query
        - **offset**: Offset used in query
    """
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date + "T00:00:00")
        end = datetime.fromisoformat(end_date + "T23:59:59")

        logs, total = AuditService.get_user_audit_logs(
            db=db,
            user_id=current_user.id,
            start_date=start,
            end_date=end,
            limit=limit,
            offset=offset,
        )

        return {
            "logs": [AuditLogResponse(log).dict() for log in logs],
            "total": total,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format: YYYY-MM-DD",
        )
    except Exception as e:
        logger.error(f"Error retrieving audit logs by date range: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs",
        )


@router.get(
    "/{resource_type}/{resource_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Resource Change History",
    description="Get complete audit history for a specific resource",
)
async def get_resource_audit_history(
    resource_type: str = Path(..., description="Type of resource"),
    resource_id: str = Path(..., description="ID of resource"),
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get complete audit history for a specific resource.

    Path Parameters:
        - **resource_type**: Type of resource (e.g., 'strategy', 'exchange_key')
        - **resource_id**: ID of the resource (UUID)

    Query Parameters:
        - **limit**: Number of results to return (default: 100, max: 500)
        - **offset**: Number of results to skip for pagination (default: 0)

    Returns:
        - **logs**: List of audit log entries showing resource changes
        - **total**: Total number of entries for this resource
        - **resource_type**: Resource type
        - **resource_id**: Resource ID
        - **limit**: Limit used in query
        - **offset**: Offset used in query
    """
    try:
        # Parse resource ID as UUID
        try:
            resource_uuid = UUID(resource_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resource ID format. Must be a valid UUID.",
            )

        logs, total = AuditService.get_resource_audit_history(
            db=db,
            resource_type=resource_type,
            resource_id=resource_uuid,
            limit=limit,
            offset=offset,
        )

        return {
            "logs": [AuditLogResponse(log).dict() for log in logs],
            "total": total,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving resource audit history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource audit history",
        )
