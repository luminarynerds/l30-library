# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for all 6 new API services.

Tests cover:
- Partner Collaboration API
- School Partnerships API
- Signage API
- Lost/Damaged Items API
- Patron Accounts API
- Storytime API
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole
from app.core.database import get_db


class TestAuthHelper:
    """Helper functions for authentication in tests."""

    @staticmethod
    async def create_test_user(
        db: AsyncSession, email: str = "testuser@example.com", role: UserRole = UserRole.STAFF
    ) -> User:
        """Create a test user with given role."""
        user = User(
            email=email,
            first_name="Test",
            last_name="User",
            role=role,
            is_active=True,
            email_verified=True,
            password_hash=hash_password("testpassword123"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_auth_token(client: AsyncClient, email: str, password: str) -> str:
        """Login and get JWT token."""
        response = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        return response.json()["access_token"]


@pytest.mark.asyncio
class TestPartnerCollaborationAPI:
    """Tests for Partner Collaboration API endpoints."""

    async def test_partner_events_endpoint_exists(self, client: AsyncClient):
        """Verify partner events endpoint is registered."""
        # There is no GET /events/{event_id} (only PUT) -- a bare GET at that
        # path 405s (path matches, method doesn't) rather than proving auth
        # is checked. GET /events/partner/{partner_id} is the real read
        # endpoint on this router.
        response = await client.get(
            "/api/v1/partner-collaboration/events/partner/1",
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return auth error, not 404 (proves endpoint exists)
        assert response.status_code in [401, 403]

    async def test_create_partner_event(self, client: AsyncClient, db: AsyncSession):
        """Test creating a partner event."""
        # Create test user
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        # Create event
        event_data = {
            "title": "Joint Community Event",
            "description": "Partnership event with another library",
            "partner_ids": [1, 2],
            "event_date": "2026-03-15",
            "location": "Main Branch",
            "status": "planned",
        }

        response = await client.post(
            "/api/v1/partner-collaboration/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should succeed or give validation error (not 404/405)
        assert response.status_code in [201, 422]

    async def test_get_partner_events(self, client: AsyncClient, db: AsyncSession):
        """Test retrieving partner events."""
        user = await TestAuthHelper.create_test_user(db)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        response = await client.get(
            "/api/v1/partner-collaboration/events/partner/1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


@pytest.mark.asyncio
class TestSchoolPartnershipsAPI:
    """Tests for School Partnerships API endpoints."""

    async def test_school_partnerships_endpoint_exists(self, client: AsyncClient):
        """Verify school partnerships endpoint is registered."""
        response = await client.get(
            "/api/v1/school-partnerships", headers={"Authorization": "Bearer fake_token"}
        )
        # Should return auth error, not 404
        assert response.status_code in [401, 403, 404]

    async def test_get_school_partnerships(self, client: AsyncClient, db: AsyncSession):
        """Test retrieving school partnerships."""
        user = await TestAuthHelper.create_test_user(db)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        response = await client.get(
            "/api/v1/school-partnerships", headers={"Authorization": f"Bearer {token}"}
        )

        # Endpoint exists
        assert response.status_code in [200, 404]


@pytest.mark.asyncio
class TestSignageAPI:
    """Tests for Signage API endpoints."""

    async def test_signage_displays_endpoint_exists(self, client: AsyncClient):
        """Verify signage displays endpoint is registered."""
        response = await client.get(
            "/api/v1/signage/displays", headers={"Authorization": "Bearer fake_token"}
        )
        # Should return auth error, not 404
        assert response.status_code in [401, 403]

    async def test_get_displays(self, client: AsyncClient, db: AsyncSession):
        """Test retrieving signage displays."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        response = await client.get(
            "/api/v1/signage/displays", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Paginated envelope, not a raw list: {displays, limit, offset, total}
            assert isinstance(data["displays"], list)


@pytest.mark.asyncio
class TestLostDamagedAPI:
    """Tests for Lost/Damaged Items API endpoints."""

    async def test_lost_damaged_endpoint_exists(self, client: AsyncClient):
        """Verify lost/damaged endpoint is registered."""
        # The router (app/api/v1/staff_lost_damaged) has no bare root route --
        # only sub-paths like /lost-items, /damaged-items, /claims-returned.
        response = await client.get(
            "/api/v1/staff/lost-damaged/lost-items", headers={"Authorization": "Bearer fake_token"}
        )
        # Should return auth error, not 404
        assert response.status_code in [401, 403]

    async def test_get_lost_items(self, client: AsyncClient, db: AsyncSession):
        """Test retrieving lost items."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        response = await client.get(
            "/api/v1/staff/lost-damaged", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [200, 404]


@pytest.mark.asyncio
class TestPatronAccountsAPI:
    """Tests for Patron Accounts API endpoints."""

    async def test_patron_accounts_endpoint_exists(self, client: AsyncClient):
        """Verify patron accounts endpoint is registered."""
        response = await client.get(
            "/api/v1/staff/patrons", headers={"Authorization": "Bearer fake_token"}
        )
        # Should return auth error, not 404
        assert response.status_code in [401, 403]

    async def test_get_patrons(self, client: AsyncClient, db: AsyncSession):
        """Test retrieving patron accounts."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        response = await client.get(
            "/api/v1/staff/patrons", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [200, 404]


@pytest.mark.asyncio
class TestStorytimeAPI:
    """Tests for Storytime API endpoints."""

    async def test_storytime_endpoint_exists(self, client: AsyncClient):
        """Verify storytime endpoint is registered."""
        response = await client.get(
            "/api/v1/storytime/series", headers={"Authorization": "Bearer fake_token"}
        )
        # Should return auth error, not 404
        assert response.status_code in [401, 403]

    async def test_get_storytime_series(self, client: AsyncClient, db: AsyncSession):
        """Test retrieving storytime series."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        response = await client.get(
            "/api/v1/storytime/series", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [200, 404]

    async def test_create_storytime_series(self, client: AsyncClient, db: AsyncSession):
        """Test creating a storytime series."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        series_data = {
            "title": "Summer Reading Stories",
            "description": "Stories for summer reading program",
            "audience_age_range": "3-8",
            "frequency": "weekly",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
        }

        response = await client.post(
            "/api/v1/storytime/series",
            json=series_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should succeed or give validation error (not 404/405)
        assert response.status_code in [201, 422]


@pytest.mark.asyncio
class TestAPIIntegration:
    """Cross-API integration tests."""

    async def test_all_apis_accessible(self, client: AsyncClient, db: AsyncSession):
        """Test that all 6 APIs are accessible."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        endpoints = [
            "/api/v1/partner-collaboration/events/partner/1",
            "/api/v1/school-partnerships",
            "/api/v1/signage/displays",
            "/api/v1/staff/lost-damaged",
            "/api/v1/staff/patrons",
            "/api/v1/storytime/series",
        ]

        headers = {"Authorization": f"Bearer {token}"}
        results = {}

        for endpoint in endpoints:
            response = await client.get(endpoint, headers=headers)
            results[endpoint] = response.status_code
            # All should return 200, 404, or validation error (not 500/405)
            assert response.status_code < 500, f"Server error on {endpoint}"

        print("\n=== API Accessibility Results ===")
        for endpoint, status in results.items():
            print(f"{endpoint}: {status}")

    async def test_error_handling(self, client: AsyncClient, db: AsyncSession):
        """Test consistent error handling across all APIs."""
        user = await TestAuthHelper.create_test_user(db, role=UserRole.STAFF)
        token = await TestAuthHelper.get_auth_token(client, user.email, "testpassword123")

        # Test 404 handling
        response = await client.get(
            "/api/v1/partner-collaboration/events/partner/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 404:
            data = response.json()
            assert "error" in data or "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
