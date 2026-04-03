"""
Dependency injection utilities for API endpoints.

Provides FastAPI dependencies for extracting and validating request data,
particularly for JWT authentication.
"""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.security import verify_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials = Depends(security)) -> UUID:
    """
    Extract and validate JWT token from request headers.

    This is a FastAPI dependency that validates the Authorization header
    and returns the user ID from the JWT payload.

    Args:
        credentials: HTTPBearer credentials extracted from Authorization header

    Returns:
        UUID: User ID from token payload

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials

    # Verify the token
    payload = verify_token(token, token_type="access")

    if payload is None:
        logger.warning("Invalid or expired token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(payload.sub)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user_id in token: {payload.sub}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    return user_id
