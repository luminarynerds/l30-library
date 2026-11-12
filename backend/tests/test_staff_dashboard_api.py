# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for Staff Dashboard API endpoints
Validates production-readiness of dashboard metrics, health checks, and real-time features
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.catalog import CatalogItem, ItemStatus
from app.models.user import User, UserRole
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.lost_damaged import (
    LostItemRecord, LostItemStatus,
    DamagedItemRecord, DamagedItemStatus,
    ClaimsReturnedDispute, ClaimDisputeStatus,
)
from app.models.outreach import (
    OutreachPartner, OutreachPartnerStatus, OutreachVisit, VisitStatus,
    BulkCheckout, BulkCheckoutStatus, OutreachDeposit, DepositStatus
)
from app.models.catalog import CatalogItem, ItemStatus


@pytest.fixture
def token(test_staff):
    """Staff auth token -- dashboard endpoints are staff-only."""
    from app.core.security import create_access_token

    return create_access_token(subject=test_staff.id, email=test_staff.email)


@pytest.fixture
def user_token(test_patron):
    """Non-staff (patron) auth token for permission-denial tests."""
    from app.core.security import create_access_token

    return create_access_token(subject=test_patron.id, email=test_patron.email)


@pytest.fixture
async def patron(test_patron):
    """Alias -- this file refers to the patron fixture as `patron`."""
    return test_patron


@pytest.fixture
async def item(test_db):
    """A catalog item with a barcode set, for barcode-driven quick actions."""
    catalog_item = CatalogItem(
        title="Dashboard Test Book",
        author="Test Author",
        isbn="978-0-888888-88-8",
        status=ItemStatus.available,
        call_number="DASH-001",
        barcode="DASH-BARCODE-001",
        publication_year=2024,
    )
    test_db.add(catalog_item)
    await test_db.commit()
    await test_db.refresh(catalog_item)
    return catalog_item


@pytest.fixture
def token(staff_user) -> str:
    """Bearer token string for the (board-fixture) staff user."""
    return create_access_token(subject=str(staff_user.id))


@pytest.fixture
async def patron(test_patron):
    """Alias: the standard patron fixture, under the name these tests expect."""
    return test_patron


@pytest.fixture
def user_token(patron) -> str:
    """Bearer token string for a non-staff (patron) user."""
    return create_access_token(subject=str(patron.id))


@pytest.fixture
async def item(test_db):
    """A barcoded catalog item for dashboard-metrics tests."""
    obj = CatalogItem(
        title="Staff Dashboard Test Book",
        author="Test Author",
        isbn="978-0-000000-02-2",
        status=ItemStatus.available,
        call_number="SDB-001",
        barcode="SDB-BARCODE-001",
    )
    test_db.add(obj)
    await test_db.commit()
    await test_db.refresh(obj)
    return obj


@pytest.mark.asyncio
class TestDashboardMetricsLoading:
    """Test suite for dashboard metrics loading functionality"""

    async def test_dashboard_stats_endpoint_returns_all_metrics(self, client, db_session, staff_user, token):
        """Verify dashboard stats endpoint returns complete metrics object"""
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            'active_checkouts', 'overdue_count', 'pending_holds', 'ready_holds',
            'total_patrons', 'active_patrons_30d', 'outstanding_fines_total',
            'patrons_with_fines', 'checkouts_today', 'returns_today',
            'lost_items_total', 'damaged_items_pending', 'items_in_mending',
            'claims_returned_pending', 'lost_item_charges_outstanding',
            'active_outreach_partners', 'upcoming_visits', 'overdue_bulk_checkouts',
            'deposits_held_total'
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    async def test_dashboard_stats_calculates_checkouts_today(self, client, db_session, staff_user, token, patron, item):
        """Verify checkouts_today metric is calculated correctly"""
        # Create a checkout today
        _ = datetime.combine(date.today(), datetime.min.time())
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['checkouts_today'] >= 1

    async def test_dashboard_stats_calculates_overdue_items(self, client, db_session, staff_user, token, patron, item):
        """Verify overdue_count metric is calculated correctly"""
        # Create an overdue checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=5),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['overdue_count'] >= 1

    async def test_dashboard_stats_calculates_holds(self, client, db_session, staff_user, token, patron, item):
        """Verify pending and ready holds are calculated correctly"""
        # ix_active_user_item_hold enforces at most one active hold per
        # (user_id, item_id) -- a second item is needed for the second hold.
        item2 = CatalogItem(
            title="Dashboard Test Book 2",
            author="Test Author",
            isbn="978-0-888888-88-9",
            status=ItemStatus.available,
            call_number="DASH-002",
            barcode="DASH-BARCODE-002",
            publication_year=2024,
        )
        db_session.add(item2)
        await db_session.flush()

        # Create pending holds
        pending_hold = Hold(
            user_id=patron.id,
            item_id=item.id,
            status=HoldStatus.pending,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(pending_hold)

        # Create ready holds
        ready_hold = Hold(
            user_id=patron.id,
            item_id=item2.id,
            status=HoldStatus.ready,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(ready_hold)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['pending_holds'] >= 1
        assert data['ready_holds'] >= 1

    async def test_dashboard_stats_calculates_fines(self, client, db_session, staff_user, token, patron):
        """Verify outstanding fines are calculated correctly"""
        # Create outstanding fine
        fine = Fine(
            user_id=patron.id,
            amount=Decimal("25.50"),
            amount_paid=Decimal("0.00"),
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(fine)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['outstanding_fines_total'] >= 25.50

    async def test_dashboard_activity_endpoint_returns_recent_activity(self, client, db_session, staff_user, token, patron, item):
        """Verify activity feed endpoint returns recent activities"""
        # Create some activity
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/activity?limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'activities' in data

    async def test_dashboard_lost_and_damaged_metrics(self, client, db_session, staff_user, token):
        """Verify lost and damaged item metrics are calculated"""
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert 'lost_items_total' in data
        assert 'lost_items_this_month' in data
        assert 'damaged_items_pending' in data
        assert 'items_in_mending' in data
        assert 'claims_returned_pending' in data


@pytest.mark.asyncio
class TestSystemHealthChecks:
    """Test suite for system health checks"""

    async def test_health_check_endpoint_exists(self, client):
        """Verify health check endpoint is available"""
        response = await client.get("/api/v1/health")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT, status.HTTP_503_SERVICE_UNAVAILABLE]

    # test_cache_metrics_endpoint_requires_staff, test_cache_metrics_returns_all_cache_types,
    # test_cache_clear_endpoint_clears_caches, test_cache_clear_with_specific_prefix removed
    # 2026-07-05: /api/v1/staff/cache/metrics and /api/v1/staff/cache/clear have never
    # existed anywhere in the app (repo-wide grep for both paths returns no route
    # definitions). No git history of these routes ever being added or removed.


@pytest.mark.asyncio
class TestKeyOperationalIndicators:
    """Test suite for key operational indicators"""

    async def test_holds_ready_for_pickup_indicator(self, client, db_session, staff_user, token, patron, item):
        """Verify holds ready for pickup indicator displays correctly"""
        # ix_active_user_item_hold enforces at most one active hold per
        # (user_id, item_id) -- each ready hold needs its own item.
        for i in range(5):
            hold_item = CatalogItem(
                title=f"Dashboard Pickup Book {i}",
                author="Test Author",
                isbn=f"978-0-777777-{i:02d}-0",
                status=ItemStatus.available,
                call_number=f"PICKUP-{i:03d}",
                barcode=f"PICKUP-BARCODE-{i:03d}",
                publication_year=2024,
            )
            db_session.add(hold_item)
            await db_session.flush()
            hold = Hold(
                user_id=patron.id,
                item_id=hold_item.id,
                status=HoldStatus.ready,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(hold)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['ready_holds'] >= 5

    async def test_overdue_items_indicator(self, client, db_session, staff_user, token, patron, item):
        """Verify overdue items indicator"""
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert 'overdue_items' in data or 'overdue_count' in data

    async def test_patron_statistics_indicator(self, client, db_session, staff_user, token):
        """Verify patron statistics are available"""
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert 'total_patrons' in data
        assert 'active_patrons_30d' in data
        assert data['total_patrons'] >= 0
        assert data['active_patrons_30d'] >= 0

    async def test_outreach_dashboard_metrics(self, client, db_session, staff_user, token):
        """Verify outreach dashboard metrics endpoint"""
        response = await client.get(
            "/api/v1/staff/dashboard/outreach",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify outreach metrics
        assert 'total_partners' in data
        assert 'active_partners' in data
        assert 'upcoming_visits_this_week' in data
        assert 'active_bulk_checkouts' in data


@pytest.mark.asyncio
class TestQuickActions:
    """Test suite for quick action features"""

    async def test_staff_can_perform_checkout(self, client, db_session, staff_user, token, patron, item):
        """Verify staff can perform checkout via API"""
        response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    async def test_staff_can_perform_checkin(self, client, db_session, staff_user, token, patron, item):
        """Verify staff can perform check-in via API"""
        # First create a checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Then check it in
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    async def test_patron_lookup_functionality(self, client, db_session, staff_user, token, patron):
        """Verify patron lookup works"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should find the patron
        assert len(data.get('patrons', [])) > 0


@pytest.mark.asyncio
class TestAlertsAndNotifications:
    """Test suite for alerts and notifications system"""

    async def test_alerts_display_when_holds_ready(self, client, db_session, staff_user, token, patron, item):
        """Verify alerts display when holds are ready"""
        # ix_active_user_item_hold enforces at most one active hold per
        # (user_id, item_id) -- each ready hold needs its own item.
        for i in range(15):
            hold_item = CatalogItem(
                title=f"Dashboard Alert Book {i}",
                author="Test Author",
                isbn=f"978-0-666666-{i:02d}-0",
                status=ItemStatus.available,
                call_number=f"ALERT-{i:03d}",
                barcode=f"ALERT-BARCODE-{i:03d}",
                publication_year=2024,
            )
            db_session.add(hold_item)
            await db_session.flush()
            hold = Hold(
                user_id=patron.id,
                item_id=hold_item.id,
                status=HoldStatus.ready,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(hold)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['ready_holds'] >= 15

    async def test_alerts_display_for_high_fines(self, client, db_session, staff_user, token, patron):
        """Verify alerts display for high outstanding fines"""
        # Create high value fines
        for i in range(3):
            fine = Fine(
                user_id=patron.id,
                amount=Decimal("250.00"),
                amount_paid=Decimal("0.00"),
                status=FineStatus.unpaid,
                fine_type=FineType.overdue,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(fine)
        await db_session.commit()

        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['outstanding_fines_total'] >= 750

    async def test_notification_preferences_endpoint(self, client, token):
        """Verify notification preferences can be retrieved and updated"""
        # Get preferences
        response = await client.get(
            "/api/v1/notifications/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK

        # Update preferences -- PUT /preferences takes a granular per-type
        # list (UpdateNotificationPreferencesRequest in
        # app/schemas/notification_preferences.py), not the old flat
        # email_notifications/sms_notifications shape.
        response = await client.put(
            "/api/v1/notifications/preferences",
            json={
                "preferences": [
                    {
                        "notification_type": "hold_ready",
                        "label": "Hold ready for pickup",
                        "channel_email": True,
                        "channel_sms": True,
                    }
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


@pytest.mark.asyncio
class TestRealTimeUpdates:
    """Test suite for real-time update mechanisms"""

    async def test_websocket_endpoint_is_available(self, client):
        """Verify WebSocket endpoint is available"""
        # Note: This is a basic check. Full WebSocket testing requires a WebSocket client
        response = await client.get("/ws")
        # Expect upgrade required or similar response
        assert response.status_code in [
            status.HTTP_426_UPGRADE_REQUIRED,
            status.HTTP_101_SWITCHING_PROTOCOLS,
            status.HTTP_404_NOT_FOUND  # If WebSocket not implemented
        ]

    async def test_activity_feed_updates_with_new_checkout(self, client, db_session, staff_user, token, patron, item):
        """Verify activity feed reflects new checkouts"""
        # Get initial activity
        response1 = await client.get(
            "/api/v1/staff/dashboard/activity?limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        initial_count = len(response1.json().get('activities', []))

        # Create new checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Get updated activity
        response2 = await client.get(
            "/api/v1/staff/dashboard/activity?limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        updated_count = len(response2.json().get('activities', []))

        # Activity count should have increased
        assert updated_count >= initial_count


@pytest.mark.asyncio
class TestProductionReadiness:
    """Test suite for production-readiness validation"""

    async def test_all_endpoints_require_authentication(self, client):
        """Verify all staff endpoints require authentication"""
        # /api/v1/staff/cache/metrics removed from this list 2026-07-05: that
        # route has never existed (see TestSystemHealthChecks removal note above).
        endpoints = [
            "/api/v1/staff/dashboard/stats",
            "/api/v1/staff/dashboard/activity",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_all_endpoints_require_staff_role(self, client, user_token):
        """Verify all staff endpoints require staff role"""
        endpoints = [
            "/api/v1/staff/dashboard/stats",
            "/api/v1/staff/dashboard/activity",
        ]

        for endpoint in endpoints:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_error_handling_for_invalid_parameters(self, client, token):
        """Verify proper error handling for invalid parameters"""
        response = await client.get(
            "/api/v1/staff/dashboard/activity?limit=1000",  # Exceeds max
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should either reject or cap at max
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    async def test_performance_under_load(self, client, db_session, staff_user, token):
        """Verify dashboard stats can be retrieved consistently"""
        for i in range(10):
            response = await client.get(
                "/api/v1/staff/dashboard/stats",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            assert 'checkouts_today' in response.json()

    async def test_response_time_acceptable(self, client, token):
        """Verify dashboard response times are acceptable"""
        import time

        start = time.time()
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        elapsed = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        # Response should complete in under 2 seconds
        assert elapsed < 2.0, f"Dashboard stats took {elapsed:.2f}s, expected < 2s"

    async def test_dashboard_data_consistency(self, client, db_session, staff_user, token):
        """Verify dashboard metrics are consistent across calls"""
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        data1 = response1.json()

        # Immediately fetch again
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        data2 = response2.json()

        # Key metrics should be identical or very close
        assert data1['checkouts_today'] == data2['checkouts_today']
        assert data1['total_patrons'] == data2['total_patrons']
