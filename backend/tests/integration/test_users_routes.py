# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for user management API endpoints.

Tests for:
- Lock user endpoint
- Unlock user endpoint
- Admin user management
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


@pytest.fixture
def admin_token(test_admin):
    """Create an access token for the admin user."""
    return create_access_token(subject=test_admin.id, email=test_admin.email)


@pytest.fixture
def staff_token(test_staff):
    """Create an access token for the staff user."""
    return create_access_token(subject=test_staff.id, email=test_staff.email)


@pytest.fixture
def patron_token(test_patron):
    """Create an access token for the patron user."""
    return create_access_token(subject=test_patron.id, email=test_patron.email)


@pytest.mark.integration
class TestLockUserEndpoint:
    """Test the lock user endpoint."""

    async def test_lock_user_endpoint_success(
        self, client: TestClient, test_admin, test_patron, admin_token
    ):
        """Test that lock user endpoint works for admin."""
        response = await client.post(
            f"/api/v1/users/{test_patron.id}/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_patron.id
        assert data["locked_until"] is not None

    async def test_lock_user_prevents_login(
        self, client: TestClient, test_admin, admin_token, test_db
    ):
        """Test that a locked user cannot login."""
        # Create a user to lock
        from app.core.security import hash_password

        user = User(
            email="tolock@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="ToLock",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        # We need to commit synchronously in this context
        import asyncio

        await test_db.commit()
        await test_db.refresh(user)

        # Lock the user
        lock_response = await client.post(
            f"/api/v1/users/{user.id}/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert lock_response.status_code == status.HTTP_200_OK

        # Try to login as the locked user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "tolock@example.com", "password": "TestPassword123!"},
        )

        # Should be rejected with 423 Locked status
        assert login_response.status_code == status.HTTP_423_LOCKED

    async def test_lock_user_requires_admin(self, client: TestClient, test_patron, patron_token):
        """Test that non-admin users cannot lock accounts."""
        response = await client.post(
            f"/api/v1/users/{test_patron.id}/lock",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    async def test_cannot_lock_own_account(self, client: TestClient, test_admin, admin_token):
        """Test that admin cannot lock their own account."""
        response = await client.post(
            f"/api/v1/users/{test_admin.id}/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "own account" in response.json()["error"]["message"].lower()

    async def test_lock_nonexistent_user(self, client: TestClient, admin_token):
        """Test locking a non-existent user returns 404."""
        response = await client.post(
            "/api/v1/users/99999/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
class TestUnlockUserEndpoint:
    """Test the unlock user endpoint."""

    async def test_unlock_user_endpoint_success(
        self, client: TestClient, test_admin, test_patron, admin_token, test_db
    ):
        """Test that unlock user endpoint works for admin."""
        import asyncio

        # First lock the user
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(days=100)
        test_patron.failed_login_attempts = 5
        await test_db.commit()

        # Now unlock
        response = await client.post(
            f"/api/v1/users/{test_patron.id}/unlock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_patron.id
        assert data["locked_until"] is None

    async def test_unlock_user_allows_login(
        self, client: TestClient, test_admin, admin_token, test_db
    ):
        """Test that an unlocked user can login again."""
        from app.core.security import hash_password
        import asyncio

        # Create and lock a user
        user = User(
            email="tounlock@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="ToUnlock",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            locked_until=datetime.now(timezone.utc) + timedelta(days=100),
            failed_login_attempts=5,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Verify login fails while locked
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "tounlock@example.com", "password": "TestPassword123!"},
        )
        assert login_response.status_code == status.HTTP_423_LOCKED

        # Unlock the user
        unlock_response = await client.post(
            f"/api/v1/users/{user.id}/unlock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert unlock_response.status_code == status.HTTP_200_OK

        # Now login should succeed
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "tounlock@example.com", "password": "TestPassword123!"},
        )
        assert login_response.status_code == status.HTTP_200_OK

    async def test_unlock_user_requires_admin(self, client: TestClient, test_patron, patron_token):
        """Test that non-admin users cannot unlock accounts."""
        response = await client.post(
            f"/api/v1/users/{test_patron.id}/unlock",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    async def test_unlock_clears_failed_attempts(
        self, client: TestClient, test_admin, test_patron, admin_token, test_db
    ):
        """Test that unlocking also clears failed login attempts."""
        import asyncio

        # Set failed attempts
        test_patron.failed_login_attempts = 10
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(days=1)
        await test_db.commit()

        # Unlock
        response = await client.post(
            f"/api/v1/users/{test_patron.id}/unlock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK

        # Refresh from DB to verify
        await test_db.refresh(test_patron)
        assert test_patron.failed_login_attempts == 0
        assert test_patron.locked_until is None


@pytest.mark.integration
class TestUserListEndpoint:
    """Test the list users endpoint."""

    async def test_list_users_requires_admin(self, client: TestClient, patron_token):
        """Test that listing users requires admin role."""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    async def test_list_users_success(self, client: TestClient, admin_token):
        """Test that admin can list users."""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert isinstance(data["users"], list)

    async def test_list_users_with_filters(self, client: TestClient, admin_token):
        """Test that user list can be filtered by role."""
        response = await client.get(
            "/api/v1/users?role=patron",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All returned users should be patrons
        for user in data["users"]:
            assert user["role"] == "patron"


@pytest.mark.integration
class TestUserDeactivation:
    """Test user deactivation endpoint."""

    async def test_deactivate_user_success(
        self, client: TestClient, test_admin, test_patron, admin_token
    ):
        """Test that admin can deactivate a user."""
        response = await client.delete(
            f"/api/v1/users/{test_patron.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "deactivated" in response.json()["message"].lower()

    async def test_cannot_deactivate_own_account(self, client: TestClient, test_admin, admin_token):
        """Test that admin cannot deactivate their own account."""
        response = await client.delete(
            f"/api/v1/users/{test_admin.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
