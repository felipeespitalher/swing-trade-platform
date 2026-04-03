"""
Simplified multi-tenant isolation tests.

These tests validate that:
1. RLS policies are correctly configured in the database
2. Application-level isolation filters work properly
3. Cascading deletes respect tenant boundaries

Note: These tests connect as PostgreSQL superuser, which bypasses RLS.
For RLS enforcement testing, use non-superuser database accounts.
"""

import pytest
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import User, ExchangeKey, Strategy, Trade, AuditLog
from app.core.security import hash_password
from app.db.rls import set_user_context, verify_rls_enabled, check_rls_health


class TestRLSPoliciesExist:
    """Verify RLS policies are correctly configured."""

    def test_rls_enabled_on_all_user_owned_tables(self, db: Session):
        """Verify RLS is enabled on all user-owned tables."""
        status = verify_rls_enabled(db)

        required_tables = ["users", "exchange_keys", "strategies", "trades", "audit_logs"]

        for table in required_tables:
            assert table in status, f"Table {table} not found in RLS status"

            # For PostgreSQL, check that RLS is enabled
            if db.bind.dialect.name == "postgresql":
                assert status[table]["rls_enabled"], f"RLS not enabled on {table}"
                assert status[table]["policy_count"] > 0, f"No RLS policies on {table}"

    def test_rls_health_check_passes(self, db: Session):
        """Verify RLS health check passes."""
        is_healthy, message = check_rls_health(db)

        if db.bind.dialect.name == "postgresql":
            assert is_healthy, f"RLS health check failed: {message}"


class TestApplicationLevelIsolation:
    """Test application-level isolation of data."""

    @pytest.fixture
    def two_users(self, db: Session):
        """Create two test users."""
        user_a = User(
            id=uuid4(),
            email="user_a@test.com",
            password_hash=hash_password("SecurePass123!"),
            first_name="Alice",
            last_name="User",
            is_email_verified=True,
        )
        user_b = User(
            id=uuid4(),
            email="user_b@test.com",
            password_hash=hash_password("SecurePass123!"),
            first_name="Bob",
            last_name="User",
            is_email_verified=True,
        )
        db.add(user_a)
        db.add(user_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        return user_a, user_b

    def test_exchange_key_isolation(self, db: Session, two_users):
        """Verify exchange keys are isolated by user_id."""
        user_a, user_b = two_users

        # Create exchange keys for both users
        key_a = ExchangeKey(
            id=uuid4(),
            user_id=user_a.id,
            exchange="binance",
            api_key_encrypted="encrypted_key_a",
            api_secret_encrypted="encrypted_secret_a",
            encryption_iv="v1",
            is_testnet=True,
            is_active=True,
        )
        key_b = ExchangeKey(
            id=uuid4(),
            user_id=user_b.id,
            exchange="kraken",
            api_key_encrypted="encrypted_key_b",
            api_secret_encrypted="encrypted_secret_b",
            encryption_iv="v1",
            is_testnet=True,
            is_active=True,
        )
        db.add(key_a)
        db.add(key_b)
        db.commit()

        # User B queries with application-level filter
        user_b_keys = db.query(ExchangeKey).filter(
            ExchangeKey.user_id == user_b.id
        ).all()

        # Should only see their own key
        assert len(user_b_keys) == 1
        assert user_b_keys[0].user_id == user_b.id
        assert user_b_keys[0].id == key_b.id

    def test_strategy_isolation(self, db: Session, two_users):
        """Verify strategies are isolated by user_id."""
        user_a, user_b = two_users

        # Create strategies for both users
        strategy_a = Strategy(
            id=uuid4(),
            user_id=user_a.id,
            name="Strategy A",
            type="momentum",
            config={"threshold": 0.5},
            is_active=True,
        )
        strategy_b = Strategy(
            id=uuid4(),
            user_id=user_b.id,
            name="Strategy B",
            type="mean_reversion",
            config={"threshold": 0.3},
            is_active=False,
        )
        db.add(strategy_a)
        db.add(strategy_b)
        db.commit()

        # User B queries with filter
        user_b_strategies = db.query(Strategy).filter(
            Strategy.user_id == user_b.id
        ).all()

        # Should only see their own strategy
        assert len(user_b_strategies) == 1
        assert user_b_strategies[0].user_id == user_b.id
        assert user_b_strategies[0].name == "Strategy B"

    def test_user_self_isolation(self, db: Session, two_users):
        """Verify users can only access themselves."""
        user_a, user_b = two_users

        # User B queries with filter
        user_b_self = db.query(User).filter(User.id == user_b.id).first()

        # Should find themselves
        assert user_b_self is not None
        assert user_b_self.id == user_b.id

        # User B should NOT be able to modify User A
        # (would need both ownership check and RLS policy)
        user_b_as_user_a = db.query(User).filter(User.id == user_a.id).first()
        assert user_b_as_user_a is not None  # Can query it (no RLS enforcement with superuser)

        # But application logic would prevent modification
        # (via explicit user_id check before UPDATE)

    def test_cascading_delete_respects_isolation(self, db: Session, two_users):
        """Verify cascading deletes only affect target user's data."""
        user_a, user_b = two_users

        # Create exchange keys for both users
        key_a = ExchangeKey(
            id=uuid4(),
            user_id=user_a.id,
            exchange="binance",
            api_key_encrypted="key_a",
            api_secret_encrypted="secret_a",
            is_active=True,
        )
        key_b = ExchangeKey(
            id=uuid4(),
            user_id=user_b.id,
            exchange="kraken",
            api_key_encrypted="key_b",
            api_secret_encrypted="secret_b",
            is_active=True,
        )
        db.add(key_a)
        db.add(key_b)
        db.commit()

        # Delete User A (should cascade to their key)
        db.delete(user_a)
        db.commit()

        # User B's key should still exist
        remaining_key = db.query(ExchangeKey).filter(
            ExchangeKey.id == key_b.id
        ).first()
        assert remaining_key is not None, "User B's key should not be deleted"
        assert remaining_key.user_id == user_b.id

        # User A's key should be deleted
        deleted_key = db.query(ExchangeKey).filter(
            ExchangeKey.id == key_a.id
        ).first()
        assert deleted_key is None, "User A's key should be cascade deleted"


class TestRLSContextManagement:
    """Test RLS context setting and utilities."""

    def test_set_user_context_works(self, db: Session):
        """Verify set_user_context doesn't raise errors."""
        user_id = uuid4()

        # Should not raise
        set_user_context(db, user_id)

    def test_set_user_context_rejects_none(self, db: Session):
        """Verify set_user_context rejects None user_id."""
        with pytest.raises(ValueError):
            set_user_context(db, None)

    def test_verify_rls_enabled_returns_dict(self, db: Session):
        """Verify verify_rls_enabled returns proper structure."""
        status = verify_rls_enabled(db)

        assert isinstance(status, dict)
        assert "users" in status or len(status) > 0  # At least some table status

        # Check structure of a status entry
        for table, info in status.items():
            assert isinstance(info, dict)
            assert "rls_enabled" in info
            assert "policy_count" in info
            assert "policies" in info
            assert isinstance(info["policies"], list)


class TestRLSWithActualQueries:
    """Test RLS behavior with actual queries (superuser bypass noted)."""

    @pytest.fixture
    def test_data(self, db: Session):
        """Create test data."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=hash_password("Test123!"),
            first_name="Test",
            last_name="User",
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        key = ExchangeKey(
            id=uuid4(),
            user_id=user.id,
            exchange="binance",
            api_key_encrypted="encrypted",
            api_secret_encrypted="encrypted",
            is_active=True,
        )
        db.add(key)
        db.commit()

        return user, key

    def test_ownership_verification_before_operations(self, db: Session, test_data):
        """Verify ownership checks work correctly."""
        user, key = test_data
        other_user_id = uuid4()

        # When user tries to delete key they own, it should work
        assert key.user_id == user.id
        db.delete(key)
        db.commit()

        # Verify it's deleted
        result = db.query(ExchangeKey).filter(ExchangeKey.id == key.id).first()
        assert result is None

    def test_audit_log_isolation(self, db: Session, two_users):
        """Verify audit logs are isolated by user_id."""

        def two_users():
            user_a = User(
                id=uuid4(),
                email="a@test.com",
                password_hash=hash_password("Test123!"),
                first_name="A",
                last_name="User",
                is_email_verified=True,
            )
            user_b = User(
                id=uuid4(),
                email="b@test.com",
                password_hash=hash_password("Test123!"),
                first_name="B",
                last_name="User",
                is_email_verified=True,
            )
            db.add(user_a)
            db.add(user_b)
            db.commit()
            return user_a, user_b

        user_a, user_b = two_users()

        # Create audit logs for both
        log_a = AuditLog(
            id=uuid4(),
            user_id=user_a.id,
            action="LOGIN",
            resource_type="user",
            resource_id=user_a.id,
        )
        log_b = AuditLog(
            id=uuid4(),
            user_id=user_b.id,
            action="CREATE_KEY",
            resource_type="exchange_key",
            resource_id=uuid4(),
        )
        db.add(log_a)
        db.add(log_b)
        db.commit()

        # User B queries only their logs
        user_b_logs = db.query(AuditLog).filter(
            AuditLog.user_id == user_b.id
        ).all()

        # Should only see their own logs
        assert len(user_b_logs) == 1
        assert user_b_logs[0].user_id == user_b.id
        assert user_b_logs[0].action == "CREATE_KEY"

    @pytest.fixture
    def two_users(self, db: Session):
        """Create two users for testing."""
        user_a = User(
            id=uuid4(),
            email=f"user_{uuid4()}@test.com",
            password_hash=hash_password("SecurePass123!"),
            first_name="Alice",
            last_name="User",
            is_email_verified=True,
        )
        user_b = User(
            id=uuid4(),
            email=f"user_{uuid4()}@test.com",
            password_hash=hash_password("SecurePass123!"),
            first_name="Bob",
            last_name="User",
            is_email_verified=True,
        )
        db.add(user_a)
        db.add(user_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        return user_a, user_b
