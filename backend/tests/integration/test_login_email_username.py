# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for login endpoint with email and username support.

Tests the new LoginRequest schema that accepts both 'email' and 'username' fields.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestLoginEmailUsernameSupport:
    """Test login endpoint with both email and username field support."""

    async def test_login_with_email_field(self, client, test_patron, test_user_data):
        """Test successful login using the 'email' field."""
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_with_username_field(self, client, test_patron, test_user_data):
        """Test successful login using the 'username' field (backwards compatibility)."""
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_with_both_email_and_username(self, client, test_patron, test_user_data):
        """Test login when both email and username are provided (email takes precedence)."""
        login_data = {
            "email": test_user_data["email"],
            "username": "other@example.com",  # Should be ignored
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_with_neither_email_nor_username(self, client):
        """Test login fails when neither email nor username is provided."""
        login_data = {
            "password": "SomePassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 400
        data = response.json()
        message = data["error"]["message"]
        assert "email" in message.lower() or "username" in message.lower()

    async def test_login_with_empty_email_and_username(self, client):
        """Test login fails when both email and username are empty strings."""
        login_data = {
            "email": "",
            "username": "",
            "password": "SomePassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 400

    async def test_login_with_whitespace_email(self, client, test_patron, test_user_data):
        """Test login with email containing whitespace (should be stripped)."""
        login_data = {
            "email": f"  {test_user_data['email']}  ",
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_email_wrong_password(self, client, test_patron, test_user_data):
        """Test login with email field but wrong password."""
        login_data = {
            "email": test_user_data["email"],
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "didn't work" in response.json()["error"]["message"].lower()

    async def test_login_username_wrong_password(self, client, test_patron, test_user_data):
        """Test login with username field but wrong password."""
        login_data = {
            "username": test_user_data["email"],
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "didn't work" in response.json()["error"]["message"].lower()

    async def test_login_email_nonexistent_user(self, client):
        """Test login with email field for non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "ValidPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    async def test_login_username_nonexistent_user(self, client):
        """Test login with username field for non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "ValidPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    async def test_login_email_lockout(self, client, test_patron, test_user_data):
        """Test account lockout using email field."""
        login_data = {
            "email": test_user_data["email"],
            "password": "WrongPassword123!",
        }

        # Make 5 failed attempts
        for _ in range(5):
            response = await client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401

        # 6th attempt should be locked
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 423  # Locked
        assert "locked" in response.json()["error"]["message"].lower()

    async def test_login_username_lockout(self, client, test_patron, test_user_data):
        """Test account lockout using username field."""
        login_data = {
            "username": test_user_data["email"],
            "password": "WrongPassword123!",
        }

        # Make 5 failed attempts
        for _ in range(5):
            response = await client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401

        # 6th attempt should be locked
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 423  # Locked
        assert "locked" in response.json()["error"]["message"].lower()

    async def test_login_inactive_user_email(self, client, test_db, test_user_data):
        """Test login with inactive user using email field."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        # Create an inactive user
        inactive_user = User(
            email=test_user_data["email"],
            password_hash=hash_password(test_user_data["password"]),
            first_name=test_user_data["first_name"],
            last_name=test_user_data["last_name"],
            role=UserRole.PATRON,
            is_active=False,
            email_verified=True,
        )
        test_db.add(inactive_user)
        await test_db.commit()

        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        # app/api/v1/auth/login.py:189-200: an inactive user deliberately gets
        # the SAME 401 + generic message as wrong-password, not a distinct
        # 400/"inactive" response -- security hardening against account-status
        # enumeration (don't tell an unauthenticated caller *why* login failed).
        assert response.status_code == 401
        assert "didn't work" in response.json()["error"]["message"].lower()

    async def test_login_returns_valid_access_token(self, client, test_patron, test_user_data):
        """Test that login with email returns a valid access token."""
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        access_token = response.json()["access_token"]

        # Use token to access protected endpoint
        profile_response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == test_user_data["email"]

    async def test_login_missing_password(self, client, test_patron, test_user_data):
        """Test login fails when password is missing."""
        login_data = {
            "email": test_user_data["email"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422  # Validation error
