"""
Authentication API endpoints.

Provides endpoints for:
- User registration
- User login
- Email verification
- Token refresh
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    TokenRefresh,
    VerificationResponse,
    RegistrationResponse,
)
from app.services.auth_service import AuthService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Register a new user account with email, password, and basic info",
)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    """
    Register a new user.

    - **email**: Valid email address (must be unique)
    - **password**: Must meet strength requirements (8+ chars, uppercase, lowercase, digit, special char)
    - **first_name**: User's first name
    - **last_name**: User's last name

    Returns:
        - **user_id**: ID of newly created user
        - **email**: User's email address
        - **message**: Success message with next steps
    """
    user, error = AuthService.register_user(db, user_data)

    if error:
        if "already registered" in error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return RegistrationResponse(
        message="User registered successfully. Please check your email to verify your account.",
        user_id=user.id,
        email=user.email,
    )


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user and return JWT tokens",
)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Authenticate a user and issue JWT tokens.

    - **email**: User's email address
    - **password**: User's password

    Returns:
        - **access_token**: JWT access token (1-hour expiry)
        - **refresh_token**: JWT refresh token (7-day expiry)
        - **token_type**: Always "bearer"
    """
    tokens, error = AuthService.login_user(db, credentials)

    if error:
        if "verify your email" in error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )

    access_token, refresh_token = tokens

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get(
    "/verify/{token}",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email",
    description="Verify user email address with verification token",
)
async def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Verify a user's email address.

    - **token**: Email verification token sent to user's email

    Returns:
        - **message**: Success or error message
        - **user_id**: User ID if verification successful
    """
    user, error = AuthService.verify_email(db, token)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return VerificationResponse(
        message="Email verified successfully",
        user_id=user.id,
    )


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Generate new access token using refresh token",
)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db),
):
    """
    Generate a new access token using a valid refresh token.

    - **refresh_token**: Valid JWT refresh token

    Returns:
        - **access_token**: New JWT access token
        - **refresh_token**: Same refresh token (unchanged)
        - **token_type**: Always "bearer"
    """
    new_access_token, error = AuthService.refresh_access_token(
        db, token_data.refresh_token
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )

    return Token(
        access_token=new_access_token,
        refresh_token=token_data.refresh_token,
        token_type="bearer",
    )
