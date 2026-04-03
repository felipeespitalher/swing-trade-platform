"""
User service layer for account management.

Provides business logic for:
- Getting user profile
- Updating user settings (timezone, risk limit, name)
- Changing password
- Changing email address
"""

import logging
import secrets
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.core.security import (
    hash_password,
    verify_password,
    PasswordValidator,
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class UserService:
    """Service for handling user account operations."""

    @staticmethod
    def get_user(db: Session, user_id: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User ID (as string UUID)

        Returns:
            Tuple of (User object, error message)
            Returns (user, None) on success
            Returns (None, error_message) on failure
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return None, "User not found"

            return user, None

        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None, "Failed to retrieve user"

    @staticmethod
    def update_user(
        db: Session,
        user_id: str,
        update_data: dict,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Update user settings.

        Args:
            db: Database session
            user_id: User ID (as string UUID)
            update_data: Dict with fields to update (first_name, last_name, timezone, risk_limit_pct)

        Returns:
            Tuple of (User object, error message)
            Returns (updated_user, None) on success
            Returns (None, error_message) on failure
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return None, "User not found"

            # Update only provided fields
            if "first_name" in update_data and update_data["first_name"] is not None:
                user.first_name = update_data["first_name"]

            if "last_name" in update_data and update_data["last_name"] is not None:
                user.last_name = update_data["last_name"]

            if "timezone" in update_data and update_data["timezone"] is not None:
                # Validate timezone format (basic check - should be valid IANA timezone)
                timezone = update_data["timezone"]
                # Try to use pytz for validation if available
                try:
                    import pytz

                    if timezone not in pytz.all_timezones:
                        return None, f"Invalid timezone: {timezone}"
                except ImportError:
                    # If pytz not available, do basic validation
                    if not isinstance(timezone, str) or len(timezone) < 3:
                        return None, f"Invalid timezone format: {timezone}"

                user.timezone = timezone

            if "risk_limit_pct" in update_data and update_data["risk_limit_pct"] is not None:
                risk_limit = update_data["risk_limit_pct"]
                if not (0.1 <= risk_limit <= 100.0):
                    return None, "Risk limit must be between 0.1 and 100.0"

                user.risk_limit_pct = risk_limit

            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)

            logger.info(f"User updated: {user.email}")
            return user, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user: {e}")
            return None, "Failed to update user settings"

    @staticmethod
    def change_password(
        db: Session,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password.

        Args:
            db: Database session
            user_id: User ID (as string UUID)
            old_password: Current password (plain text)
            new_password: New password (plain text)

        Returns:
            Tuple of (success, error_message)
            Returns (True, None) on success
            Returns (False, error_message) on failure
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return False, "User not found"

            # Verify old password
            if not verify_password(old_password, user.password_hash):
                logger.warning(f"Password change attempt with wrong password for user: {user.email}")
                return False, "Current password is incorrect"

            # Validate new password strength
            is_valid, error_msg = PasswordValidator.validate(new_password)
            if not is_valid:
                return False, error_msg

            # Update password
            user.password_hash = hash_password(new_password)
            user.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(user)

            logger.info(f"Password changed for user: {user.email}")
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error changing password: {e}")
            return False, "Failed to change password"

    @staticmethod
    def change_email(
        db: Session,
        user_id: str,
        new_email: str,
        password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user email address (requires re-verification).

        Args:
            db: Database session
            user_id: User ID (as string UUID)
            new_email: New email address
            password: Current password for confirmation

        Returns:
            Tuple of (success, error_message)
            Returns (True, None) on success
            Returns (False, error_message) on failure
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return False, "User not found"

            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning(
                    f"Email change attempt with wrong password for user: {user.email}"
                )
                return False, "Password is incorrect"

            # Check if new email is already registered
            existing_user = db.query(User).filter(User.email == new_email.lower()).first()
            if existing_user and existing_user.id != user.id:
                return False, "Email is already registered"

            # Generate new verification token
            verification_token = secrets.token_urlsafe(32)

            # Update email and mark as unverified
            old_email = user.email
            user.email = new_email.lower()
            user.is_email_verified = False
            user.email_verification_token = verification_token
            user.updated_at = datetime.utcnow()

            try:
                db.commit()
                db.refresh(user)

                # Send verification email to new address
                email_sent = EmailService.send_verification_email(
                    email=user.email,
                    user_id=str(user.id),
                    verification_token=verification_token,
                    first_name=user.first_name,
                )

                if not email_sent:
                    logger.warning(
                        f"Verification email failed to send for email change, "
                        f"user {user.id}, old_email {old_email} -> new_email {user.email}"
                    )

                logger.info(f"Email changed for user: {old_email} -> {user.email}")
                return True, None

            except IntegrityError:
                db.rollback()
                # Restore original email on error
                user.email = old_email
                db.commit()
                return False, "Email is already registered"

        except Exception as e:
            db.rollback()
            logger.error(f"Error changing email: {e}")
            return False, "Failed to change email"
