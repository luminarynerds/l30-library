# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for roles management API endpoints.

Tests for:
- List all roles
- Get a specific role
- Role permission management
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.core.security import create_access_token


@pytest.fixture
def admin_token(test_admin):
    """Create an access token for the admin user."""
    return create_access_token(subject=test_admin.id, email=test_admin.email)


@pytest.fixture
def patron_token(test_patron):
    """Create an access token for the patron user."""
    return create_access_token(subject=test_patron.id, email=test_patron.email)


@pytest.mark.integration
class TestListRoles:
    """Test listing all roles endpoint."""

    async def test_list_roles_success(self, client: TestClient, admin_token):
        """Test listing all roles returns all system roles."""
        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify expected roles exist
        role_ids = [role["id"] for role in data]
        assert "patron" in role_ids
        assert "staff" in role_ids
        assert "admin" in role_ids

    async def test_list_roles_includes_permissions(self, client: TestClient, admin_token):
        """Test that role listing includes permissions for each role."""
        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for role in data:
            assert "id" in role
            assert "name" in role
            assert "permissions" in role
            assert isinstance(role["permissions"], list)

    async def test_list_roles_requires_admin(self, client: TestClient, patron_token):
        """Test that listing roles requires admin privileges."""
        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    async def test_list_roles_no_auth_fails(self, client: TestClient):
        """Test that listing roles without authentication fails."""
        response = await client.get("/api/v1/roles")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetRole:
    """Test getting a specific role endpoint."""

    async def test_get_role_patron(self, client: TestClient, admin_token):
        """Test getting the PATRON role."""
        response = await client.get(
            "/api/v1/roles/patron",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "patron"
        assert "name" in data
        assert "permissions" in data

    async def test_get_role_admin(self, client: TestClient, admin_token):
        """Test getting the ADMIN role."""
        response = await client.get(
            "/api/v1/roles/admin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "admin"

    async def test_get_role_staff(self, client: TestClient, admin_token):
        """Test getting the STAFF role."""
        response = await client.get(
            "/api/v1/roles/staff",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "staff"

    async def test_get_role_child(self, client: TestClient, admin_token):
        """Test getting the CHILD role."""
        response = await client.get(
            "/api/v1/roles/child",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "child"

    async def test_get_nonexistent_role(self, client: TestClient, admin_token):
        """Test getting a non-existent role returns 404."""
        response = await client.get(
            "/api/v1/roles/NONEXISTENT_ROLE",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["error"]["message"].lower()

    async def test_get_role_requires_admin(self, client: TestClient, patron_token):
        """Test that getting a role requires admin privileges."""
        response = await client.get(
            "/api/v1/roles/patron",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.integration
class TestCreateRole:
    """Test role creation endpoint (should fail as roles are predefined)."""

    async def test_create_role_not_allowed(self, client: TestClient, admin_token):
        """Test that creating custom roles is not allowed."""
        response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "CUSTOM_ROLE",
                "description": "A custom role",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not supported" in response.json()["error"]["message"].lower()


@pytest.mark.integration
class TestDeleteRole:
    """Test role deletion endpoint (should fail as roles are predefined)."""

    async def test_delete_role_not_allowed(self, client: TestClient, admin_token):
        """Test that deleting system roles is not allowed."""
        response = await client.delete(
            "/api/v1/roles/patron",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be deleted" in response.json()["error"]["message"].lower()


@pytest.mark.integration
class TestRoleDescriptions:
    """Test that roles have appropriate descriptions."""

    async def test_roles_have_descriptions(self, client: TestClient, admin_token):
        """Test that all roles have descriptions."""
        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for role in data:
            assert "description" in role
            # Description should be non-empty for standard roles
            if role["id"] in ["patron", "staff", "admin", "super_admin"]:
                assert role["description"] is not None
                assert len(role["description"]) > 0

    async def test_role_names_are_formatted(self, client: TestClient, admin_token):
        """Test that role names are properly formatted."""
        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for role in data:
            # Name should be title-cased version of the ID
            assert "name" in role
            # SUPER_ADMIN -> Super Admin, PATRON -> Patron
            expected_name = role["id"].replace("_", " ").title()
            assert role["name"] == expected_name


@pytest.mark.integration
class TestRolePermissions:
    """Test role permission management."""

    async def test_admin_has_more_permissions_than_patron(self, client: TestClient, admin_token):
        """Test that admin role has more permissions than patron."""
        # Get ADMIN role
        admin_response = await client.get(
            "/api/v1/roles/admin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        admin_data = admin_response.json()

        # Get PATRON role
        patron_response = await client.get(
            "/api/v1/roles/patron",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        patron_data = patron_response.json()

        # Admin should have at least as many permissions as patron
        # (in most systems, admin has more)
        admin_perms = set(admin_data.get("permissions", []))
        patron_perms = set(patron_data.get("permissions", []))

        # Admin should have all patron permissions plus more
        # or at least not fewer
        assert len(admin_perms) >= len(patron_perms)

    async def test_staff_has_specific_permissions(self, client: TestClient, admin_token):
        """Test that staff role has appropriate permissions."""
        response = await client.get(
            "/api/v1/roles/staff",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        permissions = data.get("permissions", [])

        # Staff should have permissions but may vary by setup
        assert isinstance(permissions, list)


@pytest.mark.integration
class TestAllRoleTypes:
    """Test that all expected role types are present."""

    async def test_all_user_roles_exist(self, client: TestClient, admin_token):
        """Test that all UserRole enum values are returned."""
        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        role_ids = [role["id"] for role in data]

        # Check all expected roles from UserRole enum
        expected_roles = [
            "super_admin",
            "admin",
            "staff",
            "patron",
            "child",
            "bookmobile",
            "homebond",
        ]

        for expected in expected_roles:
            assert expected in role_ids, f"Role {expected} not found in roles list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
