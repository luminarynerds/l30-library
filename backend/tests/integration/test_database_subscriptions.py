# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for database subscription API endpoints.

Tests cover:
- Proxy configuration CRUD
- Vendor management
- Database subscription CRUD
- Public A-Z list
- Access logging
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import status

from app.core.security import create_access_token


@pytest.fixture
def admin_auth_header(test_admin):
    """Bearer auth header for the admin fixture user."""
    token = create_access_token(subject=str(test_admin.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_auth_header(test_staff):
    """Bearer auth header for the staff fixture user."""
    token = create_access_token(subject=str(test_staff.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patron_auth_header(test_patron):
    """Bearer auth header for the patron fixture user."""
    token = create_access_token(subject=str(test_patron.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_header(test_admin):
    from app.core.security import create_access_token

    token = create_access_token(subject=test_admin.id, email=test_admin.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_auth_header(test_staff):
    from app.core.security import create_access_token

    token = create_access_token(subject=test_staff.id, email=test_staff.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patron_auth_header(test_patron):
    from app.core.security import create_access_token

    token = create_access_token(subject=test_patron.id, email=test_patron.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def proxy_config_data():
    """Sample proxy configuration data."""
    return {
        "name": "Test EZproxy",
        "proxy_type": "ezproxy",
        "ezproxy_base_url": "https://proxy.testlibrary.org",
        "ezproxy_login_path": "/login",
        "ezproxy_url_param": "url",
        "onsite_ip_ranges": ["192.168.1.0/24"],
        "requires_library_card": True,
        "allows_guest_access": False,
        "is_active": True,
        "is_default": True,
    }


@pytest.fixture
def vendor_data():
    """Sample vendor data."""
    return {
        "name": "Test Vendor Inc.",
        "short_name": "TestVendor",
        "website": "https://www.testvendor.com",
        "support_email": "support@testvendor.com",
        "support_phone": "1-800-555-0100",
        "account_rep_name": "John Smith",
        "account_rep_email": "jsmith@testvendor.com",
    }


@pytest.fixture
def subscription_data():
    """Sample subscription data."""
    today = date.today()
    return {
        "name": "Test Database",
        "short_name": "TestDB",
        "description": "A test database for unit testing",
        "category": "general_reference",
        "subjects": ["Testing", "QA"],
        "access_url": "https://testdb.example.com",
        "subscription_start": today.isoformat(),
        "subscription_end": (today + timedelta(days=365)).isoformat(),
        "annual_cost": "1500.00",
        "requires_proxy": True,
        "is_active": True,
        "is_featured": False,
    }


@pytest.mark.integration
class TestProxyConfigurationEndpoints:
    """Tests for proxy configuration management."""

    async def test_create_proxy_config_as_admin(self, client, admin_auth_header, proxy_config_data):
        """Admin should be able to create proxy configuration."""
        response = await client.post(
            "/api/v1/databases/proxy-configs",
            json=proxy_config_data,
            headers=admin_auth_header,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == proxy_config_data["name"]
        assert data["proxy_type"] == "ezproxy"
        assert data["is_default"] is True

    async def test_create_proxy_config_as_staff_forbidden(
        self, client, staff_auth_header, proxy_config_data
    ):
        """Staff should not be able to create proxy configuration."""
        response = await client.post(
            "/api/v1/databases/proxy-configs",
            json=proxy_config_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_list_proxy_configs(self, client, staff_auth_header):
        """Staff should be able to list proxy configurations."""
        response = await client.get(
            "/api/v1/databases/proxy-configs",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    async def test_list_proxy_configs_unauthenticated(self, client):
        """Unauthenticated users should not access proxy configs."""
        response = await client.get("/api/v1/databases/proxy-configs")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestVendorEndpoints:
    """Tests for vendor management."""

    async def test_create_vendor_as_staff(self, client, staff_auth_header, vendor_data):
        """Staff should be able to create vendors."""
        response = await client.post(
            "/api/v1/databases/vendors",
            json=vendor_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == vendor_data["name"]
        assert data["short_name"] == vendor_data["short_name"]

    async def test_create_duplicate_vendor(self, client, staff_auth_header, vendor_data):
        """Creating a duplicate vendor should fail."""
        # Create first vendor
        await client.post(
            "/api/v1/databases/vendors",
            json=vendor_data,
            headers=staff_auth_header,
        )
        # Try to create duplicate
        response = await client.post(
            "/api/v1/databases/vendors",
            json=vendor_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_list_vendors(self, client, staff_auth_header):
        """Staff should be able to list vendors."""
        response = await client.get(
            "/api/v1/databases/vendors",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    async def test_update_vendor(self, client, staff_auth_header, vendor_data):
        """Staff should be able to update vendors."""
        # Create vendor
        create_response = await client.post(
            "/api/v1/databases/vendors",
            json=vendor_data,
            headers=staff_auth_header,
        )
        vendor_id = create_response.json()["id"]

        # Update vendor
        update_data = {"support_phone": "1-800-555-0200"}
        response = await client.put(
            f"/api/v1/databases/vendors/{vendor_id}",
            json=update_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["support_phone"] == "1-800-555-0200"

    async def test_delete_vendor_as_admin(
        self, client, admin_auth_header, staff_auth_header, vendor_data
    ):
        """Only admin should be able to delete vendors."""
        # Create vendor as staff
        create_response = await client.post(
            "/api/v1/databases/vendors",
            json=vendor_data,
            headers=staff_auth_header,
        )
        vendor_id = create_response.json()["id"]

        # Delete as admin
        response = await client.delete(
            f"/api/v1/databases/vendors/{vendor_id}",
            headers=admin_auth_header,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
class TestSubscriptionEndpoints:
    """Tests for database subscription management."""

    async def test_create_subscription(self, client, staff_auth_header, subscription_data):
        """Staff should be able to create subscriptions."""
        response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == subscription_data["name"]
        assert data["status"] == "active"

    async def test_list_subscriptions(self, client, staff_auth_header):
        """Staff should be able to list subscriptions."""
        response = await client.get(
            "/api/v1/databases/subscriptions",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    async def test_list_subscriptions_with_filters(
        self, client, staff_auth_header, subscription_data
    ):
        """Staff should be able to filter subscriptions."""
        # Create subscription
        await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )

        # Filter by category
        response = await client.get(
            "/api/v1/databases/subscriptions?category=general_reference",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_get_subscription(self, client, staff_auth_header, subscription_data):
        """Staff should be able to get subscription details."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Get subscription
        response = await client.get(
            f"/api/v1/databases/subscriptions/{subscription_id}",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == subscription_data["name"]

    async def test_update_subscription(self, client, staff_auth_header, subscription_data):
        """Staff should be able to update subscriptions."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Update subscription
        update_data = {"is_featured": True, "display_order": 5}
        response = await client.put(
            f"/api/v1/databases/subscriptions/{subscription_id}",
            json=update_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_featured"] is True
        assert response.json()["display_order"] == 5

    async def test_delete_subscription_as_admin(
        self, client, admin_auth_header, staff_auth_header, subscription_data
    ):
        """Only admin should be able to delete subscriptions."""
        # Create as staff
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Delete as admin
        response = await client.delete(
            f"/api/v1/databases/subscriptions/{subscription_id}",
            headers=admin_auth_header,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_subscription_as_staff_forbidden(
        self, client, staff_auth_header, subscription_data
    ):
        """Staff should not be able to delete subscriptions."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Try to delete as staff
        response = await client.delete(
            f"/api/v1/databases/subscriptions/{subscription_id}",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestPublicDatabaseList:
    """Tests for public A-Z database list."""

    async def test_public_list_unauthenticated(self, client):
        """Public list should be accessible without authentication."""
        response = await client.get("/api/v1/databases/public/list")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "databases" in data
        assert "total" in data
        assert "categories" in data

    async def test_public_list_filters_inactive(self, client, staff_auth_header, subscription_data):
        """Public list should only show active subscriptions."""
        # Create inactive subscription
        subscription_data["is_active"] = False
        subscription_data["name"] = "Inactive Database"
        await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )

        # Get public list
        response = await client.get("/api/v1/databases/public/list")
        data = response.json()

        # Inactive subscription should not appear
        names = [db["name"] for db in data["databases"]]
        assert "Inactive Database" not in names

    async def test_public_list_filter_by_category(self, client):
        """Public list should filter by category."""
        response = await client.get("/api/v1/databases/public/list?category=academic")
        assert response.status_code == status.HTTP_200_OK

    async def test_public_list_featured_only(self, client):
        """Public list should filter featured databases."""
        response = await client.get("/api/v1/databases/public/list?featured_only=true")
        assert response.status_code == status.HTTP_200_OK

    async def test_public_list_search(self, client, staff_auth_header, subscription_data):
        """Public list should support search."""
        # Create subscription with specific name
        subscription_data["name"] = "Unique Searchable Database"
        await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )

        # Search for it
        response = await client.get("/api/v1/databases/public/list?search=Unique")
        assert response.status_code == status.HTTP_200_OK

    async def test_get_public_database(self, client, staff_auth_header, subscription_data):
        """Should be able to get individual database public info."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Get public info
        response = await client.get(f"/api/v1/databases/public/{subscription_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "proxy_url" in data
        assert "name" in data
        # Should not include internal fields
        assert "annual_cost" not in data
        assert "internal_notes" not in data


@pytest.mark.integration
class TestAccessLogging:
    """Tests for database access logging."""

    async def test_log_access_authenticated(
        self, client, patron_auth_header, staff_auth_header, subscription_data
    ):
        """Authenticated users can log access and get proxy URL."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Log access
        response = await client.post(
            f"/api/v1/databases/access/{subscription_id}",
            headers=patron_auth_header,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "url" in data
        assert "proxied" in data

    async def test_log_access_unauthenticated(self, client, staff_auth_header, subscription_data):
        """Unauthenticated users can also log access."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Log access without auth
        response = await client.post(f"/api/v1/databases/access/{subscription_id}")
        assert response.status_code == status.HTTP_201_CREATED

    async def test_log_access_expired_subscription(self, client, staff_auth_header):
        """Access to expired subscription should be denied."""
        today = date.today()
        expired_data = {
            "name": "Expired Database",
            "access_url": "https://expired.example.com",
            "subscription_start": (today - timedelta(days=400)).isoformat(),
            "subscription_end": (today - timedelta(days=30)).isoformat(),
            "is_active": True,
        }

        # Create expired subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=expired_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Try to access
        response = await client.post(f"/api/v1/databases/access/{subscription_id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestUsageStatistics:
    """Tests for usage statistics."""

    async def test_add_usage_stats(self, client, staff_auth_header, subscription_data):
        """Staff should be able to add usage statistics."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Add usage stats
        stats_data = {
            "stat_year": 2026,
            "stat_month": 1,
            "total_item_requests": 150,
            "unique_item_requests": 75,
            "total_sessions": 50,
            "unique_users": 30,
            "data_source": "manual",
        }

        response = await client.post(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage",
            json=stats_data,
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total_item_requests"] == 150

    async def test_upsert_usage_stats_idempotent(
        self, client, staff_auth_header, subscription_data
    ):
        """Re-posting the same period overwrites, not duplicates."""
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        first = await client.post(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage",
            json={
                "stat_year": 2026,
                "stat_month": 2,
                "total_item_requests": 100,
                "searches_regular": 50,
                "data_source": "manual",
            },
            headers=staff_auth_header,
        )
        assert first.status_code == status.HTTP_200_OK
        first_id = first.json()["id"]

        second = await client.post(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage",
            json={
                "stat_year": 2026,
                "stat_month": 2,
                "total_item_requests": 200,
                "searches_regular": 75,
                "data_source": "manual",
            },
            headers=staff_auth_header,
        )
        assert second.status_code == status.HTTP_200_OK
        assert second.json()["id"] == first_id
        assert second.json()["total_item_requests"] == 200

        all_rows = await client.get(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage?year=2026",
            headers=staff_auth_header,
        )
        feb_rows = [r for r in all_rows.json() if r["stat_month"] == 2]
        assert len(feb_rows) == 1

    async def test_put_usage_stats_partial_update(
        self, client, staff_auth_header, subscription_data
    ):
        """PUT updates only the supplied fields."""
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        created = (
            await client.post(
                f"/api/v1/databases/subscriptions/{subscription_id}/usage",
                json={
                    "stat_year": 2026,
                    "stat_month": 3,
                    "total_item_requests": 100,
                    "searches_regular": 50,
                    "data_source": "manual",
                },
                headers=staff_auth_header,
            )
        ).json()

        updated = await client.put(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage/{created['id']}",
            json={"total_item_requests": 999},
            headers=staff_auth_header,
        )
        assert updated.status_code == status.HTTP_200_OK
        assert updated.json()["total_item_requests"] == 999
        assert updated.json()["searches_regular"] == 50

    async def test_delete_usage_stats(self, client, staff_auth_header, subscription_data):
        """DELETE removes the row."""
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        created = (
            await client.post(
                f"/api/v1/databases/subscriptions/{subscription_id}/usage",
                json={
                    "stat_year": 2026,
                    "stat_month": 4,
                    "total_item_requests": 50,
                    "data_source": "manual",
                },
                headers=staff_auth_header,
            )
        ).json()

        deleted = await client.delete(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage/{created['id']}",
            headers=staff_auth_header,
        )
        assert deleted.status_code == status.HTTP_204_NO_CONTENT

    async def test_usage_report_json_preview(self, client, staff_auth_header, subscription_data):
        """JSON preview aggregates monthly stats per subscription."""
        sub_id = (
            await client.post(
                "/api/v1/databases/subscriptions",
                json=subscription_data,
                headers=staff_auth_header,
            )
        ).json()["id"]

        for month, requests in [(1, 100), (2, 50), (3, 75)]:
            await client.post(
                f"/api/v1/databases/subscriptions/{sub_id}/usage",
                json={
                    "stat_year": 2026,
                    "stat_month": month,
                    "total_item_requests": requests,
                    "searches_regular": requests // 2,
                    "data_source": "manual",
                },
                headers=staff_auth_header,
            )

        report = await client.get(
            "/api/v1/databases/reports/usage?year=2026",
            headers=staff_auth_header,
        )
        assert report.status_code == status.HTTP_200_OK
        body = report.json()
        assert body["year"] == 2026
        assert len(body["rows"]) >= 1
        our_row = next(r for r in body["rows"] if r["subscription_id"] == sub_id)
        assert our_row["total_item_requests"] == 225  # 100 + 50 + 75
        assert our_row["searches_regular"] == 112  # 50 + 25 + 37

    async def test_usage_report_tsv_download(self, client, staff_auth_header, subscription_data):
        """TSV download contains Report_Header and DR_D1 columns."""
        sub_id = (
            await client.post(
                "/api/v1/databases/subscriptions",
                json=subscription_data,
                headers=staff_auth_header,
            )
        ).json()["id"]
        await client.post(
            f"/api/v1/databases/subscriptions/{sub_id}/usage",
            json={
                "stat_year": 2026,
                "stat_month": 1,
                "total_item_requests": 42,
                "data_source": "manual",
            },
            headers=staff_auth_header,
        )

        report = await client.get(
            "/api/v1/databases/reports/usage?year=2026&format=tsv",
            headers=staff_auth_header,
        )
        assert report.status_code == status.HTTP_200_OK
        body = report.text
        assert "Report_ID\tDR_D1" in body
        assert "Release\t5" in body
        assert "Database\tPublisher\tPlatform" in body

    async def test_get_usage_stats(self, client, staff_auth_header, subscription_data):
        """Staff should be able to retrieve usage statistics."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/databases/subscriptions",
            json=subscription_data,
            headers=staff_auth_header,
        )
        subscription_id = create_response.json()["id"]

        # Get usage stats
        response = await client.get(
            f"/api/v1/databases/subscriptions/{subscription_id}/usage",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)


@pytest.mark.integration
class TestDashboard:
    """Tests for subscription management dashboard."""

    async def test_get_dashboard_as_staff(self, client, staff_auth_header):
        """Staff should be able to access the dashboard."""
        response = await client.get(
            "/api/v1/databases/dashboard",
            headers=staff_auth_header,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_active" in data
        assert "total_expired" in data
        assert "total_expiring_soon" in data
        assert "total_annual_cost" in data
        assert "expiring_alerts" in data

    async def test_get_dashboard_as_patron_forbidden(self, client, patron_auth_header):
        """Patrons should not access the dashboard."""
        response = await client.get(
            "/api/v1/databases/dashboard",
            headers=patron_auth_header,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
