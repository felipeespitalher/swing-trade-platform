"""
Pydantic schemas for exchange key API requests and responses.

Provides validation and serialization for exchange API key data.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class ExchangeKeyCreate(BaseModel):
    """Schema for creating a new exchange key."""

    exchange: str = Field(
        ..., min_length=1, max_length=50, description="Exchange name (e.g., 'binance')"
    )
    label: Optional[str] = Field(
        default=None, max_length=100, description="User-defined label for this connection"
    )
    api_key: str = Field(
        ..., min_length=1, description="Exchange API key (will be encrypted)"
    )
    api_secret: str = Field(
        ..., min_length=1, description="Exchange API secret (will be encrypted)"
    )
    is_testnet: bool = Field(
        default=True, description="Whether this is a testnet/sandbox key"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "exchange": "binance",
                "label": "My Binance Account",
                "api_key": "your_api_key_here",
                "api_secret": "your_api_secret_here",
                "is_testnet": True,
            }
        }


class ExchangeKeyUpdate(BaseModel):
    """Schema for updating an exchange key (deactivation only)."""

    is_active: bool = Field(description="Whether the key is active")


class ExchangeKeyResponse(BaseModel):
    """Schema for exchange key response (no secrets exposed)."""

    id: UUID
    exchange: str
    label: Optional[str] = None
    api_key_masked: Optional[str] = None
    is_testnet: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "exchange": "binance",
                "label": "My Binance Account",
                "api_key_masked": "****abcd",
                "is_testnet": True,
                "is_active": True,
                "created_at": "2024-04-02T10:00:00+00:00",
                "updated_at": "2024-04-02T10:00:00+00:00",
            }
        }


class ExchangeKeyDetailResponse(ExchangeKeyResponse):
    """Schema for detailed exchange key response (with decrypted credentials for API response)."""

    api_key: str = Field(description="Decrypted API key (only in response, not stored)")
    api_secret: str = Field(description="Decrypted API secret (only in response, not stored)")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "exchange": "binance",
                "label": "My Binance Account",
                "api_key": "your_api_key_here",
                "api_secret": "your_api_secret_here",
                "api_key_masked": "****abcd",
                "is_testnet": True,
                "is_active": True,
                "created_at": "2024-04-02T10:00:00+00:00",
                "updated_at": "2024-04-02T10:00:00+00:00",
            }
        }


class ExchangeKeyListResponse(BaseModel):
    """Schema for list of exchange keys response."""

    keys: list[ExchangeKeyResponse] = Field(description="List of exchange keys")
    total: int = Field(description="Total number of keys")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "keys": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "exchange": "binance",
                        "label": "My Binance Account",
                        "api_key_masked": "****abcd",
                        "is_testnet": True,
                        "is_active": True,
                        "created_at": "2024-04-02T10:00:00+00:00",
                        "updated_at": "2024-04-02T10:00:00+00:00",
                    }
                ],
                "total": 1,
            }
        }
