"""
Comprehensive tests for user account settings API.

Tests cover:
- Getting current user
- Updating user settings (timezone, risk limit, name)
- Changing password
- Changing email address
- Validation of all inputs
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User


class TestGetCurrentUser:
    """Tests for GET /users/me endpoint."""

    def test_get_current_user_success(self, client: TestClient, verified_user: User):
        """Test getting current user with valid token."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(verified_user.id)
        assert data["email"] == verified_user.email
        assert data["first_name"] == verified_user.first_name
        assert data["last_name"] == verified_user.last_name
        assert data["timezone"] == "UTC"
        assert data["risk_limit_pct"] == 2.0
        assert data["is_email_verified"] is True

    def test_get_current_user_without_token(self, client: TestClient):
        """Test getting current user without authentication token."""
        response = client.get("/api/users/me")

        assert response.status_code == 401
        assert "authentication" in response.json()["detail"].lower()

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )

        assert response.status_code == 401

    def test_get_current_user_no_password_exposed(
        self, client: TestClient, verified_user: User
    ):
        """Test that password hash is not exposed in response."""
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
        assert "password" not in data
        assert "password_hash" not in data


class TestUpdateUserSettings:
    """Tests for PATCH /users/me endpoint."""

    def test_update_timezone_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test successfully updating timezone."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Update timezone
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"timezone": "America/New_York"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/New_York"

        # Verify in database
        db.refresh(verified_user)
        assert verified_user.timezone == "America/New_York"

    def test_update_risk_limit_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test successfully updating risk limit."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Update risk limit
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"risk_limit_pct": 5.5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_limit_pct"] == 5.5

        # Verify in database
        db.refresh(verified_user)
        assert float(verified_user.risk_limit_pct) == 5.5

    def test_update_first_name_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test successfully updating first name."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Update first name
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"first_name": "Johnny"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Johnny"

        # Verify in database
        db.refresh(verified_user)
        assert verified_user.first_name == "Johnny"

    def test_update_last_name_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test successfully updating last name."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Update last name
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"last_name": "Johnson"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["last_name"] == "Johnson"

        # Verify in database
        db.refresh(verified_user)
        assert verified_user.last_name == "Johnson"

    def test_update_multiple_fields_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test updating multiple fields at once."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Update multiple fields
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "Jane",
                "last_name": "Doe",
                "timezone": "Europe/London",
                "risk_limit_pct": 7.25,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Doe"
        assert data["timezone"] == "Europe/London"
        assert data["risk_limit_pct"] == 7.25

    def test_update_no_fields_returns_current_user(
        self, client: TestClient, verified_user: User
    ):
        """Test that updating with no fields returns current user."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Update with empty body
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == verified_user.email

    def test_update_invalid_risk_limit_too_low(self, client: TestClient, verified_user: User):
        """Test that risk limit below 0.1 is rejected."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to set risk limit too low
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"risk_limit_pct": 0.05},
        )

        assert response.status_code == 422

    def test_update_invalid_risk_limit_too_high(self, client: TestClient, verified_user: User):
        """Test that risk limit above 100.0 is rejected."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to set risk limit too high
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"risk_limit_pct": 150.0},
        )

        assert response.status_code == 422

    def test_update_invalid_timezone(self, client: TestClient, verified_user: User):
        """Test that invalid timezone is rejected."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to set invalid timezone
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"timezone": "InvalidTimeZone"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_update_without_token(self, client: TestClient):
        """Test updating user without authentication token."""
        response = client.patch(
            "/api/users/me",
            json={"first_name": "John"},
        )

        assert response.status_code == 401


class TestChangePassword:
    """Tests for PATCH /users/me/password endpoint."""

    def test_change_password_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test successfully changing password."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Change password
        response = client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "changed" in data["message"].lower()

        # Verify old password no longer works
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )
        assert login_response.status_code == 401

        # Verify new password works
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "NewSecurePass456!",
            },
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_old_password(
        self, client: TestClient, verified_user: User
    ):
        """Test changing password with incorrect old password."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to change password with wrong old password
        response = client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "WrongPassword123!",
                "new_password": "NewSecurePass456!",
            },
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_weak_new_password(
        self, client: TestClient, verified_user: User
    ):
        """Test changing password to a weak password."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to set weak new password
        response = client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "SecurePass123!",
                "new_password": "weak",
            },
        )

        assert response.status_code == 400
        assert "at least" in response.json()["detail"].lower()

    def test_change_password_weak_no_uppercase(
        self, client: TestClient, verified_user: User
    ):
        """Test that new password must have uppercase."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try password without uppercase
        response = client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "SecurePass123!",
                "new_password": "newsecurepass456!",
            },
        )

        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"].lower()

    def test_change_password_without_token(self, client: TestClient):
        """Test changing password without authentication token."""
        response = client.patch(
            "/api/users/me/password",
            json={
                "old_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
            },
        )

        assert response.status_code == 401


class TestChangeEmail:
    """Tests for PATCH /users/me/email endpoint."""

    def test_change_email_success(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test successfully changing email."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Change email
        response = client.patch(
            "/api/users/me/email",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "new_email": "newemail@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "verify" in data["message"].lower()

        # Verify user email is updated in database
        db.refresh(verified_user)
        assert verified_user.email == "newemail@example.com"

        # Verify user is marked as unverified
        assert verified_user.is_email_verified is False
        assert verified_user.email_verification_token is not None

    def test_change_email_wrong_password(
        self, client: TestClient, verified_user: User
    ):
        """Test changing email with wrong password."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to change email with wrong password
        response = client.patch(
            "/api/users/me/email",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "new_email": "newemail@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_email_duplicate_email(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test that changing to an existing email fails."""
        # Create another user
        from app.core.security import hash_password
        from app.models import User as UserModel
        import uuid

        other_user = UserModel(
            id=uuid.uuid4(),
            email="other@example.com",
            password_hash=hash_password("SecurePass123!"),
            first_name="Other",
            last_name="User",
            is_email_verified=True,
        )
        db.add(other_user)
        db.commit()

        # Try to change verified_user's email to other_user's email
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        response = client.patch(
            "/api/users/me/email",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "new_email": "other@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_change_email_invalid_email(self, client: TestClient, verified_user: User):
        """Test that invalid email format is rejected."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to change to invalid email
        response = client.patch(
            "/api/users/me/email",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "new_email": "not-an-email",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422

    def test_change_email_case_insensitive(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test that email is stored in lowercase."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )

        access_token = login_response.json()["access_token"]

        # Change email with uppercase
        response = client.patch(
            "/api/users/me/email",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "new_email": "NewEmail@EXAMPLE.COM",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200

        # Verify email is stored in lowercase
        db.refresh(verified_user)
        assert verified_user.email == "newemail@example.com"

    def test_change_email_without_token(self, client: TestClient):
        """Test changing email without authentication token."""
        response = client.patch(
            "/api/users/me/email",
            json={
                "new_email": "newemail@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 401


class TestIntegrationUserSettings:
    """Integration tests for user settings workflow."""

    def test_complete_user_profile_update_flow(
        self, client: TestClient, verified_user: User, db: Session
    ):
        """Test complete flow: login -> update settings -> change password -> change email."""
        # 1. Login
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": verified_user.email,
                "password": "SecurePass123!",
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # 2. Get current profile
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        original_email = response.json()["email"]

        # 3. Update settings
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "Updated",
                "timezone": "America/Los_Angeles",
                "risk_limit_pct": 10.0,
            },
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"

        # 4. Change password
        response = client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "SecurePass123!",
                "new_password": "UpdatedPass789!",
            },
        )
        assert response.status_code == 200

        # 5. Verify new password works
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": original_email,
                "password": "UpdatedPass789!",
            },
        )
        assert login_response.status_code == 200

        # 6. Get new token and change email
        new_token = login_response.json()["access_token"]
        response = client.patch(
            "/api/users/me/email",
            headers={"Authorization": f"Bearer {new_token}"},
            json={
                "new_email": "finalmail@example.com",
                "password": "UpdatedPass789!",
            },
        )
        assert response.status_code == 200

        # 7. Verify email is changed in database
        db.refresh(verified_user)
        assert verified_user.email == "finalmail@example.com"
