"""
Application configuration settings.

Handles environment-based configuration for the Swing Trade Platform API.
"""

from pydantic_settings import BaseSettings
from datetime import timedelta


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application info
    app_name: str = "Swing Trade Automation Platform API"
    app_version: str = "0.2.0"
    debug: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" for production, "text" for development

    # Database
    database_url: str = "postgresql://postgres:postgres_password@localhost:5432/swing_trade"

    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Encryption Configuration
    encryption_master_key: str = "your-encryption-master-key-change-in-production"

    # Email — Resend (https://resend.com)
    resend_api_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    resend_from_name: str = "Swing Trade Platform"

    # Email — SMTP fallback (optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@swingtrade.local"
    smtp_from_name: str = "Swing Trade Platform"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # Development
    environment: str = "development"

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def access_token_expire(self) -> timedelta:
        """Get access token expiration as timedelta."""
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def refresh_token_expire(self) -> timedelta:
        """Get refresh token expiration as timedelta."""
        return timedelta(days=self.refresh_token_expire_days)


# Global settings instance
settings = Settings()
