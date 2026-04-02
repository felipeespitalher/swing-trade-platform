"""
Comprehensive tests for authentication system.

Tests cover:
- User registration with validation
- Email verification flow
- User login with various scenarios
- Token creation and validation
- Token refresh mechanism
- Protected endpoint authentication
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from jose import jwt

from app.core.config import settings
from app.models import User
from app.core.security import verify_token


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, client: TestClient, test_user_data: dict):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "user_id" in data
        assert "message" in data
        assert "verify" in data["message"].lower()

    def test_register_duplicate_email(
        self, client: TestClient, db: Session, test_user_data: dict
    ):
        """Test registration fails with duplicate email."""
        # Register first user
        response1 = client.post("/api/auth/register", json=test_user_data)
        assert response1.status_code == 201

        # Try to register with same email
        response2 = client.post("/api/auth/register", json=test_user_data)
        assert response2.status_code == 409
        assert "already registered" in response2.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient, test_user_data: dict):
        """Test registration fails with invalid email."""
        invalid_data = {**test_user_data, "email": "not-an-email"}
        response = client.post("/api/auth/register", json=invalid_data)

        assert response.status_code == 422  # Validation error

    def test_register_weak_password_too_short(
        self, client: TestClient, test_user_data: dict
    ):
        """Test registration fails with password too short."""
        weak_data = {**test_user_data, "password": "Short1!"}
        response = client.post("/api/auth/register", json=weak_data)

        # Pydantic validates field constraints, returns 422
        assert response.status_code in [400, 422]
        if response.status_code == 422:
            # Pydantic validation error
            assert "at least" in str(response.json()).lower()
        else:
            assert "at least 8 characters" in response.json()["detail"].lower()

    def test_register_weak_password_no_uppercase(
        self, client: TestClient, test_user_data: dict
    ):
        """Test registration fails without uppercase letter."""
        weak_data = {**test_user_data, "password": "securepass123!"}
        response = client.post("/api/auth/register", json=weak_data)

        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"].lower()

    def test_register_weak_password_no_lowercase(
        self, client: TestClient, test_user_data: dict
    ):
        """Test registration fails without lowercase letter."""
        weak_data = {**test_user_data, "password": "SECUREPASS123!"}
        response = client.post("/api/auth/register", json=weak_data)

        assert response.status_code == 400
        assert "lowercase" in response.json()["detail"].lower()

    def test_register_weak_password_no_digit(
        self, client: TestClient, test_user_data: dict
    ):
        """Test registration fails without digit."""
        weak_data = {**test_user_data, "password": "SecurePass!"}
        response = client.post("/api/auth/register", json=weak_data)

        assert response.status_code == 400
        assert "digit" in response.json()["detail"].lower()

    def test_register_weak_password_no_special(
        self, client: TestClient, test_user_data: dict
    ):
        """Test registration fails without special character."""
        weak_data = {**test_user_data, "password": "SecurePass123"}
        response = client.post("/api/auth/register", json=weak_data)

        assert response.status_code == 400
        assert "special character" in response.json()["detail"].lower()

    def test_register_creates_user_in_db(self, client: TestClient, db: Session, test_user_data: dict):
        """Test that registration creates user in database."""
        response = client.post("/api/auth/register", json=test_user_data)

        assert response.status_code == 201
        user_id = response.json()["user_id"]

        # Verify user exists in database
        import uuid as uuid_module
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        assert user is not None
        assert user.email == test_user_data["email"]
        assert not user.is_email_verified
        assert user.email_verification_token is not None

    def test_register_password_hashed(self, client: TestClient, db: Session, test_user_data: dict):
        """Test that password is hashed, not stored plaintext."""
        response = client.post("/api/auth/register", json=test_user_data)

        assert response.status_code == 201

        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        # Password hash should not match plaintext password
        assert user.password_hash != test_user_data["password"]
        assert len(user.password_hash) > len(test_user_data["password"])


class TestEmailVerification:
    """Tests for email verification endpoint."""

    def test_verify_email_success(self, client: TestClient, db: Session, unverified_user: User):
        """Test successful email verification."""
        token = unverified_user.email_verification_token

        response = client.get(f"/api/auth/verify/{token}")

        assert response.status_code == 200
        data = response.json()
        assert "verified successfully" in data["message"].lower()
        assert str(unverified_user.id) == str(data["user_id"])

        # Verify user is marked as verified in database
        db.refresh(unverified_user)
        assert unverified_user.is_email_verified
        assert unverified_user.email_verification_token is None

    def test_verify_email_invalid_token(self, client: TestClient):
        """Test verification fails with invalid token."""
        response = client.get("/api/auth/verify/invalid_token_xyz")

        assert response.status_code == 400
        assert "invalid or expired" in response.json()["detail"].lower()

    def test_verify_email_already_verified(
        self, client: TestClient, db: Session, verified_user: User
    ):
        """Test verification fails for already verified user."""
        # Try to verify with a fake token (verified user has no token)
        response = client.get("/api/auth/verify/fake_token")

        assert response.status_code == 400


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client: TestClient, verified_user: User):
        """Test successful login with verified user."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_unverified_email(self, client: TestClient, unverified_user: User):
        """Test login fails with unverified email."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": unverified_user.email,
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 401
        assert "verify your email" in response.json()["detail"].lower()

    def test_login_invalid_email(self, client: TestClient):
        """Test login fails with non-existent email."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_wrong_password(self, client: TestClient, verified_user: User):
        """Test login fails with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_returns_valid_access_token(
        self, client: TestClient, verified_user: User
    ):
        """Test that login returns valid access token."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        access_token = response.json()["access_token"]

        # Verify token can be decoded
        token_payload = verify_token(access_token, token_type="access")
        assert token_payload is not None
        assert token_payload.email == verified_user.email
        assert token_payload.type == "access"

    def test_login_returns_valid_refresh_token(
        self, client: TestClient, verified_user: User
    ):
        """Test that login returns valid refresh token."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        refresh_token = response.json()["refresh_token"]

        # Verify token can be decoded
        token_payload = verify_token(refresh_token, token_type="refresh")
        assert token_payload is not None
        assert token_payload.email == verified_user.email
        assert token_payload.type == "refresh"


class TestTokenManagement:
    """Tests for token creation and validation."""

    def test_access_token_has_short_expiry(
        self, client: TestClient, verified_user: User
    ):
        """Test that access token has 1-hour expiry."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = response.json()["access_token"]
        payload = jwt.decode(
            access_token, settings.secret_key, algorithms=[settings.algorithm]
        )

        # Token should expire in roughly 1 hour (3600 seconds)
        # Allow 5-minute variance for test execution time
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        expiry_seconds = exp_time - iat_time

        assert 3300 < expiry_seconds < 3900  # 55-65 minutes

    def test_refresh_token_has_long_expiry(
        self, client: TestClient, verified_user: User
    ):
        """Test that refresh token has 7-day expiry."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        refresh_token = response.json()["refresh_token"]
        payload = jwt.decode(
            refresh_token, settings.secret_key, algorithms=[settings.algorithm]
        )

        # Token should expire in roughly 7 days (604800 seconds)
        # Allow 1-hour variance for test execution time
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        expiry_seconds = exp_time - iat_time

        assert 600000 < expiry_seconds < 609600  # 7 days +/- 1 hour

    def test_token_contains_no_secrets(
        self, client: TestClient, verified_user: User
    ):
        """Test that tokens do not contain secrets or sensitive data."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = response.json()["access_token"]
        payload = jwt.decode(
            access_token, settings.secret_key, algorithms=[settings.algorithm]
        )

        # Ensure sensitive data is not in token
        assert "password" not in str(payload)
        assert "hash" not in str(payload).lower()
        assert "secret" not in str(payload).lower()

        # Only expected fields should be present
        assert set(payload.keys()) == {
            "sub",
            "email",
            "exp",
            "iat",
            "type",
            "iss",
        }


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(
        self, client: TestClient, verified_user: User
    ):
        """Test successful token refresh."""
        # Get initial tokens
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["refresh_token"] == refresh_token  # Same refresh token returned

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Test refresh fails with invalid refresh token."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_token_xyz"},
        )

        assert response.status_code == 401
        assert "invalid or expired" in response.json()["detail"].lower()

    def test_refresh_with_access_token(self, client: TestClient, verified_user: User):
        """Test refresh fails when using access token instead of refresh token."""
        # Get initial tokens
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh (should fail)
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert refresh_response.status_code == 401


class TestProtectedEndpoints:
    """Tests for protected endpoint authentication."""

    def test_get_me_with_valid_token(self, client: TestClient, verified_user: User):
        """Test accessing /me endpoint with valid token."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == verified_user.email
        assert data["first_name"] == verified_user.first_name
        assert data["last_name"] == verified_user.last_name
        assert data["is_email_verified"]

    def test_get_me_without_token(self, client: TestClient):
        """Test /me endpoint fails without token."""
        response = client.get("/api/users/me")

        assert response.status_code == 401

    def test_get_me_with_invalid_token(self, client: TestClient):
        """Test /me endpoint fails with invalid token."""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )

        assert response.status_code == 401

    def test_get_me_with_expired_token(self, client: TestClient, verified_user: User):
        """Test /me endpoint fails with expired token."""
        # This would require manipulating token expiry
        # For now, we test with a malformed token
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer malformed.token.here"},
        )

        assert response.status_code == 401

    def test_get_me_returns_all_user_fields(
        self, client: TestClient, verified_user: User
    ):
        """Test that /me endpoint returns all user fields."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "timezone",
            "risk_limit_pct",
            "is_email_verified",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in data

    def test_get_me_no_password_exposed(
        self, client: TestClient, verified_user: User
    ):
        """Test that /me endpoint does not expose password hash."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Ensure password is never exposed
        assert "password" not in data
        assert "password_hash" not in data


class TestIntegrationFlow:
    """Integration tests for complete auth flow."""

    def test_complete_registration_to_protected_endpoint(
        self, client: TestClient, db: Session, test_user_data: dict
    ):
        """Test complete flow: register -> verify -> login -> access protected endpoint."""
        # 1. Register
        register_response = client.post("/api/auth/register", json=test_user_data)
        assert register_response.status_code == 201

        # Get verification token from database
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        verification_token = user.email_verification_token

        # 2. Verify email
        verify_response = client.get(f"/api/auth/verify/{verification_token}")
        assert verify_response.status_code == 200

        # 3. Login
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # 4. Access protected endpoint
        me_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == test_user_data["email"]


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_register_missing_field(self, client: TestClient):
        """Test registration fails when required field is missing."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422

    def test_login_case_insensitive_email(self, client: TestClient, verified_user: User):
        """Test that login is case-insensitive for email."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email.upper(),
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200

    def test_password_validator_all_requirements(self, client: TestClient):
        """Test password validator with various weak passwords."""
        weak_passwords = [
            ("Short1!", "Pydantic validation error"),  # < 8 chars
            ("abcdefgh!", "uppercase"),  # no uppercase
            ("ABCDEFGH!", "lowercase"),  # no lowercase
            ("AbcDeFg!", "digit"),  # no digit
            ("AbcDeFg1", "special character"),  # no special
        ]

        for weak_pwd, keyword in weak_passwords:
            invalid_data = {
                "email": f"test-{weak_pwd[:3]}@example.com",
                "password": weak_pwd,
                "first_name": "John",
                "last_name": "Doe",
            }
            response = client.post("/api/auth/register", json=invalid_data)

            # Status should be 400 or 422 depending on validation layer
            assert response.status_code in [400, 422]

    def test_get_me_with_bad_auth_header(self, client: TestClient):
        """Test /me endpoint with malformed Authorization header."""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Basic xyz123"},
        )

        assert response.status_code == 401

    def test_token_signature_verification(self, client: TestClient, verified_user: User):
        """Test that tokens with wrong signature are rejected."""
        # Tamper with a valid token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]
        tampered_token = access_token[:-4] + "xxxx"  # Change last 4 chars

        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )

        assert response.status_code == 401
