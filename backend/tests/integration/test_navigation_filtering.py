# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for role-based navigation filtering.

Tests the GET /api/v1/navigation endpoint and navigation service.
Location: tests/integration/test_navigation_filtering.py
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.core.security import create_access_token, hash_password


@pytest.fixture
async def staff_user(test_db):
    """Create a staff user for testing."""
    user = User(
        email="staff@example.com",
        password_hash=hash_password("StaffPass123!"),
        first_name="Staff",
        last_name="Member",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db):
    """Create an admin user for testing."""
    user = User(
        email="admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def super_admin_user(test_db):
    """Create a super admin user for testing."""
    user = User(
        email="superadmin@example.com",
        password_hash=hash_password("SuperPass123!"),
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.mark.integration
class TestNavigationEndpoint:
    """Integration tests for the navigation endpoint."""

    @pytest.mark.asyncio
    async def test_staff_user_navigation(self, client: TestClient, staff_user: User):
        """Test that staff users see only staff navigation items."""
        token = create_access_token(subject=staff_user.id, email=staff_user.email)
        response = await client.get(
            "/api/v1/navigation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should see staff operations
        assert data["canAccessStaff"] is True
        assert data["canAccessAdmin"] is False
        assert data["role"] == "staff"

        # Should have staff sections
        section_ids = [s["id"] for s in data["sections"]]
        assert "staff_main" in section_ids or "staff_tools" in section_ids

        # Should NOT have admin sections
        _ = [s["id"] for s in data["sections"] if "admin" in s["id"]]
        assert "admin_settings" not in section_ids
        assert "super_admin_system" not in section_ids

    @pytest.mark.asyncio
    async def test_admin_user_navigation(self, client: TestClient, admin_user: User):
        """Test that admin users see staff and admin navigation items."""
        token = create_access_token(subject=admin_user.id, email=admin_user.email)
        response = await client.get(
            "/api/v1/navigation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should see both staff and admin
        assert data["canAccessStaff"] is True
        assert data["canAccessAdmin"] is True
        assert data["role"] == "admin"

        # Should have both staff and admin sections
        section_ids = [s["id"] for s in data["sections"]]
        assert "staff_main" in section_ids or "staff_tools" in section_ids
        assert "admin_settings" in section_ids

    @pytest.mark.asyncio
    async def test_super_admin_user_navigation(self, client: TestClient, super_admin_user: User):
        """Test that super admin users see all navigation items including system admin."""
        token = create_access_token(subject=super_admin_user.id, email=super_admin_user.email)
        response = await client.get(
            "/api/v1/navigation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should see everything
        assert data["canAccessStaff"] is True
        assert data["canAccessAdmin"] is True
        assert data["role"] == "super_admin"

        # Should have all sections
        section_ids = [s["id"] for s in data["sections"]]
        assert "staff_main" in section_ids or "staff_tools" in section_ids
        assert "admin_settings" in section_ids
        assert "super_admin_system" in section_ids

    @pytest.mark.asyncio
    async def test_patron_user_navigation(self, client: TestClient, test_patron: User):
        """Test that patron users cannot see staff or admin items."""
        token = create_access_token(subject=test_patron.id, email=test_patron.email)
        response = await client.get(
            "/api/v1/navigation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should NOT see staff or admin
        assert data["canAccessStaff"] is False
        assert data["canAccessAdmin"] is False
        assert data["role"] == "patron"

        # Should have empty sections
        assert data["sections"] == []

    @pytest.mark.asyncio
    async def test_navigation_requires_auth(self, client: TestClient):
        """Test that navigation endpoint requires authentication."""
        response = await client.get("/api/v1/navigation")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_navigation_has_required_fields(self, client: TestClient, staff_user: User):
        """Test that navigation response has all required fields."""
        token = create_access_token(subject=staff_user.id, email=staff_user.email)
        response = await client.get(
            "/api/v1/navigation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check top-level fields
        assert "sections" in data
        assert "role" in data
        assert "canAccessAdmin" in data
        assert "canAccessStaff" in data

        # Check section fields
        for section in data["sections"]:
            assert "id" in section
            assert "label" in section
            assert "items" in section

            # Check item fields
            for item in section["items"]:
                assert "id" in item
                assert "label" in item
                assert "path" in item
                assert "requiresAuth" in item
                assert "roles" in item

    @pytest.mark.asyncio
    async def test_navigation_items_have_staff_role(self, client: TestClient, staff_user: User):
        """Test that staff navigation items include STAFF in allowed roles."""
        token = create_access_token(subject=staff_user.id, email=staff_user.email)
        response = await client.get(
            "/api/v1/navigation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Collect all items
        all_items = []
        for section in data["sections"]:
            all_items.extend(section["items"])

        # At least some items should require auth
        auth_required_items = [i for i in all_items if i["requiresAuth"]]
        assert len(auth_required_items) > 0

        # Staff items should allow STAFF role
        for item in auth_required_items:
            if "staff" in item["id"].lower():
                assert "STAFF" in item["roles"] or "ADMIN" in item["roles"]


@pytest.mark.integration
class TestNavigationAccessCheckEndpoint:
    """Integration tests for the access check endpoint."""

    @pytest.mark.asyncio
    async def test_staff_user_can_access_staff_pages(self, client: TestClient, staff_user: User):
        """Test that staff users can access staff pages."""
        token = create_access_token(subject=staff_user.id, email=staff_user.email)
        response = await client.get(
            "/api/v1/navigation/check-access/staff/circulation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["allowed"] is True
        assert data["canAccessStaff"] is True

    @pytest.mark.asyncio
    async def test_staff_user_cannot_access_admin_pages(self, client: TestClient, staff_user: User):
        """Test that staff users cannot access admin pages."""
        token = create_access_token(subject=staff_user.id, email=staff_user.email)
        response = await client.get(
            "/api/v1/navigation/check-access/admin/features",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["allowed"] is False
        assert data["canAccessAdmin"] is False

    @pytest.mark.asyncio
    async def test_admin_user_can_access_admin_pages(self, client: TestClient, admin_user: User):
        """Test that admin users can access admin pages."""
        token = create_access_token(subject=admin_user.id, email=admin_user.email)
        response = await client.get(
            "/api/v1/navigation/check-access/admin/features",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["allowed"] is True
        assert data["canAccessAdmin"] is True

    @pytest.mark.asyncio
    async def test_admin_user_can_access_staff_pages(self, client: TestClient, admin_user: User):
        """Test that admin users can also access staff pages."""
        token = create_access_token(subject=admin_user.id, email=admin_user.email)
        response = await client.get(
            "/api/v1/navigation/check-access/staff/circulation",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["allowed"] is True
        assert data["canAccessStaff"] is True

    @pytest.mark.asyncio
    async def test_access_check_requires_auth(self, client: TestClient):
        """Test that access check requires authentication."""
        response = await client.get("/api/v1/navigation/check-access/staff/circulation")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_access_check_returns_required_flags(self, client: TestClient, staff_user: User):
        """Test that access check returns required flags."""
        token = create_access_token(subject=staff_user.id, email=staff_user.email)
        response = await client.get(
            "/api/v1/navigation/check-access/admin/features",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "allowed" in data
        assert "role" in data
        assert "path" in data
        assert "canAccessStaff" in data
        assert "canAccessAdmin" in data
        assert "requiredAdmin" in data
        assert "requiredStaff" in data
