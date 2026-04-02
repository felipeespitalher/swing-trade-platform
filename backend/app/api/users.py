"""
User API endpoints.

Provides endpoints for:
- Getting current user profile
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas.auth import UserResponse
from app.services.auth_service import AuthService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


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


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get the authenticated user's profile information",
)
async def get_me(
    current_user=Depends(get_current_user_dependency),
):
    """
    Get current authenticated user's profile.

    Returns:
        - **id**: User ID
        - **email**: User's email
        - **first_name**: User's first name
        - **last_name**: User's last name
        - **timezone**: User's timezone
        - **risk_limit_pct**: Risk limit percentage
        - **is_email_verified**: Email verification status
        - **created_at**: Account creation date
        - **updated_at**: Last update date
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        timezone=current_user.timezone,
        risk_limit_pct=float(current_user.risk_limit_pct),
        is_email_verified=current_user.is_email_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
