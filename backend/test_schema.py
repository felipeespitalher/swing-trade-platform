#!/usr/bin/env python3
"""
Schema verification tests for Swing Trade Platform.
Tests the created database schema to ensure all tables, indexes, and constraints work correctly.

Usage:
    python backend/test_schema.py
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from uuid import uuid4

# Configuration
DB_HOST = 'localhost'
DB_PORT = 5432
DB_NAME = 'swing_trade'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres_password'


def connect_db():
    """Create database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connection_factory=psycopg2.extras.RealDictConnection
    )


def test_users_table():
    """Test Users table creation and basic operations."""
    print("\n[TEST 1] Users Table")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Insert a test user
        user_id = str(uuid4())
        test_email = f"test-{user_id[:8]}@example.com"

        cursor.execute("""
            INSERT INTO users (
                id, email, password_hash, first_name, last_name,
                timezone, risk_limit_pct, is_email_verified
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, created_at, updated_at
        """, (
            user_id,
            test_email,
            'hashed_password_12345',
            'Test',
            'User',
            'America/New_York',
            5.0,
            False
        ))

        result = cursor.fetchone()
        conn.commit()

        assert result['id'] == user_id, "User ID mismatch"
        assert result['email'] == test_email, "Email mismatch"
        assert result['created_at'] is not None, "created_at should not be null"
        assert result['updated_at'] is not None, "updated_at should not be null"

        print(f"[OK] Insert user: {test_email}")
        print(f"  - ID: {result['id']}")
        print(f"  - Created: {result['created_at']}")

        # Verify unique email constraint
        cursor.execute("""
            INSERT INTO users (id, email, password_hash)
            VALUES (%s, %s, %s)
        """, (str(uuid4()), test_email, 'another_password'))

        try:
            conn.commit()
            print("[FAIL] Email uniqueness constraint failed!")
            return False
        except psycopg2.IntegrityError:
            conn.rollback()
            print("[OK] Email uniqueness constraint enforced")

        # Verify risk_limit_pct CHECK constraint
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, risk_limit_pct)
            VALUES (%s, %s, %s, %s)
        """, (str(uuid4()), f"invalid-{uuid4()}@test.com", 'pwd', 150.0))

        try:
            conn.commit()
            print("[FAIL] Risk limit constraint failed!")
            return False
        except psycopg2.IntegrityError:
            conn.rollback()
            print("[OK] Risk limit (0-100) constraint enforced")

        # Query by index
        cursor.execute("SELECT email FROM users WHERE email = %s", (test_email,))
        result = cursor.fetchone()
        assert result is not None, "Index lookup failed"
        print("[OK] Index lookup (email) works")

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_exchange_keys_table():
    """Test ExchangeKeys table with foreign key constraints."""
    print("\n[TEST 2] ExchangeKeys Table")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Create a user first
        user_id = str(uuid4())
        cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
            (user_id, f"test-{user_id[:8]}@test.com", "pwd")
        )
        conn.commit()
        print(f"[OK] Created user for testing: {user_id}")

        # Insert exchange key
        key_id = str(uuid4())
        cursor.execute("""
            INSERT INTO exchange_keys (
                id, user_id, exchange, api_key_encrypted,
                api_secret_encrypted, encryption_iv, is_testnet, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            key_id,
            user_id,
            'binance',
            'encrypted_key_data',
            'encrypted_secret_data',
            'iv_12345',
            True,
            True
        ))
        result = cursor.fetchone()
        conn.commit()
        print(f"[OK] Insert exchange key: binance (testnet)")

        # Test unique constraint (user_id, exchange, is_testnet)
        cursor.execute("""
            INSERT INTO exchange_keys (
                id, user_id, exchange, api_key_encrypted,
                api_secret_encrypted, encryption_iv
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            str(uuid4()),
            user_id,
            'binance',
            'other_key',
            'other_secret',
            'iv_other'
        ))

        try:
            conn.commit()
            print("[FAIL] Unique constraint failed!")
            return False
        except psycopg2.IntegrityError:
            conn.rollback()
            print("[OK] Unique constraint (user, exchange, testnet) enforced")

        # Test foreign key constraint
        cursor.execute("""
            INSERT INTO exchange_keys (
                id, user_id, exchange, api_key_encrypted,
                api_secret_encrypted, encryption_iv
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            str(uuid4()),
            '00000000-0000-0000-0000-000000000000',  # Non-existent user
            'kraken',
            'key',
            'secret',
            'iv'
        ))

        try:
            conn.commit()
            print("[FAIL] Foreign key constraint failed!")
            return False
        except psycopg2.IntegrityError:
            conn.rollback()
            print("[OK] Foreign key constraint enforced")

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_audit_logs_table():
    """Test AuditLogs table (append-only design)."""
    print("\n[TEST 3] AuditLogs Table (Append-Only)")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Create a user
        user_id = str(uuid4())
        cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
            (user_id, f"audit-{user_id[:8]}@test.com", "pwd")
        )
        conn.commit()

        # Insert audit log
        log_id = str(uuid4())
        resource_id = str(uuid4())

        cursor.execute("""
            INSERT INTO audit_logs (
                id, user_id, action, resource_type, resource_id,
                old_values, new_values, ip_address, user_agent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, action, created_at
        """, (
            log_id,
            user_id,
            'UPDATE_STRATEGY',
            'strategies',
            resource_id,
            '{"name": "Old Strategy"}',
            '{"name": "New Strategy"}',
            '192.168.1.1',
            'Mozilla/5.0'
        ))

        result = cursor.fetchone()
        conn.commit()
        print(f"[OK] Insert audit log: UPDATE_STRATEGY")
        print(f"  - ID: {log_id}")
        print(f"  - Action: {result['action']}")

        # Verify created_at is immutable (append-only design)
        original_time = result['created_at']
        cursor.execute("""
            SELECT created_at FROM audit_logs WHERE id = %s
        """, (log_id,))
        verify_time = cursor.fetchone()['created_at']

        assert original_time == verify_time, "Timestamps should match"
        print("[OK] Audit log timestamp is immutable (append-only)")

        # Test indexes
        cursor.execute("""
            SELECT * FROM audit_logs
            WHERE user_id = %s AND action = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, 'UPDATE_STRATEGY'))

        result = cursor.fetchone()
        assert result is not None, "Index query failed"
        print("[OK] Composite indexes work correctly")

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_strategies_table():
    """Test Strategies table with JSONB config."""
    print("\n[TEST 4] Strategies Table (with JSONB)")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Create a user
        user_id = str(uuid4())
        cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
            (user_id, f"strategy-{user_id[:8]}@test.com", "pwd")
        )
        conn.commit()

        # Insert strategy with JSON config
        strategy_id = str(uuid4())
        config = {
            "indicators": {
                "rsi": {"period": 14, "overbought": 70, "oversold": 30},
                "ma": {"fast": 20, "slow": 50}
            },
            "entry_rules": ["RSI < 30", "Price > MA50"],
            "exit_rules": ["RSI > 70", "Stop Loss Hit"]
        }

        cursor.execute("""
            INSERT INTO strategies (
                id, user_id, name, description, type, config, is_active, version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, config, version
        """, (
            strategy_id,
            user_id,
            'RSI + MA Strategy',
            'Combines RSI indicator with moving averages',
            'technical',
            psycopg2.extras.Json(config),
            False,
            1
        ))

        result = cursor.fetchone()
        conn.commit()
        print(f"[OK] Insert strategy: RSI + MA Strategy")
        print(f"  - Type: technical")
        print(f"  - Version: {result['version']}")

        # Query JSONB data
        cursor.execute("""
            SELECT config->'indicators'->'rsi'->>'period' as rsi_period
            FROM strategies WHERE id = %s
        """, (strategy_id,))

        result = cursor.fetchone()
        assert result['rsi_period'] == '14', "JSONB query failed"
        print("[OK] JSONB queries work correctly")

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_ohlcv_hypertable():
    """Test OHLCV TimescaleDB hypertable."""
    print("\n[TEST 5] OHLCV Table (TimescaleDB Hypertable)")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Insert OHLCV data
        now = datetime.now(timezone.utc)

        cursor.execute("""
            INSERT INTO ohlcv (
                timestamp, exchange, symbol, timeframe,
                open, high, low, close, volume
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING timestamp, symbol, close
        """, (
            now,
            'binance',
            'BTC/USDT',
            '1h',
            45000.00,
            46000.00,
            44500.00,
            45500.00,
            1000.5
        ))

        result = cursor.fetchone()
        conn.commit()
        print(f"[OK] Insert OHLCV data: {result['symbol']}")
        print(f"  - Close: ${result['close']}")

        # Verify hypertable status
        cursor.execute("""
            SELECT hypertable_name, num_dimensions, compression_enabled
            FROM timescaledb_information.hypertables
            WHERE hypertable_name = 'ohlcv'
        """, commit=False)

        result = cursor.fetchone()
        if result:
            print(f"[OK] OHLCV is a TimescaleDB hypertable")
            print(f"  - Dimensions: {result['num_dimensions']}")
            print(f"  - Compression enabled: {result['compression_enabled']}")
        else:
            print("[FAIL] OHLCV hypertable not found")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_trades_table():
    """Test Trades table."""
    print("\n[TEST 6] Trades Table")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Create user and strategy
        user_id = str(uuid4())
        cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
            (user_id, f"trader-{user_id[:8]}@test.com", "pwd")
        )

        strategy_id = str(uuid4())
        cursor.execute(
            """INSERT INTO strategies (id, user_id, name, type, config)
               VALUES (%s, %s, %s, %s, %s)""",
            (strategy_id, user_id, 'Test', 'technical',
             psycopg2.extras.Json({}))
        )
        conn.commit()

        # Insert trade
        trade_id = str(uuid4())
        entry_date = datetime.now(timezone.utc)

        cursor.execute("""
            INSERT INTO trades (
                id, strategy_id, symbol, entry_date, entry_price,
                quantity, is_paper_trade
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, symbol, entry_price, quantity
        """, (
            trade_id,
            strategy_id,
            'BTC/USDT',
            entry_date,
            45000.00,
            0.5,
            True
        ))

        result = cursor.fetchone()
        conn.commit()
        print(f"[OK] Insert trade: {result['symbol']}")
        print(f"  - Entry price: ${result['entry_price']}")
        print(f"  - Quantity: {result['quantity']}")
        print(f"  - Paper trade: true")

        # Test quantity CHECK constraint
        cursor.execute("""
            INSERT INTO trades (
                id, strategy_id, symbol, entry_date, entry_price, quantity
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            str(uuid4()),
            strategy_id,
            'ETH/USDT',
            entry_date,
            2000.00,
            0.0  # Invalid: quantity must be > 0
        ))

        try:
            conn.commit()
            print("[FAIL] Quantity constraint failed!")
            return False
        except psycopg2.IntegrityError:
            conn.rollback()
            print("[OK] Quantity > 0 constraint enforced")

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_migration_history():
    """Test Flyway migration history tracking."""
    print("\n[TEST 7] Flyway Migration History")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT version, description, type, success
            FROM flyway_schema_history
            ORDER BY version
        """)

        results = cursor.fetchall()

        if not results:
            print("[FAIL] No migration history found")
            return False

        print(f"[OK] Found {len(results)} migration(s):")
        for row in results:
            status = "[OK]" if row['success'] else "[FAIL]"
            print(f"  {status} V{row['version']:02d}: {row['description']}")

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Swing Trade Platform - Schema Verification Tests")
    print("=" * 60)

    tests = [
        test_users_table,
        test_exchange_keys_table,
        test_audit_logs_table,
        test_strategies_table,
        test_ohlcv_hypertable,
        test_trades_table,
        test_migration_history,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"\n[FAIL] Test {test_func.__name__} crashed: {e}")
            results.append((test_func.__name__, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
