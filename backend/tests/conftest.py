"""
Pytest configuration and fixtures for testing.

Provides fixtures for:
- FastAPI test client
- Database session
- Test user data
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
import tempfile
import logging

from app.main import app
from app.models import Base
from app.db.session import get_db
from app.core.security import hash_password
from app.models import User
import uuid

logger = logging.getLogger(__name__)

# Module-level engine and session factory for test isolation
test_engine = None
TestingSessionLocal_global = None


@pytest.fixture(autouse=True)
def disable_security_middleware(monkeypatch, request):
    """
    Disable rate limiting and CSRF for all tests except those that
    specifically test these features (test_rate_limiting, test_csrf).
    """
    module = getattr(request.module, "__name__", "") or ""
    skip_modules = ("test_rate_limiting", "test_csrf", "test_integration")
    if any(m in module for m in skip_modules):
        yield
        return

    try:
        from app.core.rate_limit import RateLimiter
        monkeypatch.setattr(RateLimiter, "is_rate_limited", lambda *a, **kw: False)
    except ImportError:
        pass

    try:
        from app.core.csrf import CSRFManager
        monkeypatch.setattr(CSRFManager, "validate_token", lambda *a, **kw: True)
    except ImportError:
        pass

    yield


@pytest.fixture(scope="function")
def db():
    """
    Create test database and session for each test.

    Scope: function - creates new file-based DB for each test (SQLite)
    or uses PostgreSQL if available.
    """
    global test_engine, TestingSessionLocal_global

    # Try to use PostgreSQL for tests (better for RLS testing)
    use_postgres = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

    if use_postgres:
        # Use PostgreSQL test database
        SQLALCHEMY_TEST_DATABASE_URL = use_postgres
        test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)

        # Truncate all tables before test (PostgreSQL only)
        session_temp = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)()
        try:
            # Get all table names
            result = session_temp.execute(
                text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename NOT LIKE 'flyway%'
                    ORDER BY tablename
                """)
            )
            tables = [row[0] for row in result]

            # Disable RLS temporarily for truncation (needed to delete all rows)
            for table in tables:
                session_temp.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

            # Truncate all tables
            for table in tables:
                session_temp.execute(text(f"TRUNCATE TABLE {table} CASCADE"))

            # Re-enable RLS
            for table in tables:
                session_temp.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

            session_temp.commit()
        except Exception as e:
            logger.warning(f"Failed to truncate PostgreSQL tables: {e}")
            session_temp.rollback()
        finally:
            session_temp.close()
    else:
        # Fall back to SQLite
        import tempfile
        temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_db_fd)

        SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{temp_db_path}"
        test_engine = create_engine(
            SQLALCHEMY_TEST_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        # Create all tables for SQLite
        Base.metadata.create_all(bind=test_engine)

    # Create session factory
    TestingSessionLocal_global = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    session = TestingSessionLocal_global()

    yield session

    session.close()

    # Only drop tables for SQLite (in-memory/temp databases)
    # For PostgreSQL, keep the database intact for inspection/debugging
    if not use_postgres:
        Base.metadata.drop_all(bind=test_engine)

    test_engine.dispose()

    # Clean up temp file if SQLite
    if not use_postgres and 'temp_db_path' in locals():
        try:
            os.unlink(temp_db_path)
        except:
            pass


@pytest.fixture(scope="function")
def client(db: Session):
    """
    Create FastAPI test client with test database.

    Args:
        db: Test database session

    Yields:
        TestClient instance
    """
    global test_engine, TestingSessionLocal_global

    def override_get_db():
        # Use the same session factory as db fixture
        session = TestingSessionLocal_global()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """
    Provide test user registration data.

    Returns:
        Dict with user registration data
    """
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
    }


@pytest.fixture
def test_user_weak_password():
    """
    Provide test data with weak password.

    Returns:
        Dict with weak password
    """
    return {
        "email": "test@example.com",
        "password": "weak",
        "first_name": "John",
        "last_name": "Doe",
    }


@pytest.fixture
def verified_user(db: Session):
    """
    Create a verified test user in database.

    Args:
        db: Test database session

    Yields:
        User object
    """
    user = User(
        id=uuid.uuid4(),
        email="verified@example.com",
        password_hash=hash_password("SecurePass123!"),
        first_name="Jane",
        last_name="Smith",
        is_email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    yield user


@pytest.fixture
def unverified_user(db: Session):
    """
    Create an unverified test user in database.

    Args:
        db: Test database session

    Yields:
        User object
    """
    user = User(
        id=uuid.uuid4(),
        email="unverified@example.com",
        password_hash=hash_password("SecurePass123!"),
        first_name="Bob",
        last_name="Johnson",
        is_email_verified=False,
        email_verification_token="test_token_12345",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    yield user
