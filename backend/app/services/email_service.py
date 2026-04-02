"""
Email sending service.

Provides email functionality with:
- Mock implementation for development (console output)
- SMTP implementation for production
- Verification email templates
"""

import logging
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    @staticmethod
    def send_verification_email(
        email: str,
        user_id: str,
        verification_token: str,
        first_name: str,
    ) -> bool:
        """
        Send email verification email.

        Args:
            email: Recipient email address
            user_id: User ID for the verification link
            verification_token: Token for email verification
            first_name: User's first name for personalization

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            verification_url = (
                f"http://localhost:8000/api/auth/verify/{verification_token}"
            )

            subject = "Verify Your Email Address"
            html_content = EmailService._build_verification_email_html(
                first_name, verification_url
            )
            text_content = EmailService._build_verification_email_text(
                first_name, verification_url
            )

            # In development, print to console
            if settings.environment == "development" or not settings.smtp_host:
                logger.info(
                    f"[EMAIL - DEVELOPMENT MODE]\n"
                    f"To: {email}\n"
                    f"Subject: {subject}\n"
                    f"---\n"
                    f"{text_content}\n"
                    f"---\n"
                    f"Verification URL: {verification_url}\n"
                )
                return True

            # Production: Send via SMTP
            return EmailService._send_smtp(
                to_email=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            return False

    @staticmethod
    def _send_smtp(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body

        Returns:
            True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = to_email

            # Attach text and HTML parts
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send via SMTP
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.environment != "development":
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"SMTP error sending to {to_email}: {e}")
            return False

    @staticmethod
    def _build_verification_email_html(first_name: str, verification_url: str) -> str:
        """
        Build HTML email content for verification.

        Args:
            first_name: User's first name
            verification_url: URL to click for verification

        Returns:
            HTML email content
        """
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Welcome to Swing Trade Platform!</h2>

                    <p>Hi {first_name},</p>

                    <p>Thank you for creating an account. To get started, please verify your email address by clicking the button below:</p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}"
                           style="display: inline-block; padding: 12px 30px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Verify Email Address
                        </a>
                    </div>

                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                        {verification_url}
                    </p>

                    <p>This link will expire in 24 hours.</p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                    <p style="color: #666; font-size: 12px;">
                        If you didn't create this account, please ignore this email.
                    </p>

                    <p style="color: #666; font-size: 12px;">
                        Swing Trade Platform<br>
                        © 2024 All rights reserved
                    </p>
                </div>
            </body>
        </html>
        """

    @staticmethod
    def _build_verification_email_text(first_name: str, verification_url: str) -> str:
        """
        Build plain text email content for verification.

        Args:
            first_name: User's first name
            verification_url: URL to click for verification

        Returns:
            Plain text email content
        """
        return f"""
Welcome to Swing Trade Platform!

Hi {first_name},

Thank you for creating an account. To get started, please verify your email address by visiting this link:

{verification_url}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

---
Swing Trade Platform
© 2024 All rights reserved
        """
