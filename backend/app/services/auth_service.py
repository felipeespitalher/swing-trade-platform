"""
Authentication service layer.

Provides business logic for:
- User registration
- User login
- Email verification
- Token management
- Token refresh
"""

import logging
import secrets
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.schemas.auth import UserRegister, UserLogin
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    PasswordValidator,
    verify_token,
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    def register_user(
        db: Session,
        registration_data: UserRegister,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user.

        Args:
            db: Database session
            registration_data: User registration data

        Returns:
            Tuple of (User object, error message)
            Returns (user, None) on success
            Returns (None, error_message) on failure
        """
        # Validate password strength
        is_valid, error_msg = PasswordValidator.validate(registration_data.password)
        if not is_valid:
            return None, error_msg

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == registration_data.email.lower()).first()
        if existing_user:
            if not existing_user.is_email_verified:
                # Resend verification email for unverified accounts
                verification_token = secrets.token_urlsafe(32)
                existing_user.email_verification_token = verification_token
                db.commit()
                EmailService.send_verification_email(
                    email=existing_user.email,
                    user_id=str(existing_user.id),
                    verification_token=verification_token,
                    first_name=existing_user.first_name,
                )
                logger.info(f"Verification email resent for unverified user: {existing_user.email}")
                return None, "Email already registered but not verified. A new verification email has been sent."
            return None, "Email already registered"

        try:
            # Generate verification token
            verification_token = secrets.token_urlsafe(32)

            # Create new user
            new_user = User(
                id=uuid.uuid4(),
                email=registration_data.email.lower(),
                password_hash=hash_password(registration_data.password),
                first_name=registration_data.first_name,
                last_name=registration_data.last_name,
                email_verification_token=verification_token,
                is_email_verified=False,
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            # Send verification email
            email_sent = EmailService.send_verification_email(
                email=new_user.email,
                user_id=str(new_user.id),
                verification_token=verification_token,
                first_name=new_user.first_name,
            )

            if not email_sent:
                logger.warning(
                    f"Verification email failed to send for user {new_user.id}, "
                    "but user was created successfully"
                )

            logger.info(f"New user registered: {new_user.email}")
            return new_user, None

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during registration: {e}")
            return None, "Email already registered"
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during registration: {e}")
            return None, "Registration failed. Please try again."

    @staticmethod
    def login_user(
        db: Session,
        login_data: UserLogin,
    ) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
        """
        Authenticate a user and issue tokens.

        Args:
            db: Database session
            login_data: User login credentials

        Returns:
            Tuple of (tokens, error_message)
            Returns ((access_token, refresh_token), None) on success
            Returns (None, error_message) on failure
        """
        try:
            # Find user by email
            user = db.query(User).filter(User.email == login_data.email.lower()).first()

            if not user:
                logger.warning(f"Login attempt for non-existent user: {login_data.email}")
                return None, "Invalid email or password"

            # Check if email is verified
            if not user.is_email_verified:
                logger.warning(f"Login attempt with unverified email: {login_data.email}")
                return None, "Please verify your email before logging in"

            # Verify password
            if not verify_password(login_data.password, user.password_hash):
                logger.warning(f"Failed login attempt for user: {login_data.email}")
                return None, "Invalid email or password"

            # Create tokens
            access_token = create_access_token(
                user_id=str(user.id),
                email=user.email,
            )
            refresh_token = create_refresh_token(
                user_id=str(user.id),
                email=user.email,
            )

            logger.info(f"User logged in successfully: {user.email}")
            return (access_token, refresh_token), None

        except Exception as e:
            logger.error(f"Error during login: {e}")
            return None, "Login failed. Please try again."

    @staticmethod
    def verify_email(
        db: Session,
        verification_token: str,
    ) -> Tuple[Optional[User], Optional[str], Optional[str], Optional[str]]:
        """
        Verify a user's email address.

        Args:
            db: Database session
            verification_token: Email verification token

        Returns:
            Tuple of (User, error, access_token, refresh_token)
            Returns (user, None, access_token, refresh_token) on success
            Returns (None, error_message, None, None) on failure
        """
        try:
            # Find user by verification token
            user = db.query(User).filter(
                User.email_verification_token == verification_token
            ).first()

            if not user:
                logger.warning(f"Invalid verification token attempted")
                return None, "Invalid or expired verification token", None, None

            # Mark email as verified
            user.is_email_verified = True
            user.email_verification_token = None

            db.commit()
            db.refresh(user)

            access_token = create_access_token(user_id=str(user.id), email=user.email)
            refresh_token = create_refresh_token(user_id=str(user.id), email=user.email)

            logger.info(f"Email verified for user: {user.email}")
            return user, None, access_token, refresh_token

        except Exception as e:
            db.rollback()
            logger.error(f"Error verifying email: {e}")
            return None, "Email verification failed. Please try again.", None, None

    @staticmethod
    def refresh_access_token(
        db: Session,
        refresh_token: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate a new access token from a refresh token.

        Args:
            db: Database session
            refresh_token: JWT refresh token

        Returns:
            Tuple of (access_token, error_message)
            Returns (access_token, None) on success
            Returns (None, error_message) on failure
        """
        try:
            # Verify refresh token
            token_payload = verify_token(refresh_token, token_type="refresh")

            if not token_payload:
                logger.warning("Invalid refresh token")
                return None, "Invalid or expired refresh token"

            # Find user
            try:
                user_id = uuid.UUID(token_payload.sub)
            except (ValueError, AttributeError):
                logger.warning(f"Invalid user ID in token: {token_payload.sub}")
                return None, "Invalid token"

            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                logger.warning(f"User not found for refresh token: {token_payload.sub}")
                return None, "User not found"

            # Create new access token
            new_access_token = create_access_token(
                user_id=str(user.id),
                email=user.email,
            )

            logger.info(f"Access token refreshed for user: {user.email}")
            return new_access_token, None

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None, "Token refresh failed. Please login again."

    @staticmethod
    def get_current_user(
        db: Session,
        access_token: str,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Get the current authenticated user from access token.

        Args:
            db: Database session
            access_token: JWT access token

        Returns:
            Tuple of (User object, error message)
            Returns (user, None) on success
            Returns (None, error_message) on failure
        """
        try:
            # Verify access token
            token_payload = verify_token(access_token, token_type="access")

            if not token_payload:
                return None, "Invalid or expired token"

            # Find user
            try:
                user_id = uuid.UUID(token_payload.sub)
            except (ValueError, AttributeError):
                return None, "Invalid token"

            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return None, "User not found"

            return user, None

        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None, "Failed to get user information"

    @staticmethod
    def request_password_reset(
        db: Session,
        email: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate a password reset token and send reset email.

        Always returns success (even for unknown emails) to prevent
        user enumeration attacks.

        Args:
            db: Database session
            email: User's email address

        Returns:
            Tuple of (reset_token_or_None, error_message_or_None)
        """
        try:
            user = db.query(User).filter(User.email == email.lower()).first()

            if not user:
                # Return success anyway to avoid user enumeration
                logger.info(f"Password reset requested for unknown email: {email}")
                return None, None

            reset_token = create_password_reset_token(
                user_id=str(user.id),
                email=user.email,
                pwd_hash=user.password_hash,
            )

            EmailService.send_password_reset_email(
                email=user.email,
                first_name=user.first_name or "Usuário",
                reset_token=reset_token,
            )

            logger.info(f"Password reset requested for: {user.email}")
            return reset_token, None

        except Exception as e:
            logger.error(f"Error requesting password reset: {e}")
            return None, "Failed to process password reset request"

    @staticmethod
    def reset_password(
        db: Session,
        token: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset user password using a valid reset token.

        Args:
            db: Database session
            token: JWT password reset token
            new_password: New plain-text password

        Returns:
            Tuple of (success, error_message)
        """
        from app.core.security import settings
        from jose import JWTError, jwt

        try:
            # Decode without type check first to get payload
            try:
                payload = jwt.decode(
                    token, settings.secret_key, algorithms=[settings.algorithm]
                )
            except JWTError:
                return False, "Token inválido ou expirado"

            if payload.get("type") != "password_reset":
                return False, "Token inválido"

            user_id_str = payload.get("sub")
            pwd_fp = payload.get("pwd_fp", "")

            try:
                user_id = uuid.UUID(user_id_str)
            except (ValueError, TypeError):
                return False, "Token inválido"

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "Usuário não encontrado"

            # Check fingerprint — invalidates token if password already changed
            if user.password_hash[-16:] != pwd_fp:
                return False, "Token já utilizado ou expirado"

            # Validate new password strength
            is_valid, error_msg = PasswordValidator.validate(new_password)
            if not is_valid:
                return False, error_msg

            from datetime import timezone as _tz
            user.password_hash = hash_password(new_password)
            user.updated_at = __import__("datetime").datetime.now(_tz.utc)
            db.commit()

            logger.info(f"Password reset successfully for: {user.email}")
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error resetting password: {e}")
            return False, "Falha ao redefinir senha"
