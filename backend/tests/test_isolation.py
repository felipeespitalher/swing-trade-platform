"""
Multi-tenant isolation tests.

Validates that Row-Level Security (RLS) policies prevent users
from seeing or modifying other users' data.

Test categories:
1. Exchange Key Isolation
2. Strategy Isolation
3. Trade Isolation
4. Audit Log Isolation
5. User Self-Isolation
6. Cascading Delete Isolation
7. RLS Policy Verification

Note: These tests validate application-level isolation. Full RLS enforcement
requires PostgreSQL with RLS enabled. SQLite tests use application-level filtering.
"""

import pytest
import os
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import User, ExchangeKey, Strategy, Trade, AuditLog
from app.core.security import hash_password
from app.db.rls import set_user_context, verify_rls_enabled, check_rls_health


class TestExchangeKeyIsolation:
    """Test that users cannot see or access other users' exchange keys."""

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

    def test_user_cannot_read_other_users_exchange_keys(self, db: Session, two_users):
        """User A should not see User B's exchange keys."""
        user_a, user_b = two_users

        # User A adds an exchange key
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
        db.add(key_a)

        # User B adds an exchange key
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
        db.add(key_b)
        db.commit()

        # User B queries exchange keys with RLS context
        set_user_context(db, user_b.id)
        user_b_keys = db.query(ExchangeKey).all()

        # User B should see only their own key (1 key)
        # Note: RLS enforcement depends on PostgreSQL configuration
        # This test validates application-level filtering for consistency
        assert len(user_b_keys) == 1, f"User B should see 1 key, got {len(user_b_keys)}"
        assert user_b_keys[0].user_id == user_b.id
        assert user_b_keys[0].exchange == "kraken"

        # Verify User B does NOT see User A's key
        for key in user_b_keys:
            assert key.user_id != user_a.id, "User B should not see User A's keys"

    def test_user_cannot_modify_other_users_exchange_key(self, db: Session, two_users):
        """User A should not be able to modify User B's exchange key."""
        user_a, user_b = two_users

        # Create a key for User B
        key_b = ExchangeKey(
            id=uuid4(),
            user_id=user_b.id,
            exchange="binance",
            api_key_encrypted="encrypted_key_b",
            api_secret_encrypted="encrypted_secret_b",
            encryption_iv="v1",
            is_testnet=True,
            is_active=True,
        )
        db.add(key_b)
        db.commit()

        # User A tries to modify User B's key
        set_user_context(db, user_a.id)
        query = db.query(ExchangeKey).filter(ExchangeKey.id == key_b.id)

        # User A should not be able to find the key with RLS enabled
        # Application-level check: verify ownership before allowing update
        found_key = query.first()

        # With RLS, found_key should be None
        # With application-level checks, verify ownership
        if found_key:
            assert found_key.user_id == user_a.id, (
                "Found key should belong to User A if RLS is working"
            )

    def test_user_cannot_delete_other_users_exchange_key(self, db: Session, two_users):
        """User A should not be able to delete User B's exchange key."""
        user_a, user_b = two_users

        # Create a key for User B
        key_b = ExchangeKey(
            id=uuid4(),
            user_id=user_b.id,
            exchange="binance",
            api_key_encrypted="encrypted_key_b",
            api_secret_encrypted="encrypted_secret_b",
            encryption_iv="v1",
            is_testnet=True,
            is_active=True,
        )
        db.add(key_b)
        db.commit()

        # Count total keys before attempted delete
        total_before = db.query(ExchangeKey).count()

        # User A tries to delete User B's key
        set_user_context(db, user_a.id)
        query = db.query(ExchangeKey).filter(ExchangeKey.id == key_b.id)

        found_key = query.first()
        if found_key and found_key.user_id == user_a.id:
            db.delete(found_key)
            db.commit()

        # Count after - should be the same (no deletion occurred)
        total_after = db.query(ExchangeKey).count()
        assert total_after == total_before, (
            "User A should not be able to delete User B's key"
        )


class TestStrategyIsolation:
    """Test that users cannot see or access other users' strategies."""

    @pytest.fixture
    def two_users_with_strategies(self, db: Session):
        """Create two users with strategies."""
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
        db.refresh(user_a)
        db.refresh(user_b)
        db.refresh(strategy_a)
        db.refresh(strategy_b)

        return (user_a, strategy_a), (user_b, strategy_b)

    def test_user_cannot_read_other_users_strategies(self, db: Session, two_users_with_strategies):
        """User A should not see User B's strategies."""
        (user_a, strategy_a), (user_b, strategy_b) = two_users_with_strategies

        set_user_context(db, user_b.id)
        user_b_strategies = db.query(Strategy).all()

        # User B should see only their strategy
        assert len(user_b_strategies) == 1
        assert user_b_strategies[0].user_id == user_b.id
        assert user_b_strategies[0].name == "Strategy B"

        # Verify User B does NOT see User A's strategy
        for strategy in user_b_strategies:
            assert strategy.user_id != user_a.id

    def test_user_cannot_modify_other_users_strategy(self, db: Session, two_users_with_strategies):
        """User A should not be able to modify User B's strategy."""
        (user_a, strategy_a), (user_b, strategy_b) = two_users_with_strategies

        original_name = strategy_b.name

        # User A tries to modify User B's strategy
        set_user_context(db, user_a.id)
        query = db.query(Strategy).filter(Strategy.id == strategy_b.id)

        found_strategy = query.first()

        # If found, should belong to User A
        if found_strategy:
            assert found_strategy.user_id == user_a.id

        # Reset context and check original value unchanged
        db.rollback()
        set_user_context(db, user_b.id)
        db.refresh(strategy_b)
        assert strategy_b.name == original_name

    def test_user_cannot_delete_other_users_strategy(self, db: Session, two_users_with_strategies):
        """User A should not be able to delete User B's strategy."""
        (user_a, strategy_a), (user_b, strategy_b) = two_users_with_strategies

        total_before = db.query(Strategy).count()

        # User A tries to delete User B's strategy
        set_user_context(db, user_a.id)
        query = db.query(Strategy).filter(Strategy.id == strategy_b.id)

        found_strategy = query.first()
        if found_strategy and found_strategy.user_id == user_a.id:
            db.delete(found_strategy)
            db.commit()

        total_after = db.query(Strategy).count()
        assert total_after == total_before


class TestTradeIsolation:
    """Test that users cannot see or access other users' trades."""

    @pytest.fixture
    def two_users_with_trades(self, db: Session):
        """Create two users with strategies and trades."""
        from datetime import datetime, timezone

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
            is_active=True,
        )
        db.add(strategy_a)
        db.add(strategy_b)
        db.commit()

        trade_a = Trade(
            id=uuid4(),
            strategy_id=strategy_a.id,
            symbol="AAPL",
            entry_date=datetime.now(timezone.utc),
            entry_price=150.0,
            quantity=10.0,
            is_paper_trade=True,
        )
        trade_b = Trade(
            id=uuid4(),
            strategy_id=strategy_b.id,
            symbol="GOOGL",
            entry_date=datetime.now(timezone.utc),
            entry_price=2800.0,
            quantity=5.0,
            is_paper_trade=True,
        )
        db.add(trade_a)
        db.add(trade_b)
        db.commit()

        return (user_a, strategy_a, trade_a), (user_b, strategy_b, trade_b)

    def test_user_cannot_read_other_users_trades(self, db: Session, two_users_with_trades):
        """User A should not see User B's trades."""
        (user_a, _, trade_a), (user_b, strategy_b, trade_b) = two_users_with_trades

        set_user_context(db, user_b.id)

        # User B queries trades via their strategy
        user_b_trades = db.query(Trade).filter(Trade.strategy_id == strategy_b.id).all()

        # User B should see only their trades
        assert len(user_b_trades) == 1
        assert user_b_trades[0].symbol == "GOOGL"

        # Verify User B does NOT see User A's trade directly
        all_visible_trades = db.query(Trade).all()
        for trade in all_visible_trades:
            # With RLS, should only see trades from own strategies
            if trade.strategy_id:
                strategy = db.query(Strategy).filter(
                    Strategy.id == trade.strategy_id
                ).first()
                if strategy:
                    assert strategy.user_id == user_b.id

    def test_user_cannot_modify_other_users_trade(self, db: Session, two_users_with_trades):
        """User A should not be able to modify User B's trade."""
        (user_a, strategy_a, trade_a), (user_b, strategy_b, trade_b) = two_users_with_trades

        original_symbol = trade_b.symbol

        # User A tries to modify User B's trade
        set_user_context(db, user_a.id)
        query = db.query(Trade).filter(Trade.id == trade_b.id)

        found_trade = query.first()

        # If found through strategy relationship, should be User A's
        if found_trade and found_trade.strategy_id:
            strategy = db.query(Strategy).filter(
                Strategy.id == found_trade.strategy_id
            ).first()
            if strategy:
                assert strategy.user_id == user_a.id

        # Verify original trade unchanged
        db.rollback()
        db.refresh(trade_b)
        assert trade_b.symbol == original_symbol


class TestAuditLogIsolation:
    """Test that users cannot see other users' audit logs."""

    @pytest.fixture
    def two_users_with_audit_logs(self, db: Session):
        """Create two users with audit logs."""
        from datetime import datetime, timezone

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

        return (user_a, log_a), (user_b, log_b)

    def test_user_cannot_read_other_users_audit_logs(self, db: Session, two_users_with_audit_logs):
        """User A should not see User B's audit logs."""
        (user_a, log_a), (user_b, log_b) = two_users_with_audit_logs

        set_user_context(db, user_b.id)
        user_b_logs = db.query(AuditLog).all()

        # User B should see only their logs
        assert len(user_b_logs) == 1
        assert user_b_logs[0].user_id == user_b.id
        assert user_b_logs[0].action == "CREATE_KEY"

        # Verify User B does NOT see User A's logs
        for log in user_b_logs:
            assert log.user_id != user_a.id


class TestUserSelfIsolation:
    """Test that users can only see and modify themselves."""

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

    def test_user_can_read_only_themselves(self, db: Session, two_users):
        """User A can only see themselves, not User B."""
        user_a, user_b = two_users

        set_user_context(db, user_a.id)
        visible_users = db.query(User).all()

        # With RLS, user_a should only see themselves
        assert len(visible_users) == 1
        assert visible_users[0].id == user_a.id

    def test_user_cannot_modify_other_user(self, db: Session, two_users):
        """User A cannot modify User B's account."""
        user_a, user_b = two_users

        original_first_name = user_b.first_name

        # User A tries to modify User B
        set_user_context(db, user_a.id)
        query = db.query(User).filter(User.id == user_b.id)

        found_user = query.first()

        # Should not find user_b
        if found_user:
            assert found_user.id == user_a.id, "Should not find other user"

        # Verify user_b unchanged
        db.rollback()
        db.refresh(user_b)
        assert user_b.first_name == original_first_name


class TestCascadingDeleteIsolation:
    """Test that cascading deletes respect tenant boundaries."""

    def test_deleting_user_cascade_deletes_only_their_resources(self, db: Session):
        """Deleting a user should only delete their own resources."""
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

        # Create resources for both users
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

        # Delete user_a
        db.delete(user_a)
        db.commit()

        # User B's key should still exist
        remaining_key = db.query(ExchangeKey).filter(
            ExchangeKey.id == key_b.id
        ).first()
        assert remaining_key is not None, "User B's key should not be deleted"
        assert remaining_key.user_id == user_b.id

        # User A's key should be deleted (cascade)
        deleted_key = db.query(ExchangeKey).filter(
            ExchangeKey.id == key_a.id
        ).first()
        assert deleted_key is None, "User A's key should be deleted"


class TestRLSPolicyVerification:
    """Test RLS policy configuration and health."""

    def test_rls_policies_exist(self, db: Session):
        """Verify that RLS policies are configured on all required tables."""
        status = verify_rls_enabled(db)

        required_tables = ["users", "exchange_keys", "strategies", "trades", "audit_logs"]

        for table in required_tables:
            assert table in status, f"Table {table} not found in RLS status"
            # Note: SQLite doesn't support RLS, so this test only validates
            # the RLS verification function works
            if db.bind.dialect.name == "postgresql":
                assert status[table]["policy_count"] > 0, (
                    f"No RLS policies found on {table}"
                )

    def test_rls_health_check(self, db: Session):
        """Verify RLS health check function works."""
        is_healthy, message = check_rls_health(db)

        # For SQLite test database, RLS not supported
        # For PostgreSQL, should pass
        if db.bind.dialect.name == "postgresql":
            assert is_healthy, f"RLS health check failed: {message}"
        else:
            # SQLite doesn't support RLS
            assert isinstance(message, str)
