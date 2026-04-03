"""
Exchange key API endpoints for managing encrypted API credentials.

Provides REST endpoints for adding, listing, retrieving, and deleting exchange API keys.
All endpoints require JWT authentication and are user-scoped.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.exchange_key import ExchangeKey
from app.schemas.exchange_key import (
    ExchangeKeyCreate,
    ExchangeKeyResponse,
    ExchangeKeyDetailResponse,
    ExchangeKeyListResponse,
)
from app.services.exchange_key_service import ExchangeKeyService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchange-keys", tags=["exchange-keys"])

# Initialize service
exchange_key_service = ExchangeKeyService()


@router.post(
    "",
    response_model=ExchangeKeyDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new exchange API key",
)
async def add_exchange_key(
    exchange_key_data: ExchangeKeyCreate,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExchangeKeyDetailResponse:
    """
    Add a new exchange API key (encrypted).

    The API key and secret are encrypted using AES-256-GCM before storage.
    Only one key per exchange/testnet combination is allowed per user.

    Request body:
    - exchange: Exchange name (e.g., 'binance')
    - api_key: Exchange API key (will be encrypted)
    - api_secret: Exchange API secret (will be encrypted)
    - is_testnet: Whether this is a testnet key (default: true)

    Returns:
    - id: UUID of the stored key
    - exchange: Exchange name
    - api_key: Decrypted API key (for immediate user confirmation)
    - api_secret: Decrypted API secret (for immediate user confirmation)
    - is_testnet: Testnet status
    - is_active: Key active status
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """
    try:
        # Add the key (encrypted)
        created_key = await exchange_key_service.add_exchange_key(
            db=db,
            user_id=user_id,
            exchange=exchange_key_data.exchange,
            api_key=exchange_key_data.api_key,
            api_secret=exchange_key_data.api_secret,
            is_testnet=exchange_key_data.is_testnet,
        )

        # Decrypt for response (user gets confirmation)
        decrypted = await exchange_key_service.decrypt_exchange_key(created_key, user_id)

        return ExchangeKeyDetailResponse(
            id=created_key.id,
            exchange=created_key.exchange,
            api_key=decrypted["api_key"],
            api_secret=decrypted["api_secret"],
            is_testnet=created_key.is_testnet,
            is_active=created_key.is_active,
            created_at=created_key.created_at,
            updated_at=created_key.updated_at,
        )

    except ValueError as e:
        logger.warning(f"Validation error adding exchange key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error adding exchange key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add exchange key",
        ) from e


@router.get(
    "",
    response_model=ExchangeKeyListResponse,
    summary="List user's exchange keys",
)
async def list_exchange_keys(
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = Query(False, description="Only return active keys"),
) -> ExchangeKeyListResponse:
    """
    List all exchange keys for the current user.

    Only returns non-sensitive fields (id, exchange, testnet status, active status, timestamps).
    API keys and secrets are NOT included in this list response for security.

    Query parameters:
    - active_only: If true, only return active keys (default: false)

    Returns:
    - keys: List of exchange key summaries
    - total: Total number of keys
    """
    try:
        keys = await exchange_key_service.get_user_exchange_keys(
            db=db, user_id=user_id, active_only=active_only
        )

        return ExchangeKeyListResponse(
            keys=[
                ExchangeKeyResponse(
                    id=key.id,
                    exchange=key.exchange,
                    is_testnet=key.is_testnet,
                    is_active=key.is_active,
                    created_at=key.created_at,
                    updated_at=key.updated_at,
                )
                for key in keys
            ],
            total=len(keys),
        )

    except Exception as e:
        logger.error(f"Error listing exchange keys: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve exchange keys",
        ) from e


@router.get(
    "/{key_id}",
    response_model=ExchangeKeyDetailResponse,
    summary="Get a specific exchange key with decrypted credentials",
)
async def get_exchange_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExchangeKeyDetailResponse:
    """
    Get a specific exchange key with decrypted credentials.

    WARNING: This endpoint returns the plaintext API key and secret.
    Only call when you actually need the credentials.

    Path parameters:
    - key_id: UUID of the exchange key to retrieve

    Returns:
    - id: UUID of the key
    - exchange: Exchange name
    - api_key: Decrypted API key
    - api_secret: Decrypted API secret
    - is_testnet: Testnet status
    - is_active: Key active status
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """
    try:
        exchange_key = await exchange_key_service.get_exchange_key(
            db=db, user_id=user_id, key_id=key_id
        )

        if not exchange_key:
            logger.warning(f"Attempt to access non-existent key: key_id={key_id}, user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exchange key not found"
            )

        # Decrypt credentials for response
        decrypted = await exchange_key_service.decrypt_exchange_key(exchange_key, user_id)

        return ExchangeKeyDetailResponse(
            id=exchange_key.id,
            exchange=exchange_key.exchange,
            api_key=decrypted["api_key"],
            api_secret=decrypted["api_secret"],
            is_testnet=exchange_key.is_testnet,
            is_active=exchange_key.is_active,
            created_at=exchange_key.created_at,
            updated_at=exchange_key.updated_at,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error retrieving exchange key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve exchange key",
        ) from e


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/revoke an exchange key",
)
async def delete_exchange_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete (revoke) an exchange API key.

    The key is permanently deleted from the database.
    This action cannot be undone.

    Path parameters:
    - key_id: UUID of the exchange key to delete
    """
    try:
        success = await exchange_key_service.delete_exchange_key(
            db=db, user_id=user_id, key_id=key_id
        )

        if not success:
            logger.warning(f"Attempt to delete non-existent key: key_id={key_id}, user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exchange key not found"
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deleting exchange key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete exchange key",
        ) from e


@router.patch(
    "/{key_id}/deactivate",
    response_model=ExchangeKeyResponse,
    summary="Deactivate an exchange key",
)
async def deactivate_exchange_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExchangeKeyResponse:
    """
    Deactivate an exchange key without deleting it.

    Useful for temporarily disabling a key. Can be reactivated later.

    Path parameters:
    - key_id: UUID of the exchange key to deactivate
    """
    try:
        exchange_key = await exchange_key_service.deactivate_exchange_key(
            db=db, user_id=user_id, key_id=key_id
        )

        if not exchange_key:
            logger.warning(f"Attempt to deactivate non-existent key: key_id={key_id}, user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exchange key not found"
            )

        return ExchangeKeyResponse(
            id=exchange_key.id,
            exchange=exchange_key.exchange,
            is_testnet=exchange_key.is_testnet,
            is_active=exchange_key.is_active,
            created_at=exchange_key.created_at,
            updated_at=exchange_key.updated_at,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deactivating exchange key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate exchange key",
        ) from e


@router.patch(
    "/{key_id}/activate",
    response_model=ExchangeKeyResponse,
    summary="Activate an exchange key",
)
async def activate_exchange_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExchangeKeyResponse:
    """
    Reactivate a deactivated exchange key.

    Path parameters:
    - key_id: UUID of the exchange key to activate
    """
    try:
        exchange_key = await exchange_key_service.activate_exchange_key(
            db=db, user_id=user_id, key_id=key_id
        )

        if not exchange_key:
            logger.warning(f"Attempt to activate non-existent key: key_id={key_id}, user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exchange key not found"
            )

        return ExchangeKeyResponse(
            id=exchange_key.id,
            exchange=exchange_key.exchange,
            is_testnet=exchange_key.is_testnet,
            is_active=exchange_key.is_active,
            created_at=exchange_key.created_at,
            updated_at=exchange_key.updated_at,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error activating exchange key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate exchange key",
        ) from e
