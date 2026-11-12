# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for staff override patron restrictions.

This module tests staff capabilities to override patron restrictions:
- Waiving fines
- Extending due dates (override renewal)
- Increasing checkout limits (staff checkout bypass)
- Lifting blocks (unblock/unsuspend patrons)

These tests verify that staff members can perform administrative
overrides to help patrons in exceptional circumstances.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole, PatronStatus


# =============================================================================
# Helper Functions
# =============================================================================


async def get_staff_token(client, email, password):
    """Helper to get staff authentication token."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


async def get_patron_token(client, email, password):
    """Helper to get patron authentication token."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def staff_test_user(test_db):
    """Create a staff user for testing with known password."""
    from app.core.security import hash_password

    staff = User(
        email="override_staff@l30.org",
        password_hash=hash_password("StaffTestPassword123!"),
        first_name="Staff",
        last_name="Override",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(staff)
    await test_db.commit()
    await test_db.refresh(staff)
    return staff


@pytest.fixture
async def admin_test_user(test_db):
    """Create an admin user for testing with known password."""
    from app.core.security import hash_password

    admin = User(
        email="override_admin@l30.org",
        password_hash=hash_password("AdminTestPassword123!"),
        first_name="Admin",
        last_name="Override",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def patron_test_user(test_db):
    """Create a patron user for testing with known password."""
    from app.core.security import hash_password

    patron = User(
        email="override_patron@example.test",
        password_hash=hash_password("PatronTestPassword123!"),
        first_name="Test",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LC12345678",
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.fixture
async def blocked_patron_user(test_db):
    """Create a blocked patron for testing."""
    from app.core.security import hash_password

    patron = User(
        email="blocked_override_patron@example.test",
        password_hash=hash_password("BlockedPatronPassword123!"),
        first_name="Blocked",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=False,
        email_verified=True,
        patron_status=PatronStatus.BLOCKED,
        block_reason="Test block reason",
        library_card="LC99999999",
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.fixture
async def suspended_patron_user(test_db):
    """Create a suspended patron for testing."""
    from app.core.security import hash_password

    patron = User(
        email="suspended_override_patron@example.test",
        password_hash=hash_password("SuspendedPatronPassword123!"),
        first_name="Suspended",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=False,
        email_verified=True,
        patron_status=PatronStatus.SUSPENDED,
        suspension_reason="Test suspension reason",
        suspended_at=datetime.now(timezone.utc),
        library_card="LC88888888",
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.fixture
async def test_available_item(test_db):
    """Create a catalog item for testing."""
    item = CatalogItem(
        title="Override Test Book",
        author="Test Author",
        isbn="9781234567899",
        barcode="OVERRIDE001",
        status=ItemStatus.available,
        location="Test Shelf",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def checked_out_item_with_checkout(test_db, patron_test_user):
    """Create a catalog item that's checked out with its checkout record."""
    item = CatalogItem(
        title="Checked Out Override Book",
        author="Test Author",
        isbn="9781234567891",
        barcode="OVERRIDE002",
        status=ItemStatus.checked_out,
        location="Test Shelf",
    )
    test_db.add(item)
    await test_db.flush()

    checkout = Checkout(
        user_id=patron_test_user.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
        renewal_count=0,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(item)
    await test_db.refresh(checkout)
    return item, checkout


@pytest.fixture
async def overdue_checkout_item(test_db, patron_test_user):
    """Create an overdue checkout."""
    item = CatalogItem(
        title="Overdue Override Book",
        author="Test Author",
        isbn="9781234567892",
        barcode="OVERRIDE003",
        status=ItemStatus.checked_out,
        location="Test Shelf",
    )
    test_db.add(item)
    await test_db.flush()

    checkout = Checkout(
        user_id=patron_test_user.id,
        item_id=item.id,
        status=CheckoutStatus.overdue,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=21),
        due_date=datetime.now(timezone.utc) - timedelta(days=7),
        renewal_count=0,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(item)
    await test_db.refresh(checkout)
    return item, checkout


@pytest.fixture
async def unpaid_fine_record(test_db, patron_test_user):
    """Create an unpaid fine for testing."""
    fine = Fine(
        user_id=patron_test_user.id,
        amount=Decimal("10.00"),
        amount_paid=Decimal("0.00"),
        fine_type=FineType.other,
        status=FineStatus.unpaid,
        description="Test fine for damaged book",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


@pytest.fixture
async def partial_fine_record(test_db, patron_test_user):
    """Create a partially paid fine for testing."""
    fine = Fine(
        user_id=patron_test_user.id,
        amount=Decimal("25.00"),
        amount_paid=Decimal("10.00"),
        fine_type=FineType.lost_item,
        status=FineStatus.partial,
        description="Test fine for lost book",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


@pytest.fixture
async def item_with_hold_record(test_db, patron_test_user):
    """Create a checkout with another patron's hold on the item."""
    from app.core.security import hash_password

    # Create another patron for the hold
    other_patron = User(
        email="other_hold_patron@example.test",
        password_hash=hash_password("OtherPatronPassword123!"),
        first_name="Other",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LC77777777",
    )
    test_db.add(other_patron)
    await test_db.flush()

    item = CatalogItem(
        title="Popular Override Book",
        author="Popular Author",
        isbn="9781234567893",
        barcode="OVERRIDE004",
        status=ItemStatus.checked_out,
        location="Test Shelf",
    )
    test_db.add(item)
    await test_db.flush()

    checkout = Checkout(
        user_id=patron_test_user.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
        renewal_count=0,
    )
    test_db.add(checkout)

    hold = Hold(
        user_id=other_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)

    await test_db.commit()
    await test_db.refresh(item)
    await test_db.refresh(checkout)
    await test_db.refresh(hold)
    return item, checkout, hold


# =============================================================================
# Tests: Waiving Fines
# =============================================================================


@pytest.mark.integration
class TestWaiveFines:
    """Tests for staff ability to waive fines."""

    async def test_staff_can_waive_unpaid_fine(
        self,
        client,
        test_db,
        staff_test_user,
        admin_test_user,
        patron_test_user,
        unpaid_fine_record,
    ):
        """Admin should be able to waive an unpaid fine over the $5 staff
        auto-waive threshold (see _AUTO_WAIVE_LIMIT in
        app/api/v1/staff_fines/fines.py). This fine is $10.00: a plain
        STAFF actor would land it in pending_approval instead of waiving
        it outright, so this scenario needs an admin+ actor to auto-waive.
        The endpoint also now returns a FineWaiverResponse, not the fine
        itself, and money fields serialize as JSON floats.
        """
        token = await get_staff_token(client, "override_admin@l30.org", "AdminTestPassword123!")
        assert token is not None, "Failed to get admin token"

        response = await client.post(
            f"/api/v1/staff/fines/{unpaid_fine_record.id}/waive",
            json={"reason": "Customer hardship - one-time courtesy waiver"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "waived"
        assert data["fine_id"] == unpaid_fine_record.id
        assert data["waived_by"] == admin_test_user.id

        # Verify in database
        await test_db.refresh(unpaid_fine_record)
        assert unpaid_fine_record.status == FineStatus.waived
        assert unpaid_fine_record.waived_by_id == admin_test_user.id
        assert unpaid_fine_record.waived_at is not None
        assert "Customer hardship" in (unpaid_fine_record.notes or "")

    async def test_staff_can_waive_partial_fine(
        self,
        client,
        test_db,
        staff_test_user,
        admin_test_user,
        patron_test_user,
        partial_fine_record,
    ):
        """Admin should be able to waive the remaining $15.00 balance of a
        partial fine -- over the $5 staff auto-waive threshold, so this
        needs an admin+ actor (see note on test_staff_can_waive_unpaid_fine).
        """
        token = await get_staff_token(client, "override_admin@l30.org", "AdminTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/fines/{partial_fine_record.id}/waive",
            json={"reason": "Amnesty day waiver"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "waived"

        # Verify in database
        await test_db.refresh(partial_fine_record)
        assert partial_fine_record.status == FineStatus.waived
        assert partial_fine_record.waived_by_id == admin_test_user.id

    async def test_cannot_waive_already_paid_fine(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
    ):
        """Cannot waive a fine that's already been paid."""
        # Create a paid fine
        paid_fine = Fine(
            user_id=patron_test_user.id,
            amount=Decimal("5.00"),
            amount_paid=Decimal("5.00"),
            fine_type=FineType.other,
            status=FineStatus.paid,
            description="Already paid fine",
        )
        test_db.add(paid_fine)
        await test_db.commit()
        await test_db.refresh(paid_fine)

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/fines/{paid_fine.id}/waive",
            json={"reason": "Testing waiver"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "already" in response.json()["error"]["message"].lower()

    async def test_bulk_waive_fines_for_amnesty(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
        unpaid_fine_record,
    ):
        """Staff should be able to bulk waive fines for amnesty day."""
        # Create additional fine
        another_fine = Fine(
            user_id=patron_test_user.id,
            amount=Decimal("15.00"),
            amount_paid=Decimal("0.00"),
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            description="Another test fine",
        )
        test_db.add(another_fine)
        await test_db.commit()

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            "/api/v1/staff/patrons/bulk-waive-fines",
            json={
                "patron_ids": [patron_test_user.id],
                "reason": "Amnesty Day - All fines waived",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["fines_waived"] >= 2
        assert float(data["total_amount_waived"]) >= 25.00


# =============================================================================
# Tests: Extending Due Dates (Override Renewal)
# =============================================================================


@pytest.mark.integration
class TestOverrideRenewal:
    """Tests for staff ability to extend due dates via override renewal."""

    async def test_staff_can_renew_checkout(
        self,
        client,
        test_db,
        staff_test_user,
        checked_out_item_with_checkout,
    ):
        """Staff should be able to renew a checkout."""
        item, checkout = checked_out_item_with_checkout
        original_due_date = checkout.due_date

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["renewal_count"] == 1

        # Verify due date was extended
        new_due_date = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        original_due_aware = (
            original_due_date.replace(tzinfo=timezone.utc)
            if original_due_date.tzinfo is None
            else original_due_date
        )
        assert new_due_date > original_due_aware

    async def test_staff_can_renew_overdue_checkout(
        self,
        client,
        test_db,
        staff_test_user,
        overdue_checkout_item,
    ):
        """Staff should be able to renew an overdue checkout."""
        item, checkout = overdue_checkout_item

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Overdue checkout should become active again
        assert data["status"] == "active"
        assert data["renewal_count"] == 1

        # New due date should be in the future
        new_due_date = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        assert new_due_date > datetime.now(timezone.utc)

    async def test_staff_override_renew_still_blocked_by_hold_restriction(
        self,
        client,
        test_db,
        staff_test_user,
        item_with_hold_record,
    ):
        """Staff override renewal does NOT bypass hold restrictions.

        app/api/v1/staff/circulation_checkin.py::staff_override_renew is
        explicit about this: staff override waives the overdue-grace cutoff
        and (with override=True) the renewal cap, but "the hold queue still
        applies, so a waiting patron is never bumped." So a checkout with a
        pending hold from another patron still gets a 409 on override-renew.
        """
        item, checkout, hold = item_with_hold_record

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409

        # Verify checkout was not renewed
        await test_db.refresh(checkout)
        assert checkout.renewal_count == 0

    async def test_renew_all_eligible_items(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
        checked_out_item_with_checkout,
    ):
        """Staff should be able to renew all eligible items for a patron."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{patron_test_user.id}/renew-all",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["renewed_count"] >= 1
        assert "renewed" in data["message"].lower()


# =============================================================================
# Tests: Lifting Blocks
# =============================================================================


@pytest.mark.integration
class TestLiftBlocks:
    """Tests for staff ability to lift patron blocks."""

    async def test_staff_can_unblock_patron(
        self,
        client,
        test_db,
        staff_test_user,
        blocked_patron_user,
    ):
        """Staff should be able to unblock a blocked patron."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{blocked_patron_user.id}/status",
            json={"action": "unblock"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

        # Verify in database
        await test_db.refresh(blocked_patron_user)
        assert blocked_patron_user.is_active is True
        assert blocked_patron_user.patron_status == PatronStatus.ACTIVE
        assert blocked_patron_user.block_reason is None

    async def test_staff_can_lift_suspension(
        self,
        client,
        test_db,
        staff_test_user,
        suspended_patron_user,
    ):
        """Staff should be able to lift a suspension."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{suspended_patron_user.id}/status",
            json={"action": "unsuspend"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

        # Verify in database
        await test_db.refresh(suspended_patron_user)
        assert suspended_patron_user.is_active is True
        assert suspended_patron_user.patron_status == PatronStatus.ACTIVE
        assert suspended_patron_user.suspension_reason is None
        assert suspended_patron_user.suspended_at is None

    async def test_staff_can_unblock_using_legacy_endpoint(
        self,
        client,
        test_db,
        staff_test_user,
        blocked_patron_user,
    ):
        """Legacy block endpoint should also work for unblocking."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{blocked_patron_user.id}/block",
            json={"blocked": False},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    async def test_staff_can_block_patron(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
    ):
        """Staff should be able to block a patron with a reason."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{patron_test_user.id}/status",
            json={
                "action": "block",
                "reason": "Policy violation - multiple lost items",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

        # Verify in database
        await test_db.refresh(patron_test_user)
        assert patron_test_user.is_active is False
        assert patron_test_user.patron_status == PatronStatus.BLOCKED
        assert "Policy violation" in patron_test_user.block_reason

    async def test_staff_can_suspend_patron_with_expiry(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
    ):
        """Staff should be able to suspend a patron with an expiry date."""
        expiry_date = datetime.now(timezone.utc) + timedelta(days=30)

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{patron_test_user.id}/status",
            json={
                "action": "suspend",
                "reason": "Overdue items - temporary suspension",
                "suspended_until": expiry_date.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

        # Verify in database
        await test_db.refresh(patron_test_user)
        assert patron_test_user.patron_status == PatronStatus.SUSPENDED
        assert patron_test_user.suspended_until is not None

    async def test_block_requires_reason(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
    ):
        """Blocking a patron should require a reason."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{patron_test_user.id}/status",
            json={"action": "block"},  # No reason provided
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "reason" in response.json()["error"]["message"].lower()


# =============================================================================
# Tests: Staff Checkout Bypass
# =============================================================================


@pytest.mark.integration
class TestStaffCheckoutBypass:
    """Tests for staff ability to checkout items with overrides."""

    async def test_staff_can_checkout_for_patron(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
        test_available_item,
    ):
        """Staff should be able to checkout items for a patron."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{patron_test_user.id}/quick-checkout",
            json={"barcode": test_available_item.barcode},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["user_id"] == patron_test_user.id
        assert data["item_id"] == test_available_item.id
        assert data["status"] == "active"

    async def test_staff_checkin_by_barcode(
        self,
        client,
        test_db,
        staff_test_user,
        checked_out_item_with_checkout,
    ):
        """Staff should be able to checkin items by barcode."""
        item, checkout = checked_out_item_with_checkout

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            "/api/v1/staff/checkin-barcode",
            params={"barcode": item.barcode},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["checkout"]["status"] == "returned"

    async def test_staff_checkin_by_checkout_id(
        self,
        client,
        test_db,
        staff_test_user,
        checked_out_item_with_checkout,
    ):
        """Staff should be able to checkin items by checkout ID."""
        item, checkout = checked_out_item_with_checkout

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.post(
            "/api/v1/circulation/checkin",
            params={"checkout_id": checkout.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"

    async def test_staff_can_list_patron_checkouts(
        self,
        client,
        test_db,
        staff_test_user,
        patron_test_user,
        checked_out_item_with_checkout,
    ):
        """Staff should be able to see all patron checkouts.

        GET /api/v1/staff/checkouts (a flat, patron-filterable listing) was
        removed 2026-02-15 (b2013f01b) with no 1:1 successor. The scoped
        per-patron endpoint below fully covers this test's intent.
        """
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        response = await client.get(
            f"/api/v1/staff/patrons/{patron_test_user.id}/checkouts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(c["user_id"] == patron_test_user.id for c in data)


# =============================================================================
# Tests: Combined Scenarios
# =============================================================================


@pytest.mark.integration
class TestCombinedScenarios:
    """Tests for complex scenarios involving multiple overrides."""

    async def test_unblock_and_checkout_workflow(
        self,
        client,
        test_db,
        staff_test_user,
        blocked_patron_user,
        test_available_item,
    ):
        """Staff should be able to unblock a patron and then checkout for them."""
        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        # First, unblock the patron
        unblock_response = await client.post(
            f"/api/v1/staff/patrons/{blocked_patron_user.id}/status",
            json={"action": "unblock"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert unblock_response.status_code == 200

        # Then checkout an item for them
        checkout_response = await client.post(
            f"/api/v1/staff/patrons/{blocked_patron_user.id}/quick-checkout",
            json={"barcode": test_available_item.barcode},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert checkout_response.status_code == 201
        data = checkout_response.json()["checkout"]
        assert data["user_id"] == blocked_patron_user.id

    async def test_waive_fines_and_unblock_workflow(
        self,
        client,
        test_db,
        staff_test_user,
    ):
        """Staff should be able to waive fines and unblock in one workflow."""
        from app.core.security import hash_password

        # Create a patron with fines and blocked status
        patron = User(
            email="fined_blocked_workflow@example.test",
            password_hash=hash_password("FineBlockedPassword123!"),
            first_name="Fined",
            last_name="Blocked",
            role=UserRole.PATRON,
            is_active=False,
            email_verified=True,
            patron_status=PatronStatus.BLOCKED,
            block_reason="High fines",
            library_card="LC55555555",
        )
        test_db.add(patron)
        await test_db.flush()

        fine = Fine(
            user_id=patron.id,
            amount=Decimal("50.00"),
            amount_paid=Decimal("0.00"),
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            description="Lost book replacement",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)
        await test_db.refresh(patron)

        token = await get_staff_token(client, "override_staff@l30.org", "StaffTestPassword123!")
        assert token is not None

        # Waive the fine
        waive_response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/waive",
            json={"reason": "Lost book was found and returned"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert waive_response.status_code == 200

        # Unblock the patron
        unblock_response = await client.post(
            f"/api/v1/staff/patrons/{patron.id}/status",
            json={"action": "unblock"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert unblock_response.status_code == 200
        assert unblock_response.json()["is_active"] is True


# =============================================================================
# Tests: Authorization
# =============================================================================


@pytest.mark.integration
class TestAuthorization:
    """Tests to verify proper authorization for staff overrides."""

    async def test_patron_cannot_waive_own_fines(
        self,
        client,
        test_db,
        patron_test_user,
        unpaid_fine_record,
    ):
        """Patrons should not be able to waive their own fines."""
        token = await get_patron_token(
            client, "override_patron@example.test", "PatronTestPassword123!"
        )
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/fines/{unpaid_fine_record.id}/waive",
            json={"reason": "Self waiver attempt"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should be forbidden (403)
        assert response.status_code == 403

    async def test_patron_cannot_unblock_self(
        self,
        client,
        test_db,
        blocked_patron_user,
        patron_test_user,
    ):
        """Patrons should not be able to unblock themselves."""
        token = await get_patron_token(
            client, "override_patron@example.test", "PatronTestPassword123!"
        )
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/patrons/{blocked_patron_user.id}/status",
            json={"action": "unblock"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should be forbidden (403)
        assert response.status_code == 403

    async def test_patron_cannot_override_renew(
        self,
        client,
        test_db,
        checked_out_item_with_checkout,
        patron_test_user,
    ):
        """Patrons should not be able to use staff override renewal."""
        item, checkout = checked_out_item_with_checkout

        token = await get_patron_token(
            client, "override_patron@example.test", "PatronTestPassword123!"
        )
        assert token is not None

        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should be forbidden (403)
        assert response.status_code == 403

    async def test_unauthenticated_cannot_waive_fines(self, client):
        """Unauthenticated users should not be able to waive fines."""
        response = await client.post(
            "/api/v1/staff/fines/1/waive",
            json={"reason": "Anonymous waiver attempt"},
        )

        assert response.status_code == 401

    async def test_unauthenticated_cannot_unblock_patrons(self, client):
        """Unauthenticated users should not be able to unblock patrons."""
        response = await client.post(
            "/api/v1/staff/patrons/1/status",
            json={"action": "unblock"},
        )

        assert response.status_code == 401
