# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for staff checkout flow.

Tests cover:
1. Barcode scanning functionality
2. Manual entry checkout
3. Checkout overrides for blocked/suspended/deceased patrons
4. Handling items with holds during checkout
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import PatronStatus, User, UserRole


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
async def test_catalog_item_with_barcode(test_db):
    """Create a test catalog item with a barcode for staff operations."""
    item = CatalogItem(
        title="Test Book with Barcode",
        author="Test Author",
        isbn="978-0-123456-78-9",
        description="A test book for staff checkout testing",
        status=ItemStatus.available,
        call_number="TEST-002",
        publication_year=2024,
        barcode="BARCODE-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_catalog_item_codabar(test_db):
    """Create a test catalog item with Codabar barcode format."""
    item = CatalogItem(
        title="Codabar Book",
        author="Library Author",
        isbn="978-0-987654-32-1",
        description="A test book with Codabar barcode",
        status=ItemStatus.available,
        call_number="CODA-001",
        publication_year=2024,
        barcode="A1234567890A",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_catalog_item_code39(test_db):
    """Create a test catalog item with Code 39 barcode format."""
    item = CatalogItem(
        title="Code 39 Book",
        author="Tech Author",
        isbn="978-0-111111-11-1",
        description="A test book with Code 39 barcode",
        status=ItemStatus.available,
        call_number="C39-001",
        publication_year=2024,
        barcode="*TEST123*",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_suspended_patron(test_db):
    """Create a test patron with suspended status."""
    from app.core.security import hash_password

    user = User(
        email="suspended@example.com",
        password_hash=hash_password("SuspendedPassword123!"),
        first_name="Suspended",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        patron_status=PatronStatus.SUSPENDED,
        suspension_reason="Overdue items",
        suspended_at=datetime.now(),
        suspended_until=datetime.now() + timedelta(days=7),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_blocked_patron(test_db):
    """Create a test patron with blocked status (administrative block)."""
    from app.core.security import hash_password

    user = User(
        email="blocked@example.com",
        password_hash=hash_password("BlockedPassword123!"),
        first_name="Blocked",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        patron_status=PatronStatus.BLOCKED,
        block_reason="Lost library materials",
        blocked_at=datetime.now(),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_deceased_patron(test_db):
    """Create a test patron marked as deceased."""
    from app.core.security import hash_password
    from datetime import date

    user = User(
        email="deceased@example.com",
        password_hash=hash_password("DeceasedPassword123!"),
        first_name="Deceased",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        patron_status=PatronStatus.DECEASED,
        date_of_death=date(2024, 1, 15),
        deceased_marked_at=datetime.now(),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_item_with_pending_hold(test_db, test_catalog_item_with_barcode):
    """Create a pending hold on an item."""
    from app.core.security import hash_password

    # Create another patron who has a pending hold
    hold_patron = User(
        email="holdpatron@example.com",
        password_hash=hash_password("HoldPassword123!"),
        first_name="Hold",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(hold_patron)
    await test_db.commit()
    await test_db.refresh(hold_patron)

    # Mark item as checked out first (holds are on checked-out items)
    test_catalog_item_with_barcode.status = ItemStatus.checked_out

    hold = Hold(
        user_id=hold_patron.id,
        item_id=test_catalog_item_with_barcode.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    return {"item": test_catalog_item_with_barcode, "hold": hold, "hold_patron": hold_patron}


@pytest.fixture
async def test_item_with_ready_hold(test_db, test_patron):
    """Create a ready hold on an available item for test_patron."""
    from app.models.catalog import CatalogItem

    # Create item
    item = CatalogItem(
        title="Ready Hold Book",
        author="Hold Author",
        isbn="978-0-222222-22-2",
        description="A book ready for pickup",
        status=ItemStatus.on_hold,
        call_number="HOLD-001",
        publication_year=2024,
        barcode="HOLD-BARCODE-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Create ready hold for test_patron
    hold = Hold(
        user_id=test_patron.id,
        item_id=item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=7),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    return {"item": item, "hold": hold}


@pytest.fixture
async def test_item_with_hold_for_other_patron(test_db, test_patron):
    """Create a ready hold for a different patron."""
    from app.core.security import hash_password
    from app.models.catalog import CatalogItem

    # Create another patron
    other_patron = User(
        email="otherhold@example.com",
        password_hash=hash_password("OtherHoldPassword123!"),
        first_name="Other",
        last_name="HoldPatron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(other_patron)
    await test_db.commit()
    await test_db.refresh(other_patron)

    # Create item
    item = CatalogItem(
        title="Other Hold Book",
        author="Other Author",
        isbn="978-0-333333-33-3",
        description="A book on hold for another patron",
        status=ItemStatus.on_hold,
        call_number="OTHER-001",
        publication_year=2024,
        barcode="OTHER-HOLD-BARCODE",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Create ready hold for other patron
    hold = Hold(
        user_id=other_patron.id,
        item_id=item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=7),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    return {"item": item, "hold": hold, "other_patron": other_patron}


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


# =============================================================================
# BARCODE SCANNING UNIT TESTS
# =============================================================================


# =============================================================================
# STAFF CHECKOUT INTEGRATION TESTS - BARCODE SCANNING
# =============================================================================


@pytest.mark.integration
class TestStaffCheckoutBarcodeScanning:
    """Integration tests for staff checkout with barcode scanning."""

    async def test_staff_checkout_with_valid_barcode(
        self, client, test_staff, test_staff_data, test_patron, test_catalog_item_with_barcode
    ):
        """Test successful staff checkout using barcode."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["user_id"] == test_patron.id
        assert data["item_id"] == test_catalog_item_with_barcode.id
        assert data["status"] == "active"
        assert data["item_title"] == test_catalog_item_with_barcode.title

    async def test_staff_checkout_with_codabar_barcode(
        self, client, test_staff, test_staff_data, test_patron, test_catalog_item_codabar
    ):
        """Test staff checkout with Codabar format barcode."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": test_catalog_item_codabar.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["item_title"] == "Codabar Book"

    async def test_staff_checkout_with_code39_barcode(
        self, client, test_staff, test_staff_data, test_patron, test_catalog_item_code39
    ):
        """Test staff checkout with Code 39 format barcode."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": test_catalog_item_code39.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["item_title"] == "Code 39 Book"

    async def test_staff_checkout_invalid_barcode_not_found(
        self, client, test_staff, test_staff_data, test_patron
    ):
        """Test staff checkout fails with non-existent barcode."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": "NONEXISTENT-BARCODE-XYZ",
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "barcode" in response.json()["error"]["message"].lower()

    async def test_staff_checkin_by_barcode_success(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff checkin by barcode scanning."""
        # First checkout the item
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        checkin_data = {"barcode": test_catalog_item_with_barcode.barcode}
        response = await client.post(
            f"/api/v1/staff/checkin-barcode?barcode={checkin_data['barcode']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkout" in data
        assert data["checkout"]["status"] == "returned"

    async def test_staff_checkin_by_barcode_no_active_checkout(
        self, client, test_staff, test_staff_data, test_catalog_item_with_barcode
    ):
        """Test staff checkin by barcode fails when no active checkout."""
        token = await get_staff_token(client, test_staff_data)
        checkin_data = {"barcode": test_catalog_item_with_barcode.barcode}
        response = await client.post(
            f"/api/v1/staff/checkin-barcode?barcode={checkin_data['barcode']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # staff_checkin_by_barcode wraps all lookup failures as a generic 400.
        assert response.status_code == 400
        assert "no active checkout" in response.json()["error"]["message"].lower()


# =============================================================================
# STAFF CHECKOUT INTEGRATION TESTS - MANUAL ENTRY
# =============================================================================


@pytest.mark.integration
class TestStaffCheckoutManualEntry:
    """Integration tests for staff checkout with manual patron/item entry."""

    async def test_manual_entry_checkout_by_patron_id(
        self, client, test_staff, test_staff_data, test_patron, test_catalog_item_with_barcode
    ):
        """Test staff checkout by manually entering patron ID and barcode."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["user_id"] == test_patron.id

    async def test_manual_entry_patron_not_found(
        self, client, test_staff, test_staff_data, test_catalog_item_with_barcode
    ):
        """Test checkout fails when manually entered patron ID doesn't exist."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": 99999,  # Non-existent patron
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "patron" in response.json()["error"]["message"].lower()

    async def test_manual_entry_item_already_checked_out(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test checkout fails when item is already checked out to same patron."""
        # First checkout
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Already-checked-out is a ConflictError (409), not a generic 400.
        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    async def test_manual_checkin_by_checkout_id(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff can checkin using checkout ID instead of barcode."""
        # Create checkout
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"


# =============================================================================
# CHECKOUT OVERRIDES FOR BLOCKED/SUSPENDED/DECEASED PATRONS
# =============================================================================


@pytest.mark.integration
class TestStaffCheckoutOverrides:
    """Tests for staff checkout overrides for patron status restrictions."""

    async def test_staff_can_override_suspended_patron(
        self,
        client,
        test_staff,
        test_staff_data,
        test_suspended_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff CAN checkout for a suspended patron (override allowed)."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_suspended_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Staff should be able to override suspension
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["user_id"] == test_suspended_patron.id
        assert data["status"] == "active"

    async def test_staff_cannot_override_blocked_patron(
        self,
        client,
        test_staff,
        test_staff_data,
        test_blocked_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff CANNOT checkout for a blocked patron (no override)."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_blocked_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Staff cannot override administrative blocks
        assert response.status_code == 403
        detail = response.json()["detail"].lower()
        assert "blocked" in detail or "lost" in detail

    async def test_staff_cannot_override_deceased_patron(
        self,
        client,
        test_staff,
        test_staff_data,
        test_deceased_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff CANNOT checkout for a deceased patron (no override)."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_deceased_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Staff cannot override deceased status
        assert response.status_code == 403
        assert "deceased" in response.json()["detail"].lower()

    async def test_staff_checkout_inactive_patron_blocked(
        self, client, test_db, test_staff, test_staff_data, test_catalog_item_with_barcode
    ):
        """Test staff cannot checkout for an inactive patron."""
        from app.core.security import hash_password

        inactive_patron = User(
            email="inactive@example.com",
            password_hash=hash_password("InactivePassword123!"),
            first_name="Inactive",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=False,  # Inactive account
            email_verified=True,
        )
        test_db.add(inactive_patron)
        await test_db.commit()
        await test_db.refresh(inactive_patron)

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": inactive_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # is_active=False is a ForbiddenError (403), not a generic 400.
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    async def test_staff_override_renew_for_suspended_patron(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_suspended_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff can override renew for suspended patron."""
        # Create checkout for suspended patron
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_suspended_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["renewal_count"] == 1

    async def test_staff_can_override_expired_card_checkout(
        self, client, test_db, test_staff, test_staff_data, test_catalog_item_with_barcode
    ):
        """Test staff can checkout for patron with expired library card."""
        from app.core.security import hash_password

        expired_card_patron = User(
            email="expiredcard@example.com",
            password_hash=hash_password("ExpiredPassword123!"),
            first_name="Expired",
            last_name="Card",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=datetime.now() - timedelta(days=30),  # Expired 30 days ago
        )
        test_db.add(expired_card_patron)
        await test_db.commit()
        await test_db.refresh(expired_card_patron)

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": expired_card_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Staff can override expired card
        assert response.status_code == 201


# =============================================================================
# HANDLING ITEMS WITH HOLDS DURING CHECKOUT
# =============================================================================


@pytest.mark.integration
class TestStaffCheckoutWithHolds:
    """Tests for staff checkout when items have holds."""

    async def test_checkout_fulfills_ready_hold_for_patron(
        self, client, test_db, test_staff, test_staff_data, test_patron, test_item_with_ready_hold
    ):
        """Test that checkout fulfills a ready hold for the same patron."""
        item = test_item_with_ready_hold["item"]
        hold = test_item_with_ready_hold["hold"]

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": item.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201

        # Verify hold was fulfilled
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.fulfilled

    async def test_checkout_blocked_when_hold_for_different_patron(
        self, client, test_staff, test_staff_data, test_patron, test_item_with_hold_for_other_patron
    ):
        """Test that checkout is blocked when item is on hold for a different patron."""
        item = test_item_with_hold_for_other_patron["item"]

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "patron_id": test_patron.id,  # Try to checkout for different patron
            "barcode": item.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # ITEM_ON_HOLD is a ConflictError (409), not a generic 400.
        assert response.status_code == 409
        assert "hold" in response.json()["detail"].lower()

    async def test_checkin_promotes_next_pending_hold(
        self, client, test_db, test_staff, test_staff_data, test_patron, test_item_with_pending_hold
    ):
        """Test that checkin promotes the next pending hold to ready."""
        item = test_item_with_pending_hold["item"]
        hold = test_item_with_pending_hold["hold"]
        _ = test_item_with_pending_hold["hold_patron"]

        # Create a checkout for test_patron
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify hold is now ready
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert hold.expires_at is not None

    async def test_checkin_by_barcode_promotes_hold(
        self, client, test_db, test_staff, test_staff_data, test_patron, test_item_with_pending_hold
    ):
        """Test checkin by barcode also promotes holds."""
        item = test_item_with_pending_hold["item"]
        hold = test_item_with_pending_hold["hold"]

        # Create a checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        checkin_data = {"barcode": item.barcode}
        response = await client.post(
            f"/api/v1/staff/checkin-barcode?barcode={checkin_data['barcode']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify hold was promoted
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.ready

    async def test_staff_override_renew_with_holds(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff can override renew even when item has holds."""
        from app.core.security import hash_password

        # Create a checkout
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Create another patron with a hold on this item
        hold_patron = User(
            email="holdwaiting@example.com",
            password_hash=hash_password("HoldWaitingPassword123!"),
            first_name="Waiting",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(hold_patron)
        await test_db.commit()
        await test_db.refresh(hold_patron)

        hold = Hold(
            user_id=hold_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        # Staff override renewal does NOT bypass hold restrictions --
        # app/api/v1/staff/circulation_checkin.py::staff_override_renew is
        # explicit that "the hold queue still applies, so a waiting patron
        # is never bumped." Only the overdue-grace cutoff (always) and the
        # renewal cap (with override=True) are bypassed.
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        await test_db.refresh(checkout)
        assert checkout.renewal_count == 0

    async def test_checkin_sets_item_available_no_holds(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test checkin sets item to available when no holds exist."""
        # Create checkout
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify item is available
        await test_db.refresh(test_catalog_item_with_barcode)
        assert test_catalog_item_with_barcode.status == ItemStatus.available

    async def test_checkin_sets_item_on_hold_with_pending_holds(
        self, client, test_db, test_staff, test_staff_data, test_patron, test_item_with_pending_hold
    ):
        """Test checkin sets item to on_hold when pending holds exist."""
        item = test_item_with_pending_hold["item"]

        # Create checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify item is on_hold
        await test_db.refresh(item)
        assert item.status == ItemStatus.on_hold


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


@pytest.mark.integration
class TestStaffCheckoutEdgeCases:
    """Edge cases and error handling for staff checkout."""

    async def test_checkout_requires_staff_role(
        self, client, test_patron, test_user_data, test_catalog_item_with_barcode
    ):
        """Test that checkout endpoint requires staff role."""
        # Login as patron
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        token = response.json()["access_token"]

        checkout_data = {
            "patron_id": test_patron.id,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_checkout_unauthenticated_returns_401(
        self, client, test_catalog_item_with_barcode
    ):
        """Test that checkout without authentication returns 401."""
        checkout_data = {
            "patron_id": 1,
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
            json=checkout_data,
        )
        assert response.status_code == 401

    async def test_checkin_already_returned_fails(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test checkin fails for already returned item."""
        # Create returned checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.returned,
            checked_out_at=datetime.now() - timedelta(days=7),
            due_date=datetime.now() + timedelta(days=14),
            returned_at=datetime.now() - timedelta(days=1),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "already been returned" in response.json()["error"]["message"].lower()

    async def test_override_renew_already_returned_fails(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test override renew fails for returned checkout."""
        # Create returned checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.returned,
            checked_out_at=datetime.now() - timedelta(days=7),
            due_date=datetime.now() + timedelta(days=14),
            returned_at=datetime.now() - timedelta(days=1),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/override-renew/{checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # renew_checkout raises ConflictError (409) for a non-active checkout.
        assert response.status_code == 409

    async def test_checkin_nonexistent_checkout_fails(self, client, test_staff, test_staff_data):
        """Test checkin fails for non-existent checkout ID."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/circulation/checkin?checkout_id=99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "couldn't find" in response.json()["error"]["message"].lower()

    async def test_list_checkouts_with_filters(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test staff can list checkouts filtered to one patron.

        Redirected to GET /api/v1/staff/patrons/{patron_id}/checkouts
        (app/api/v1/staff/patron_operations.py:2253), the scoped successor
        to the deleted flat GET /api/v1/staff/checkouts?patron_id= listing
        (removed 2026-02-15, b2013f01b) -- this test only ever needed the
        single-patron case, which the successor covers exactly.
        """
        # Create checkout
        test_catalog_item_with_barcode.status = ItemStatus.checked_out
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)

        # Test with patron filter
        response = await client.get(
            f"/api/v1/staff/patrons/{test_patron.id}/checkouts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for checkout in data:
            assert checkout["user_id"] == test_patron.id

    async def test_multiple_items_checkout_sequence(
        self, client, test_db, test_staff, test_staff_data, test_patron
    ):
        """Test checking out multiple items in sequence."""
        from app.models.catalog import CatalogItem

        # Create multiple items
        items = []
        for i in range(3):
            item = CatalogItem(
                title=f"Sequence Book {i}",
                author="Sequence Author",
                isbn=f"978-0-{i}00000-00-{i}",
                description=f"Sequence test book {i}",
                status=ItemStatus.available,
                call_number=f"SEQ-00{i}",
                publication_year=2024,
                barcode=f"SEQ-BARCODE-{i}",
            )
            test_db.add(item)
            items.append(item)
        await test_db.commit()
        for item in items:
            await test_db.refresh(item)

        token = await get_staff_token(client, test_staff_data)

        # Checkout all items
        for item in items:
            checkout_data = {
                "patron_id": test_patron.id,
                "barcode": item.barcode,
            }
            response = await client.post(
                f"/api/v1/staff/patrons/{checkout_data['patron_id']}/quick-checkout",
                json=checkout_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 201

        # Verify all checkouts exist. GET /api/v1/staff/checkouts (flat,
        # all-patrons listing) was removed 2026-02-15 (b2013f01b) with no
        # 1:1 successor -- verify via a direct DB query instead of the
        # missing endpoint (see test_list_checkouts_with_filters above,
        # which redirects to the scoped per-patron successor where that's
        # sufficient; here we want a hard count so a DB check is more
        # direct anyway).
        from sqlalchemy import select
        from app.models.circulation import Checkout, CheckoutStatus

        result = await test_db.execute(
            select(Checkout).where(
                Checkout.user_id == test_patron.id,
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            )
        )
        checkouts = result.scalars().all()
        assert len(checkouts) >= 3
