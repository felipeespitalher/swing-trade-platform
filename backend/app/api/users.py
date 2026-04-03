"""
User API endpoints.

Provides endpoints for:
- Getting current user profile
- Updating user settings (timezone, risk limit, name)
- Changing password
- Changing email address
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas.auth import (
    UserResponse,
    UserUpdate,
    UserPasswordChange,
    UserEmailChange,
    OperationResponse,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService
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


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Settings",
    description="Update the authenticated user's settings (name, timezone, risk limit)",
)
async def update_me(
    update: UserUpdate,
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Update current user's settings.

    Args:
        update: User settings to update (optional fields)

    Returns:
        Updated UserResponse with new settings
    """
    # Prepare update data (only include non-None fields)
    update_data = {
        k: v for k, v in update.dict(exclude_unset=True).items() if v is not None
    }

    # If no fields to update, return current user
    if not update_data:
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

    # Update user
    updated_user, error = UserService.update_user(
        db,
        str(current_user.id),
        update_data,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        timezone=updated_user.timezone,
        risk_limit_pct=float(updated_user.risk_limit_pct),
        is_email_verified=updated_user.is_email_verified,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
    )


@router.patch(
    "/me/password",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change the authenticated user's password",
)
async def change_password(
    pwd_change: UserPasswordChange,
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.

    Args:
        pwd_change: Old and new password

    Returns:
        Operation status with success message
    """
    success, error = UserService.change_password(
        db,
        str(current_user.id),
        pwd_change.old_password,
        pwd_change.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return OperationResponse(
        success=True,
        message="Password changed successfully",
    )


@router.patch(
    "/me/email",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Email",
    description="Change the authenticated user's email (requires re-verification)",
)
async def change_email(
    email_change: UserEmailChange,
    current_user=Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Change current user's email address.

    The new email will require verification before it becomes active.
    User must confirm with their current password.

    Args:
        email_change: New email and password confirmation

    Returns:
        Operation status with success message
    """
    success, error = UserService.change_email(
        db,
        str(current_user.id),
        email_change.new_email,
        email_change.password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return OperationResponse(
        success=True,
        message="Email change initiated. Please verify your new email address.",
    )
