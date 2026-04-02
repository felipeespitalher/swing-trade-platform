"""
Pydantic schemas for authentication and user data.

Defines request/response schemas for registration, login, and token management.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserRegister(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        }


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
            }
        }


class Token(BaseModel):
    """Schema for token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="JWT refresh token")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


class UserResponse(BaseModel):
    """Schema for user response (no password exposed)."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    timezone: str = Field(..., description="User timezone")
    risk_limit_pct: float = Field(..., description="Risk limit percentage")
    is_email_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "timezone": "UTC",
                "risk_limit_pct": 2.0,
                "is_email_verified": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class VerificationResponse(BaseModel):
    """Schema for email verification response."""

    message: str = Field(..., description="Status message")
    user_id: Optional[UUID] = Field(None, description="User ID if successful")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message": "Email verified successfully",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class RegistrationResponse(BaseModel):
    """Schema for registration response."""

    message: str = Field(..., description="Status message")
    user_id: UUID = Field(..., description="Created user ID")
    email: str = Field(..., description="User email")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message": "User registered successfully. Please check your email to verify your account.",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
            }
        }
