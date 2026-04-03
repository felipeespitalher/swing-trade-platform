"""
Comprehensive tests for exchange key management API and service.

Tests covering:
- Exchange key CRUD operations
- User isolation and security
- Encryption and decryption
- API endpoints
- Error handling
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, ExchangeKey
from app.core.security import hash_password, create_access_token
from app.core.encryption import EncryptionManager
from app.services.exchange_key_service import ExchangeKeyService
from app.schemas.exchange_key import ExchangeKeyCreate


class TestExchangeKeyService:
    """Tests for ExchangeKeyService business logic."""

    @pytest.fixture
    def encryption_manager(self):
        """Create encryption manager for tests."""
        return EncryptionManager("test-master-key")

    @pytest.fixture
    def service(self, encryption_manager):
        """Create exchange key service with test encryption manager."""
        return ExchangeKeyService(encryption_manager)

    @pytest.fixture
    def user(self, db: Session):
        """Create test user."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_add_exchange_key(self, service, db: Session, user):
        """Test adding a new exchange key."""
        result = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="test-api-key-12345",
            api_secret="test-api-secret-67890",
            is_testnet=True,
        )
        assert result.id is not None
        assert result.user_id == user.id
        assert result.exchange == "binance"
        assert result.is_testnet is True
        assert result.is_active is True
        # Keys should be encrypted, not plaintext
        assert result.api_key_encrypted != "test-api-key-12345"
        assert result.api_secret_encrypted != "test-api-secret-67890"

    @pytest.mark.asyncio
    async def test_add_exchange_key_duplicate_fails(self, service, db: Session, user):
        """Test adding duplicate exchange key fails."""
        # Add first key
        await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key1",
            api_secret="secret1",
            is_testnet=True,
        )
        # Try to add same exchange/testnet combination
        with pytest.raises(ValueError, match="already exists"):
            await service.add_exchange_key(
                db=db,
                user_id=user.id,
                exchange="binance",
                api_key="key2",
                api_secret="secret2",
                is_testnet=True,
            )

    @pytest.mark.asyncio
    async def test_add_different_testnet_allowed(self, service, db: Session, user):
        """Test adding mainnet and testnet keys for same exchange is allowed."""
        # Add testnet key
        testnet_key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="testnet-key",
            api_secret="testnet-secret",
            is_testnet=True,
        )
        # Add mainnet key - should succeed
        mainnet_key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="mainnet-key",
            api_secret="mainnet-secret",
            is_testnet=False,
        )
        assert testnet_key.id != mainnet_key.id
        assert testnet_key.is_testnet is True
        assert mainnet_key.is_testnet is False

    @pytest.mark.asyncio
    async def test_get_user_exchange_keys(self, service, db: Session, user):
        """Test retrieving all keys for a user."""
        # Add multiple keys
        await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key1",
            api_secret="secret1",
        )
        await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="kraken",
            api_key="key2",
            api_secret="secret2",
        )
        # Retrieve keys
        keys = await service.get_user_exchange_keys(db=db, user_id=user.id)
        assert len(keys) == 2
        exchanges = {key.exchange for key in keys}
        assert exchanges == {"binance", "kraken"}

    @pytest.mark.asyncio
    async def test_get_user_exchange_keys_empty(self, service, db: Session, user):
        """Test retrieving keys when user has none."""
        keys = await service.get_user_exchange_keys(db=db, user_id=user.id)
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_get_user_exchange_keys_active_only(self, service, db: Session, user):
        """Test retrieving only active keys."""
        # Add active and inactive keys
        key1 = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key1",
            api_secret="secret1",
        )
        key2 = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="kraken",
            api_key="key2",
            api_secret="secret2",
        )
        # Deactivate one key
        await service.deactivate_exchange_key(db=db, user_id=user.id, key_id=key2.id)
        # Get only active keys
        active_keys = await service.get_user_exchange_keys(
            db=db, user_id=user.id, active_only=True
        )
        assert len(active_keys) == 1
        assert active_keys[0].exchange == "binance"

    @pytest.mark.asyncio
    async def test_get_exchange_key(self, service, db: Session, user):
        """Test retrieving specific key."""
        key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key1",
            api_secret="secret1",
        )
        retrieved = await service.get_exchange_key(db=db, user_id=user.id, key_id=key.id)
        assert retrieved.id == key.id
        assert retrieved.exchange == "binance"

    @pytest.mark.asyncio
    async def test_get_exchange_key_not_found(self, service, db: Session, user):
        """Test retrieving non-existent key returns None."""
        result = await service.get_exchange_key(
            db=db, user_id=user.id, key_id=uuid4()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_decrypt_exchange_key(self, service, db: Session, user):
        """Test decrypting exchange key credentials."""
        api_key = "binance-api-key-12345"
        api_secret = "binance-secret-67890"
        key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key=api_key,
            api_secret=api_secret,
        )
        decrypted = await service.decrypt_exchange_key(key, user.id)
        assert decrypted["api_key"] == api_key
        assert decrypted["api_secret"] == api_secret

    @pytest.mark.asyncio
    async def test_decrypt_with_wrong_user_fails(self, service, db: Session, user):
        """Test decryption fails with wrong user ID."""
        key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key",
            api_secret="secret",
        )
        other_user_id = uuid4()
        with pytest.raises(ValueError, match="Cannot decrypt key not owned"):
            await service.decrypt_exchange_key(key, other_user_id)

    @pytest.mark.asyncio
    async def test_delete_exchange_key(self, service, db: Session, user):
        """Test deleting an exchange key."""
        key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key",
            api_secret="secret",
        )
        success = await service.delete_exchange_key(db=db, user_id=user.id, key_id=key.id)
        assert success is True
        # Verify it's deleted
        remaining = await service.get_exchange_key(db=db, user_id=user.id, key_id=key.id)
        assert remaining is None

    @pytest.mark.asyncio
    async def test_delete_non_existent_key(self, service, db: Session, user):
        """Test deleting non-existent key returns False."""
        success = await service.delete_exchange_key(
            db=db, user_id=user.id, key_id=uuid4()
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_deactivate_exchange_key(self, service, db: Session, user):
        """Test deactivating an exchange key."""
        key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key",
            api_secret="secret",
        )
        assert key.is_active is True
        deactivated = await service.deactivate_exchange_key(
            db=db, user_id=user.id, key_id=key.id
        )
        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_activate_exchange_key(self, service, db: Session, user):
        """Test reactivating an exchange key."""
        key = await service.add_exchange_key(
            db=db,
            user_id=user.id,
            exchange="binance",
            api_key="key",
            api_secret="secret",
        )
        # Deactivate then reactivate
        await service.deactivate_exchange_key(db=db, user_id=user.id, key_id=key.id)
        activated = await service.activate_exchange_key(
            db=db, user_id=user.id, key_id=key.id
        )
        assert activated.is_active is True


class TestExchangeKeyAPI:
    """Tests for Exchange Key API endpoints."""

    @pytest.fixture
    def verified_user_with_token(self, db: Session):
        """Create a verified user with JWT token."""
        user = User(
            id=uuid4(),
            email="api@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(str(user.id), user.email)
        return user, token

    def test_post_exchange_key_success(self, client: TestClient, verified_user_with_token):
        """Test adding exchange key via API."""
        user, token = verified_user_with_token
        response = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "test-api-key",
                "api_secret": "test-api-secret",
                "is_testnet": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["exchange"] == "binance"
        assert data["api_key"] == "test-api-key"
        assert data["api_secret"] == "test-api-secret"
        assert data["is_testnet"] is True
        assert data["is_active"] is True

    def test_post_exchange_key_no_auth(self, client: TestClient):
        """Test adding exchange key without authentication fails."""
        response = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "test-api-key",
                "api_secret": "test-api-secret",
                "is_testnet": True,
            },
        )
        assert response.status_code == 403

    def test_post_exchange_key_duplicate(self, client: TestClient, verified_user_with_token, db: Session):
        """Test adding duplicate exchange key fails."""
        user, token = verified_user_with_token
        # Add first key
        response1 = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key1",
                "api_secret": "secret1",
                "is_testnet": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 201
        # Try to add duplicate
        response2 = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key2",
                "api_secret": "secret2",
                "is_testnet": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 409

    def test_get_exchange_keys_list(self, client: TestClient, verified_user_with_token):
        """Test listing exchange keys."""
        user, token = verified_user_with_token
        # Add some keys
        for i in range(3):
            client.post(
                "/api/exchange-keys",
                json={
                    "exchange": f"exchange{i}",
                    "api_key": f"key{i}",
                    "api_secret": f"secret{i}",
                    "is_testnet": i % 2 == 0,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        # List keys
        response = client.get(
            "/api/exchange-keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["keys"]) == 3
        # List should not contain api_key and api_secret for security
        for key in data["keys"]:
            assert "api_key" not in key
            assert "api_secret" not in key

    def test_get_exchange_keys_empty(self, client: TestClient, verified_user_with_token):
        """Test listing keys when user has none."""
        user, token = verified_user_with_token
        response = client.get(
            "/api/exchange-keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["keys"] == []

    def test_get_exchange_keys_active_only(self, client: TestClient, verified_user_with_token):
        """Test filtering for active keys only."""
        user, token = verified_user_with_token
        # Add active key
        response1 = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key1",
                "api_secret": "secret1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id_1 = response1.json()["id"]
        # Add inactive key
        response2 = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "kraken",
                "api_key": "key2",
                "api_secret": "secret2",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id_2 = response2.json()["id"]
        # Deactivate second key
        client.patch(
            f"/api/exchange-keys/{key_id_2}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Get only active
        response = client.get(
            "/api/exchange-keys?active_only=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert data["total"] == 1
        assert data["keys"][0]["exchange"] == "binance"

    def test_get_exchange_key_detail(self, client: TestClient, verified_user_with_token):
        """Test retrieving specific key with decrypted credentials."""
        user, token = verified_user_with_token
        # Add key
        post_response = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "secret-key-12345",
                "api_secret": "secret-secret-67890",
                "is_testnet": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = post_response.json()["id"]
        # Get specific key
        response = client.get(
            f"/api/exchange-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["api_key"] == "secret-key-12345"
        assert data["api_secret"] == "secret-secret-67890"

    def test_get_exchange_key_not_found(self, client: TestClient, verified_user_with_token):
        """Test retrieving non-existent key."""
        user, token = verified_user_with_token
        response = client.get(
            f"/api/exchange-keys/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_delete_exchange_key(self, client: TestClient, verified_user_with_token):
        """Test deleting an exchange key."""
        user, token = verified_user_with_token
        # Add key
        post_response = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key",
                "api_secret": "secret",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = post_response.json()["id"]
        # Delete key
        response = client.delete(
            f"/api/exchange-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204
        # Verify it's deleted
        get_response = client.get(
            f"/api/exchange-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    def test_deactivate_exchange_key(self, client: TestClient, verified_user_with_token):
        """Test deactivating an exchange key."""
        user, token = verified_user_with_token
        # Add key
        post_response = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key",
                "api_secret": "secret",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = post_response.json()["id"]
        # Deactivate
        response = client.patch(
            f"/api/exchange-keys/{key_id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_activate_exchange_key(self, client: TestClient, verified_user_with_token):
        """Test reactivating an exchange key."""
        user, token = verified_user_with_token
        # Add key
        post_response = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key",
                "api_secret": "secret",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = post_response.json()["id"]
        # Deactivate
        client.patch(
            f"/api/exchange-keys/{key_id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Activate
        response = client.patch(
            f"/api/exchange-keys/{key_id}/activate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True


class TestUserIsolation:
    """Tests for user isolation and security."""

    @pytest.fixture
    def two_users_with_tokens(self, db: Session):
        """Create two users with tokens."""
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        user2 = User(
            id=uuid4(),
            email="user2@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(user1)
        db.add(user2)
        db.commit()
        db.refresh(user1)
        db.refresh(user2)
        token1 = create_access_token(str(user1.id), user1.email)
        token2 = create_access_token(str(user2.id), user2.email)
        return (user1, token1), (user2, token2)

    def test_user_cannot_see_other_users_keys(self, client: TestClient, two_users_with_tokens):
        """Test that user A cannot see user B's keys."""
        (user1, token1), (user2, token2) = two_users_with_tokens
        # User 1 adds key
        response1 = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key1",
                "api_secret": "secret1",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )
        key_id = response1.json()["id"]
        # User 2 tries to get user 1's key
        response2 = client.get(
            f"/api/exchange-keys/{key_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response2.status_code == 404

    def test_user_cannot_delete_other_users_keys(self, client: TestClient, two_users_with_tokens):
        """Test that user A cannot delete user B's keys."""
        (user1, token1), (user2, token2) = two_users_with_tokens
        # User 1 adds key
        response1 = client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "key1",
                "api_secret": "secret1",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )
        key_id = response1.json()["id"]
        # User 2 tries to delete user 1's key
        response2 = client.delete(
            f"/api/exchange-keys/{key_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response2.status_code == 404
        # Verify key still exists for user 1
        response3 = client.get(
            f"/api/exchange-keys/{key_id}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert response3.status_code == 200

    def test_keys_are_encrypted_in_database(self, client: TestClient, verified_user_with_token, db: Session):
        """Test that keys are encrypted in database (not readable)."""
        user, token = verified_user_with_token
        # Add key via API
        client.post(
            "/api/exchange-keys",
            json={
                "exchange": "binance",
                "api_key": "my-secret-api-key",
                "api_secret": "my-secret-secret",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # Query database directly
        key_record = db.query(ExchangeKey).filter(ExchangeKey.user_id == user.id).first()
        assert key_record is not None
        # Encrypted fields should NOT contain plaintext
        assert "my-secret-api-key" not in key_record.api_key_encrypted
        assert "my-secret-secret" not in key_record.api_secret_encrypted
        # But should be able to decrypt
        assert len(key_record.api_key_encrypted) > 10  # Should be long base64 string

    @pytest.fixture
    def verified_user_with_token(self, db: Session):
        """Create a verified user with JWT token."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(str(user.id), user.email)
        return user, token
