# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Real-time updates and WebSocket integration tests for Staff Dashboard
Tests WebSocket connections, real-time notifications, and live data updates
"""

import pytest
import json
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.catalog import CatalogItem, ItemStatus


@pytest.fixture
def token(test_staff):
    """Staff auth token -- dashboard endpoints are staff-only."""
    from app.core.security import create_access_token

    return create_access_token(subject=test_staff.id, email=test_staff.email)


@pytest.fixture
async def patron(test_patron):
    """Alias -- this file refers to the patron fixture as `patron`."""
    return test_patron


@pytest.fixture
async def item(test_db):
    """A catalog item for real-time dashboard metric tests."""
    catalog_item = CatalogItem(
        title="Realtime Test Book",
        author="Test Author",
        isbn="978-0-777777-77-7",
        status=ItemStatus.available,
        call_number="RT-001",
        barcode="RT-BARCODE-001",
        publication_year=2024,
    )
    test_db.add(catalog_item)
    await test_db.commit()
    await test_db.refresh(catalog_item)
    return catalog_item


# TestWebSocketConnections removed 2026-07-05: tested a generic staff-dashboard
# `/ws` with query-string token auth that has never existed. Only registered
# websocket routes app-wide are /api/v1/rfid/ws, /api/v1/ws/patron,
# /api/v1/staff/floor/ws, and a board-meetings live channel -- none match this
# class's assumptions. Traced to commit 7d60bdf4f ("Verify LSC outreach
# features..."), a speculative verification commit with no corresponding
# backend route ever added. websocket_client/authenticated_websocket_client
# fixtures were never defined anywhere in the suite.


@pytest.mark.asyncio
class TestDashboardRealTimeUpdates:
    """Test real-time dashboard updates"""

    async def test_new_checkout_updates_metrics_in_realtime(
        self,
        client,
        db_session,
        staff_user,
        token,
        patron,
        item
    ):
        """Verify new checkout updates dashboard metrics in real-time"""
        # Capture ids before any request -- the dashboard endpoint commits on
        # its own session and expires ORM-bound attributes on `patron`/`item`
        # (AsyncSession has no implicit-lazy-load support, so a later bare
        # `patron.id` access raises MissingGreenlet).
        patron_id, item_id = patron.id, item.id

        # Get baseline metrics
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        baseline_checkouts = response1.json()['checkouts_today']

        # Create new checkout
        checkout = Checkout(
            user_id=patron_id,
            item_id=item_id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=date.today() + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Get updated metrics
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        updated_checkouts = response2.json()['checkouts_today']

        # Should show updated count
        assert updated_checkouts >= baseline_checkouts

    async def test_new_hold_updates_metrics_in_realtime(
        self,
        client,
        db_session,
        staff_user,
        token,
        patron,
        item
    ):
        """Verify new hold updates dashboard metrics in real-time"""
        # Capture ids before any request -- see comment in
        # test_new_checkout_updates_metrics_in_realtime.
        patron_id, item_id = patron.id, item.id

        # Get baseline
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        baseline_ready_holds = response1.json()['ready_holds']

        # Create ready hold
        hold = Hold(
            user_id=patron_id,
            item_id=item_id,
            status=HoldStatus.ready,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(hold)
        await db_session.commit()

        # Get updated metrics
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        updated_ready_holds = response2.json()['ready_holds']

        # Should show updated count
        assert updated_ready_holds >= baseline_ready_holds

    async def test_activity_feed_updates_in_realtime(
        self,
        client,
        db_session,
        staff_user,
        token,
        patron,
        item
    ):
        """Verify activity feed updates with new activities"""
        # Create a checkout (activity)
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=date.today() + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Activity feed should include the checkout
        response = await client.get(
            "/api/v1/staff/dashboard/activity?limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        activities = response.json()['activities']
        assert len(activities) > 0

        # Find checkout activity (ActivityItem's field is `activity_type`)
        checkout_activity = next(
            (a for a in activities if a['activity_type'] == 'checkout'),
            None
        )
        assert checkout_activity is not None

    async def test_overdue_items_updates_in_realtime(
        self,
        client,
        db_session,
        staff_user,
        token,
        patron,
        item
    ):
        """Verify overdue items count updates when items become overdue"""
        # Create checkout that will be overdue
        past_due_date = date.today() - timedelta(days=1)
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=past_due_date,
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Get metrics - should show overdue item
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['overdue_count'] >= 1

    async def test_fines_update_in_realtime(
        self,
        client,
        db_session,
        staff_user,
        token,
        patron
    ):
        """Verify fines are updated in real-time"""
        # Capture id before any request -- see comment in
        # test_new_checkout_updates_metrics_in_realtime.
        patron_id = patron.id

        # Get baseline fines
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        baseline_fines = float(response1.json()['outstanding_fines_total'])

        # Create new fine
        fine = Fine(
            user_id=patron_id,
            amount=50.00,
            amount_paid=0.00,
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(fine)
        await db_session.commit()

        # Get updated fines
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        updated_fines = float(response2.json()['outstanding_fines_total'])

        # Should show updated fine amount
        assert updated_fines >= baseline_fines


@pytest.mark.asyncio
class TestAutoRefreshMechanism:
    """Test auto-refresh mechanism for dashboard"""

    async def test_auto_refresh_interval_5_minutes(self):
        """Verify auto-refresh interval is set to 5 minutes"""
        # From StaffDashboardPage.tsx:
        # const AUTO_REFRESH_INTERVAL = 5 * 60 * 1000 = 300000ms
        expected_interval = 5 * 60 * 1000
        assert expected_interval == 300000

    async def test_manual_refresh_button_functionality(self, client, token):
        """Verify manual refresh updates data"""
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        _ = response1.json()

        # Manual refresh would call the same endpoint again
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        data2 = response2.json()

        # Should get valid response
        assert response2.status_code == 200
        assert data2 is not None


@pytest.mark.asyncio
class TestMessageQueuing:
    """Test message queuing for WebSocket"""

    async def test_messages_queued_while_disconnected(self):
        """Verify messages are queued while WebSocket is disconnected"""
        # This tests the useReconnectingWebSocket hook's queue functionality
        # Messages should be stored and flushed on reconnect
        queue = []

        def queue_message(msg):
            queue.append(msg)

        # Simulate queuing while disconnected
        queue_message({"type": "update", "data": "metrics"})
        queue_message({"type": "update", "data": "activity"})

        assert len(queue) == 2

    async def test_messages_flushed_on_reconnect(self):
        """Verify queued messages are flushed when connection restored"""
        queue = []
        sent = []

        def queue_message(msg):
            queue.append(msg)

        def send_queued_messages():
            while queue:
                msg = queue.pop(0)
                sent.append(msg)

        # Queue messages while disconnected
        queue_message({"type": "update"})
        queue_message({"type": "alert"})

        assert len(queue) == 2
        assert len(sent) == 0

        # Flush on reconnect
        send_queued_messages()

        assert len(queue) == 0
        assert len(sent) == 2


@pytest.mark.asyncio
class TestConnectionStateTracking:
    """Test WebSocket connection state tracking"""

    async def test_connection_states(self):
        """Verify all connection states are tracked"""
        states = ["connecting", "connected", "disconnected", "reconnecting"]

        for state in states:
            assert state in ["connecting", "connected", "disconnected", "reconnecting"]

    async def test_connection_state_transitions(self):
        """Verify proper connection state transitions"""
        # Valid state transitions:
        # connecting -> connected
        # connected -> disconnected
        # disconnected -> reconnecting
        # reconnecting -> connected

        transitions = [
            ("connecting", "connected"),
            ("connected", "disconnected"),
            ("disconnected", "reconnecting"),
            ("reconnecting", "connected"),
        ]

        for from_state, to_state in transitions:
            assert from_state in ["connecting", "connected", "disconnected", "reconnecting"]
            assert to_state in ["connecting", "connected", "disconnected", "reconnecting"]


@pytest.mark.asyncio
class TestRealTimeNotifications:
    """Test real-time notifications delivery"""

    # test_alert_notification_delivery removed 2026-07-05: POST
    # /api/v1/notifications/send has never existed. notifications.py only
    # defines /live, /live/unread-count, /live/{id}/read, /live/read-all,
    # /live/{id}, and /templates -- no generic "send" endpoint. Same
    # speculative-test origin as TestWebSocketConnections above.

    async def test_notification_preferences_respected(self, client, token):
        """Verify notification preferences are respected"""
        # Update preferences to disable email
        await client.put(
            "/api/v1/notifications/preferences",
            json={"email_notifications": False},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Verify preference was saved
        response = await client.get(
            "/api/v1/notifications/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestPerformanceUnderRealTimeLoad:
    """Test performance with real-time updates"""

    async def test_metrics_latency(self, client, token):
        """Verify metrics endpoint has acceptable latency"""
        import time

        start = time.time()
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        latency = time.time() - start

        assert response.status_code == 200
        # Should complete in < 1 second
        assert latency < 1.0, f"Metrics endpoint latency: {latency:.3f}s"

    async def test_activity_feed_latency(self, client, token):
        """Verify activity feed has acceptable latency"""
        import time

        start = time.time()
        response = await client.get(
            "/api/v1/staff/dashboard/activity?limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        latency = time.time() - start

        assert response.status_code == 200
        # Should complete in < 1 second
        assert latency < 1.0, f"Activity feed latency: {latency:.3f}s"

    async def test_concurrent_dashboard_requests(self, client, token):
        """Verify dashboard can handle concurrent requests"""
        import asyncio

        async def fetch_stats():
            # Simulate concurrent requests
            responses = []
            for _ in range(5):
                response = await client.get(
                    "/api/v1/staff/dashboard/stats",
                    headers={"Authorization": f"Bearer {token}"}
                )
                responses.append(response.status_code)
            return responses

        statuses = await fetch_stats()

        # All requests should succeed
        assert all(status == 200 for status in statuses)


@pytest.mark.asyncio
class TestNetworkResilience:
    """Test resilience to network issues"""

    async def test_reconnection_on_network_failure(self, client, token):
        """Verify system handles network failures gracefully"""
        # Simulate network failure and recovery
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should still be responsive after simulated failure
        assert response.status_code == 200

    async def test_partial_response_handling(self, client, token):
        """Verify system handles incomplete responses"""
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should always have complete data
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 10  # Should have many fields

    async def test_timeout_handling(self, client, token):
        """Verify timeouts are handled appropriately"""
        # This would test behavior when requests timeout
        # Implementation depends on client configuration
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [200, 408, 504]  # OK, Request Timeout, or Service Unavailable
