"""
Security utilities for JWT tokens and password hashing.

Provides functions for:
- Password hashing and verification with bcrypt
- JWT token creation and validation
- Token payload management
"""

from datetime import datetime, timedelta
from typing import Optional, Any
import re
import logging

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
# Using pbkdf2_sha256 which is built-in and reliable
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # Subject (user ID)
    email: str
    exp: int  # Expiration time
    iat: int  # Issued at
    type: str  # "access" or "refresh"
    iss: str = "swing-trade-platform"  # Issuer


class PasswordValidator:
    """Validates password strength requirements."""

    MIN_LENGTH = 8
    UPPERCASE_PATTERN = re.compile(r"[A-Z]")
    LOWERCASE_PATTERN = re.compile(r"[a-z]")
    DIGIT_PATTERN = re.compile(r"\d")
    SPECIAL_PATTERN = re.compile(r"[!@#$%^&*()_+\-=\[\]{};:'\",.<>?/\\|`~]")

    @classmethod
    def validate(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength.

        Args:
            password: Password string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"

        if not cls.UPPERCASE_PATTERN.search(password):
            return False, "Password must contain at least 1 uppercase letter"

        if not cls.LOWERCASE_PATTERN.search(password):
            return False, "Password must contain at least 1 lowercase letter"

        if not cls.DIGIT_PATTERN.search(password):
            return False, "Password must contain at least 1 digit"

        if not cls.SPECIAL_PATTERN.search(password):
            return False, "Password must contain at least 1 special character (!@#$%^&*)"

        return True, None


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-SHA256.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to compare against

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to embed in token
        email: User email to embed in token
        expires_delta: Custom expiration delta (uses default if None)

    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = settings.access_token_expire

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
        "iss": "swing-trade-platform",
    }

    encoded_jwt = jwt.encode(
        payload, settings.secret_key, algorithm=settings.algorithm
    )

    return encoded_jwt


def create_refresh_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID to embed in token
        email: User email to embed in token
        expires_delta: Custom expiration delta (uses default if None)

    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = settings.refresh_token_expire

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
        "iss": "swing-trade-platform",
    }

    encoded_jwt = jwt.encode(
        payload, settings.secret_key, algorithm=settings.algorithm
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenPayload if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        # Validate token type
        if payload.get("type") != token_type:
            logger.warning(
                f"Token type mismatch: expected {token_type}, got {payload.get('type')}"
            )
            return None

        return TokenPayload(**payload)

    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None
