"""
Exchange key service for managing encrypted API credentials.

Handles encryption, storage, retrieval, and deletion of exchange API keys
with user isolation and security validation.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.exchange_key import ExchangeKey
from app.core.encryption import EncryptionManager
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExchangeKeyService:
    """Service for managing encrypted exchange API keys."""

    def __init__(self, encryption_manager: Optional[EncryptionManager] = None):
        """
        Initialize the exchange key service.

        Args:
            encryption_manager: Optional EncryptionManager instance
                               If not provided, creates one from settings
        """
        if encryption_manager:
            self.encryption = encryption_manager
        else:
            # Get master key from environment/config
            master_key = getattr(settings, "encryption_master_key", None)
            if not master_key:
                raise ValueError(
                    "ENCRYPTION_MASTER_KEY must be set in environment or config"
                )
            self.encryption = EncryptionManager(master_key)

    async def add_exchange_key(
        self,
        db: Session,
        user_id: UUID,
        exchange: str,
        api_key: str,
        api_secret: str,
        is_testnet: bool = True,
    ) -> ExchangeKey:
        """
        Add a new exchange API key (encrypted).

        Encrypts the API key and secret using AES-256-GCM with the user_id as AAD.
        The user_id as AAD prevents ciphertext swapping between users.

        Args:
            db: Database session
            user_id: UUID of the user
            exchange: Exchange name (e.g., 'binance')
            api_key: Plain API key
            api_secret: Plain API secret
            is_testnet: Whether this is a testnet key (default: True)

        Returns:
            Created ExchangeKey model

        Raises:
            ValueError: If exchange/user_id/is_testnet combination already exists
        """
        # Check for existing key with same combination
        existing = (
            db.query(ExchangeKey)
            .filter(
                ExchangeKey.user_id == user_id,
                ExchangeKey.exchange == exchange,
                ExchangeKey.is_testnet == is_testnet,
            )
            .first()
        )

        if existing:
            logger.warning(
                f"Attempt to create duplicate exchange key: user_id={user_id}, "
                f"exchange={exchange}, is_testnet={is_testnet}"
            )
            raise ValueError(
                f"Exchange key for {exchange} (testnet={is_testnet}) already exists for this user"
            )

        # Encrypt api_key and api_secret using user_id as AAD
        aad = str(user_id)
        encrypted_key = self.encryption.encrypt(api_key, aad=aad)
        encrypted_secret = self.encryption.encrypt(api_secret, aad=aad)

        # Create and store the exchange key
        exchange_key = ExchangeKey(
            user_id=user_id,
            exchange=exchange.lower(),
            api_key_encrypted=encrypted_key,
            api_secret_encrypted=encrypted_secret,
            is_testnet=is_testnet,
            is_active=True,
        )

        db.add(exchange_key)
        db.commit()
        db.refresh(exchange_key)

        logger.info(
            f"Added exchange key: user_id={user_id}, exchange={exchange}, is_testnet={is_testnet}"
        )

        return exchange_key

    async def get_user_exchange_keys(
        self, db: Session, user_id: UUID, active_only: bool = False
    ) -> list[ExchangeKey]:
        """
        Get all exchange keys for a user (decrypted).

        Queries only the user's own keys and decrypts them on retrieval.
        This ensures user isolation - a user can only see their own keys.

        Args:
            db: Database session
            user_id: UUID of the user
            active_only: If True, only return active keys

        Returns:
            List of ExchangeKey models with decrypted values
        """
        query = db.query(ExchangeKey).filter(ExchangeKey.user_id == user_id)

        if active_only:
            query = query.filter(ExchangeKey.is_active == True)

        keys = query.order_by(ExchangeKey.created_at.desc()).all()

        logger.info(
            f"Retrieved {len(keys)} exchange keys for user_id={user_id} (active_only={active_only})"
        )

        return keys

    async def get_exchange_key(
        self, db: Session, user_id: UUID, key_id: UUID
    ) -> Optional[ExchangeKey]:
        """
        Get a specific exchange key for a user.

        Ensures the key belongs to the requesting user (ownership verification).

        Args:
            db: Database session
            user_id: UUID of the user making the request
            key_id: UUID of the exchange key to retrieve

        Returns:
            ExchangeKey if found and owned by user, None otherwise
        """
        exchange_key = (
            db.query(ExchangeKey)
            .filter(ExchangeKey.id == key_id, ExchangeKey.user_id == user_id)
            .first()
        )

        if exchange_key:
            logger.info(f"Retrieved exchange key: key_id={key_id}, user_id={user_id}")
        else:
            logger.warning(
                f"Attempt to access non-existent or unauthorized key: key_id={key_id}, user_id={user_id}"
            )

        return exchange_key

    async def decrypt_exchange_key(
        self, exchange_key: ExchangeKey, user_id: UUID
    ) -> dict[str, str]:
        """
        Decrypt an exchange key's credentials.

        Args:
            exchange_key: The ExchangeKey model to decrypt
            user_id: UUID of the user (must match exchange_key.user_id)

        Returns:
            Dictionary with decrypted 'api_key' and 'api_secret'

        Raises:
            ValueError: If user_id doesn't match the key's owner
        """
        if exchange_key.user_id != user_id:
            logger.error(
                f"Unauthorized decryption attempt: key_id={exchange_key.id}, "
                f"owner_id={exchange_key.user_id}, requester_id={user_id}"
            )
            raise ValueError("Cannot decrypt key not owned by this user")

        aad = str(user_id)
        try:
            api_key = self.encryption.decrypt(exchange_key.api_key_encrypted, aad=aad)
            api_secret = self.encryption.decrypt(
                exchange_key.api_secret_encrypted, aad=aad
            )
            return {"api_key": api_key, "api_secret": api_secret}
        except Exception as e:
            logger.error(f"Failed to decrypt exchange key: {str(e)}")
            raise ValueError(f"Failed to decrypt exchange key: {str(e)}")

    async def delete_exchange_key(
        self, db: Session, user_id: UUID, key_id: UUID
    ) -> bool:
        """
        Delete an exchange key (revoke).

        Only allows deletion of keys owned by the user.

        Args:
            db: Database session
            user_id: UUID of the user making the request
            key_id: UUID of the exchange key to delete

        Returns:
            True if deletion was successful, False if key not found

        Raises:
            ValueError: If key is not owned by the user
        """
        exchange_key = (
            db.query(ExchangeKey)
            .filter(ExchangeKey.id == key_id, ExchangeKey.user_id == user_id)
            .first()
        )

        if not exchange_key:
            logger.warning(
                f"Attempt to delete non-existent or unauthorized key: key_id={key_id}, user_id={user_id}"
            )
            return False

        db.delete(exchange_key)
        db.commit()

        logger.info(f"Deleted exchange key: key_id={key_id}, user_id={user_id}")

        return True

    async def deactivate_exchange_key(
        self, db: Session, user_id: UUID, key_id: UUID
    ) -> Optional[ExchangeKey]:
        """
        Deactivate an exchange key without deleting it.

        Useful for temporarily disabling a key.

        Args:
            db: Database session
            user_id: UUID of the user making the request
            key_id: UUID of the exchange key to deactivate

        Returns:
            Updated ExchangeKey if successful, None if not found
        """
        exchange_key = (
            db.query(ExchangeKey)
            .filter(ExchangeKey.id == key_id, ExchangeKey.user_id == user_id)
            .first()
        )

        if not exchange_key:
            logger.warning(
                f"Attempt to deactivate non-existent or unauthorized key: key_id={key_id}, user_id={user_id}"
            )
            return None

        exchange_key.is_active = False
        db.commit()
        db.refresh(exchange_key)

        logger.info(f"Deactivated exchange key: key_id={key_id}, user_id={user_id}")

        return exchange_key

    async def activate_exchange_key(
        self, db: Session, user_id: UUID, key_id: UUID
    ) -> Optional[ExchangeKey]:
        """
        Reactivate an exchange key.

        Args:
            db: Database session
            user_id: UUID of the user making the request
            key_id: UUID of the exchange key to activate

        Returns:
            Updated ExchangeKey if successful, None if not found
        """
        exchange_key = (
            db.query(ExchangeKey)
            .filter(ExchangeKey.id == key_id, ExchangeKey.user_id == user_id)
            .first()
        )

        if not exchange_key:
            logger.warning(
                f"Attempt to activate non-existent or unauthorized key: key_id={key_id}, user_id={user_id}"
            )
            return None

        exchange_key.is_active = True
        db.commit()
        db.refresh(exchange_key)

        logger.info(f"Activated exchange key: key_id={key_id}, user_id={user_id}")

        return exchange_key
