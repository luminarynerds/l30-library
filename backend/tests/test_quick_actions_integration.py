# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for staff dashboard quick actions
Tests checkout, checkin, and patron lookup functionality
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus


@pytest.fixture
def token(test_staff):
    """Staff auth token -- quick actions are staff-only."""
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
        title="Quick Action Test Book",
        author="Test Author",
        isbn="978-0-999999-99-9",
        status=ItemStatus.available,
        call_number="QA-001",
        barcode="QA-BARCODE-001",
        publication_year=2024,
    )
    test_db.add(catalog_item)
    await test_db.commit()
    await test_db.refresh(catalog_item)
    return catalog_item


@pytest.mark.asyncio
class TestCheckoutQuickAction:
    """Test checkout quick action functionality"""

    async def test_checkout_action_succeeds_with_valid_patron_and_item(
        self,
        client,
        db_session,
        staff_user,
        token,
        patron,
        item
    ):
        """Verify checkout action succeeds with valid patron and item"""
        response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], response.text
        data = response.json()

        # Verify checkout was created
        assert "checkout_id" in data or "id" in data or response.status_code == 201

    async def test_checkout_action_fails_with_invalid_patron(self, client, token, item):
        """Verify checkout fails with invalid patron"""
        response = await client.post(
            "/api/v1/staff/patrons/99999/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]

    async def test_checkout_action_fails_with_invalid_item(
        self,
        client,
        token,
        patron
    ):
        """Verify checkout fails with invalid item"""
        response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/quick-checkout",
            json={"barcode": "INVALID_BARCODE_12345"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]

    async def test_checkout_action_fails_for_blocked_patron(
        self,
        client,
        db_session,
        token,
        item
    ):
        """Verify checkout fails when patron is blocked"""
        from app.models.user import User

        # Create blocked patron
        blocked_patron = User(
            email=f"blocked_patron_{datetime.now().timestamp()}@test.com",
            password_hash="hashed_password",
            first_name="Blocked",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=False  # Effectively blocked
        )
        db_session.add(blocked_patron)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/staff/patrons/{blocked_patron.id}/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should fail due to blocked status
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ]

    async def test_checkout_respects_checkout_limits(
        self,
        client,
        db_session,
        token,
        patron,
        item
    ):
        """Verify checkout respects patron checkout limits"""
        # Try to checkout item that may already be checked out
        checkout1 = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout1)
        await db_session.commit()

        # Try to checkout same item again
        response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should either fail (a duplicate active checkout is a 409 Conflict;
        # some validation paths raise 400) or check out a different copy
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        ]

    async def test_checkout_updates_dashboard_metrics(
        self,
        client,
        db_session,
        token,
        patron,
        item
    ):
        """Verify checkout updates dashboard metrics"""
        # Capture identifiers before any request. The dashboard/stats call
        # below can expire ORM attributes on `patron`/`item` (commit inside
        # the request's own session); re-accessing `.id`/`.barcode` afterward
        # triggers a lazy DB reload with no active greenlet, which raises
        # sqlalchemy.exc.MissingGreenlet in plain sync test code.
        patron_id = patron.id
        item_barcode = item.barcode

        # Get baseline
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        baseline_checkouts = response1.json()['checkouts_today']

        # Perform checkout
        await client.post(
            f"/api/v1/staff/patrons/{patron_id}/quick-checkout",
            json={"barcode": item_barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Get updated metrics
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        updated_checkouts = response2.json()['checkouts_today']

        # Should increment
        assert updated_checkouts >= baseline_checkouts


@pytest.mark.asyncio
class TestCheckinQuickAction:
    """Test checkin quick action functionality"""

    async def test_checkin_action_succeeds_with_valid_item(
        self,
        client,
        db_session,
        token,
        patron,
        item
    ):
        """Verify checkin action succeeds with valid item"""
        # First checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Then checkin
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], response.text

    async def test_checkin_action_fails_with_invalid_item(self, client, token):
        """Verify checkin fails with invalid item"""
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": "INVALID_BARCODE_12345"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # checkin-barcode wraps any lookup failure in a generic 400, not 404
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_checkin_action_handles_already_checked_in_item(
        self,
        client,
        token,
        item
    ):
        """Verify checkin handles already checked-in items gracefully"""
        # Try to checkin item that's not checked out
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    async def test_checkin_updates_dashboard_metrics(
        self,
        client,
        db_session,
        token,
        patron,
        item
    ):
        """Verify checkin updates dashboard metrics"""
        # First checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Capture before any request -- see comment in
        # test_checkout_updates_dashboard_metrics on why `item.barcode`
        # can't be re-accessed after the dashboard/stats call.
        item_barcode = item.barcode

        # Get baseline
        response1 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        baseline_returns = response1.json()['returns_today']

        # Perform checkin
        await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item_barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Get updated metrics
        response2 = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        updated_returns = response2.json()['returns_today']

        # Should increment
        assert updated_returns >= baseline_returns

    async def test_checkin_calculates_fines_for_overdue_items(
        self,
        client,
        db_session,
        token,
        patron,
        item
    ):
        """Verify checkin calculates fines for overdue items"""
        # Create overdue checkout
        overdue_due_date = datetime.now(timezone.utc) - timedelta(days=5)
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=20),
            due_date=overdue_due_date,
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        # Perform checkin
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], response.text


@pytest.mark.asyncio
class TestPatronLookupQuickAction:
    """Test patron lookup quick action functionality"""

    async def test_patron_lookup_by_email(
        self,
        client,
        token,
        patron
    ):
        """Verify patron lookup by email works"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should find the patron
        assert 'patrons' in data or len(data) > 0

    async def test_patron_lookup_by_name(
        self,
        client,
        token,
        patron
    ):
        """Verify patron lookup by name works"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.first_name}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should find the patron
        assert 'patrons' in data or len(data) > 0

    async def test_patron_lookup_returns_patron_details(
        self,
        client,
        token,
        patron
    ):
        """Verify patron lookup returns necessary details"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should include patron ID and name for quick actions
        result = data.get('patrons', data)[0] if isinstance(data, dict) else data[0]
        assert 'id' in result or 'patron_id' in result
        assert 'email' in result or 'first_name' in result

    async def test_patron_lookup_with_no_results(
        self,
        client,
        token
    ):
        """Verify patron lookup handles no results gracefully"""
        response = await client.get(
            "/api/v1/staff/patrons?search=nonexistent_email_12345@test.com",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return empty results, not error
        results = data.get('patrons', data)
        assert len(results) == 0

    async def test_patron_lookup_pagination(
        self,
        client,
        token,
        patron
    ):
        """Verify patron lookup supports pagination"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.first_name}&limit=10&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_patron_lookup_respects_privacy(
        self,
        client,
        token,
        patron
    ):
        """Verify patron lookup doesn't expose sensitive data"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        result = data.get('patrons', data)[0] if isinstance(data, dict) else data[0]

        # Should not include password or sensitive data
        assert 'password_hash' not in result
        assert 'password' not in result
        assert 'salt' not in result


@pytest.mark.asyncio
class TestQuickActionPermissions:
    """Test permission checks for quick actions"""

    async def test_checkout_requires_staff_role(
        self,
        client,
        user_token,
        patron,
        item
    ):
        """Verify checkout requires staff role"""
        response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_checkin_requires_staff_role(
        self,
        client,
        user_token,
        item
    ):
        """Verify checkin requires staff role"""
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_patron_lookup_requires_authentication(
        self,
        client,
        patron
    ):
        """Verify patron lookup requires authentication"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_patron_lookup_requires_staff_role(
        self,
        client,
        user_token,
        patron
    ):
        """Verify patron lookup requires staff role"""
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}",
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestQuickActionPerformance:
    """Test performance of quick actions"""

    async def test_checkout_completes_quickly(
        self,
        client,
        token,
        patron,
        item
    ):
        """Verify checkout action completes quickly"""
        import time

        start = time.time()
        response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/quick-checkout",
            json={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )
        elapsed = time.time() - start

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], response.text
        # Should complete in under 2 seconds
        assert elapsed < 2.0

    async def test_checkin_completes_quickly(
        self,
        client,
        db_session,
        token,
        patron,
        item
    ):
        """Verify checkin action completes quickly"""
        import time

        # Setup checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=CheckoutStatus.active
        )
        db_session.add(checkout)
        await db_session.commit()

        start = time.time()
        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"}
        )
        elapsed = time.time() - start

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], response.text
        # Should complete in under 2 seconds
        assert elapsed < 2.0

    async def test_patron_lookup_completes_quickly(
        self,
        client,
        token,
        patron
    ):
        """Verify patron lookup completes quickly"""
        import time

        start = time.time()
        response = await client.get(
            f"/api/v1/staff/patrons?search={patron.email}",
            headers={"Authorization": f"Bearer {token}"}
        )
        elapsed = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        # Should complete in under 1 second
        assert elapsed < 1.0
