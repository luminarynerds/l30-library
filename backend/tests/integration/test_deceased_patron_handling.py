# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for deceased patron handling functionality.

These tests verify:
1. PatronStatus enum and deceased status checks
2. Circulation service blocks for deceased patrons
3. Staff endpoint to mark patron as deceased
4. Estate follow-up functionality
5. Notification to estate contacts
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole, PatronStatus
from app.core.error_codes import ErrorCode


# =============================================================================
# Auth Fixtures
# =============================================================================
# Module-local JWT fixtures, minted the same way as tests/api/v1/legal/
# test_legal_resources.py. The users come from the shared test_staff /
# test_admin conftest fixtures so get_current_user can load them via the
# overridden test_db session.


@pytest.fixture
async def admin_client(test_db, test_admin):
    """Async HTTP client authenticated as an admin via dependency override.

    The repo-standard auth pattern for endpoint tests (see conftest
    staff_client); minted JWTs trip verify_token's revocation check in the
    test environment.
    """
    from httpx import AsyncClient as _AsyncClient, ASGITransport
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with _AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# =============================================================================
# Model Tests
# =============================================================================


class TestPatronStatusEnum:
    """Test PatronStatus enum values and behavior."""

    async def test_patron_status_values(self):
        """Verify PatronStatus enum has expected values."""
        assert PatronStatus.ACTIVE == "active"
        assert PatronStatus.BLOCKED == "blocked"
        assert PatronStatus.SUSPENDED == "suspended"
        assert PatronStatus.DECEASED == "deceased"

    async def test_patron_status_is_string_enum(self):
        """Verify PatronStatus is a string enum for JSON serialization."""
        assert isinstance(PatronStatus.DECEASED, str)
        assert PatronStatus.DECEASED.value == "deceased"


class TestUserDeceasedProperties:
    """Test User model properties related to deceased status."""

    @pytest.fixture
    def deceased_patron(self):
        """Create a deceased patron for testing."""
        patron = User(
            id=1,
            email="deceased@example.com",
            password_hash="fakehash",
            first_name="John",
            last_name="Doe",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
            date_of_death=datetime(2025, 12, 15).date(),
            estate_contact_name="Jane Doe",
            estate_contact_email="jane@example.com",
        )
        return patron

    @pytest.fixture
    def active_patron(self):
        """Create an active patron for testing."""
        patron = User(
            id=2,
            email="active@example.com",
            password_hash="fakehash",
            first_name="Alice",
            last_name="Smith",
            role=UserRole.PATRON,
            patron_status=PatronStatus.ACTIVE,
            is_active=True,
        )
        return patron

    async def test_is_deceased_property(self, deceased_patron, active_patron):
        """Test is_deceased property correctly identifies deceased patrons."""
        assert deceased_patron.is_deceased is True
        assert active_patron.is_deceased is False

    async def test_can_access_account_blocked_for_deceased(self, deceased_patron, active_patron):
        """Test can_access_account returns False for deceased patrons."""
        assert deceased_patron.can_access_account is False
        assert active_patron.can_access_account is True

    async def test_can_circulate_blocked_for_deceased(self, deceased_patron, active_patron):
        """Test can_circulate returns False for deceased patrons."""
        assert deceased_patron.can_circulate is False
        assert active_patron.can_circulate is True


# =============================================================================
# Circulation Service Tests
# =============================================================================


@pytest.mark.asyncio
class TestCirculationDeceasedBlocking:
    """Test that circulation operations are blocked for deceased patrons."""

    @pytest.fixture
    async def setup_deceased_patron(self, db_session: AsyncSession):
        """Create a deceased patron with test data."""
        patron = User(
            email="deceased_test@example.com",
            password_hash="fakehash",
            first_name="Test",
            last_name="Deceased",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
            date_of_death=datetime(2025, 12, 1).date(),
            deceased_marked_at=datetime.now(timezone.utc),
        )
        db_session.add(patron)
        await db_session.flush()
        return patron

    @pytest.fixture
    async def setup_available_item(self, db_session: AsyncSession):
        """Create an available catalog item."""
        item = CatalogItem(
            title="Test Book",
            author="Test Author",
            isbn="9781234567890",
            barcode="TEST123",
            status=ItemStatus.available,
        )
        db_session.add(item)
        await db_session.flush()
        return item

    async def test_checkout_blocked_for_deceased_patron(
        self, db_session: AsyncSession, setup_deceased_patron, setup_available_item
    ):
        """Test that checkout is blocked for deceased patrons."""
        from app.services.unified_circulation_service import checkout_item
        from app.core.exceptions import ForbiddenError

        patron = setup_deceased_patron
        item = setup_available_item

        with pytest.raises(ForbiddenError) as exc_info:
            await checkout_item(patron, item.id, db_session, is_staff_operation=False)

        assert exc_info.value.code in [ErrorCode.PATRON_DECEASED, ErrorCode.PATRON_BLOCKED]
        assert "deceased" in exc_info.value.message.lower()

    async def test_checkout_blocked_for_deceased_even_with_staff_override(
        self, db_session: AsyncSession, setup_deceased_patron, setup_available_item
    ):
        """Test that checkout is blocked for deceased patrons even with staff override."""
        from app.services.unified_circulation_service import checkout_item
        from app.core.exceptions import ForbiddenError

        patron = setup_deceased_patron
        item = setup_available_item

        # Even with is_staff_operation=True, deceased should be blocked
        with pytest.raises(ForbiddenError) as exc_info:
            await checkout_item(patron, item.id, db_session, is_staff_operation=True)

        assert exc_info.value.code in [ErrorCode.PATRON_DECEASED, ErrorCode.PATRON_BLOCKED]

    async def test_hold_blocked_for_deceased_patron(
        self, db_session: AsyncSession, setup_deceased_patron, setup_available_item
    ):
        """Test that placing holds is blocked for deceased patrons."""
        from app.services.unified_circulation_service import place_hold
        from app.core.exceptions import ForbiddenError

        patron = setup_deceased_patron
        item = setup_available_item

        with pytest.raises(ForbiddenError) as exc_info:
            await place_hold(patron, item.id, db_session)

        assert exc_info.value.code in [ErrorCode.PATRON_DECEASED, ErrorCode.PATRON_BLOCKED]


# =============================================================================
# Staff Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
class TestMarkPatronDeceasedEndpoint:
    """Test the staff endpoint to mark patron as deceased."""

    @pytest.fixture
    async def setup_patron_with_items(self, db_session: AsyncSession):
        """Create a patron with checkouts and fines for testing."""
        patron = User(
            email="patron_with_items@example.com",
            password_hash="fakehash",
            first_name="Active",
            last_name="Patron",
            role=UserRole.PATRON,
            patron_status=PatronStatus.ACTIVE,
            is_active=True,
        )
        db_session.add(patron)
        await db_session.flush()

        # Create an item and checkout
        item = CatalogItem(
            title="Borrowed Book",
            author="Some Author",
            isbn="9780987654321",
            barcode="ITEM001",
            status=ItemStatus.checked_out,
        )
        db_session.add(item)
        await db_session.flush()

        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            # ck_checkout_due_after_checkout: due_date must follow checked_out_at
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=28),
            due_date=datetime.now(timezone.utc) - timedelta(days=7),  # Overdue
        )
        db_session.add(checkout)
        await db_session.flush()

        # Create a fine
        fine = Fine(
            user_id=patron.id,
            checkout_id=checkout.id,
            fine_type=FineType.overdue,
            amount=Decimal("5.00"),
            amount_paid=Decimal("0.00"),
            status=FineStatus.unpaid,
            description="Overdue fine",
        )
        db_session.add(fine)

        # Create a pending hold
        hold_item = CatalogItem(
            title="Hold Book",
            author="Hold Author",
            isbn="9781111111111",
            barcode="HOLD001",
            status=ItemStatus.available,
        )
        db_session.add(hold_item)
        await db_session.flush()

        hold = Hold(
            user_id=patron.id,
            item_id=hold_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        db_session.add(hold)

        await db_session.commit()
        return patron, item, checkout, fine, hold

    async def test_mark_patron_deceased_success(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        setup_patron_with_items,
    ):
        """Test successfully marking a patron as deceased."""
        patron, item, checkout, fine, hold = setup_patron_with_items

        response = await admin_client.post(
            f"/api/v1/staff/patrons/{patron.id}/mark-deceased",
            json={
                "date_of_death": "2025-12-01T00:00:00Z",
                "estate_contact_name": "Estate Contact",
                "estate_contact_email": "estate@example.com",
                "notes": "Test notes",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["patron_id"] == patron.id
        assert data["estate_followup_required"] is True
        assert data["outstanding_checkouts"] == 1
        assert float(data["outstanding_fines_amount"]) == 5.00

        # Verify patron is now deceased
        await db_session.refresh(patron)
        assert patron.patron_status == PatronStatus.DECEASED
        assert patron.is_active is False
        assert patron.estate_contact_name == "Estate Contact"

        # Verify hold was cancelled
        await db_session.refresh(hold)
        assert hold.status == HoldStatus.cancelled

    async def test_mark_patron_deceased_requires_admin(
        self,
        staff_client: AsyncClient,
        db_session: AsyncSession,
        setup_patron_with_items,
    ):
        """Test that marking patron deceased requires admin privileges."""
        patron, *_ = setup_patron_with_items

        response = await staff_client.post(
            f"/api/v1/staff/patrons/{patron.id}/mark-deceased",
            json={"notes": "Test"},
        )

        # Should be forbidden for non-admin staff
        assert response.status_code == 403

    async def test_cannot_mark_staff_as_deceased(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that staff accounts cannot be marked as deceased."""
        staff = User(
            email="staff_user@example.com",
            password_hash="fakehash",
            first_name="Staff",
            last_name="Member",
            role=UserRole.STAFF,
            patron_status=PatronStatus.ACTIVE,
            is_active=True,
        )
        db_session.add(staff)
        await db_session.commit()

        response = await admin_client.post(
            f"/api/v1/staff/patrons/{staff.id}/mark-deceased",
            json={},
        )

        assert response.status_code == 400
        assert "staff accounts" in response.json()["error"]["message"].lower()

    async def test_cannot_mark_already_deceased_patron(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that already deceased patron cannot be marked again."""
        patron = User(
            email="already_deceased@example.com",
            password_hash="fakehash",
            first_name="Already",
            last_name="Deceased",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
        )
        db_session.add(patron)
        await db_session.commit()

        response = await admin_client.post(
            f"/api/v1/staff/patrons/{patron.id}/mark-deceased",
            json={},
        )

        assert response.status_code == 400
        assert "already" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
class TestEstateOutstandingEndpoint:
    """Test the estate outstanding items endpoint."""

    @pytest.fixture
    async def setup_deceased_patron_with_items(self, db_session: AsyncSession):
        """Create a deceased patron with outstanding items."""
        patron = User(
            email="estate_test@example.com",
            password_hash="fakehash",
            first_name="Estate",
            last_name="Test",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
            date_of_death=datetime(2025, 12, 1).date(),
            estate_contact_name="Family Contact",
            estate_contact_email="family@example.com",
            estate_followup_required=True,
        )
        db_session.add(patron)
        await db_session.flush()

        item = CatalogItem(
            title="Outstanding Book",
            author="Author Name",
            isbn="9782222222222",
            barcode="OUT001",
            status=ItemStatus.checked_out,
        )
        db_session.add(item)
        await db_session.flush()

        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.overdue,
            # ck_checkout_due_after_checkout: due_date must follow checked_out_at
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=51),
            due_date=datetime.now(timezone.utc) - timedelta(days=30),
        )
        db_session.add(checkout)
        await db_session.flush()

        fine = Fine(
            user_id=patron.id,
            checkout_id=checkout.id,
            fine_type=FineType.lost_item,
            amount=Decimal("25.00"),
            amount_paid=Decimal("0.00"),
            status=FineStatus.unpaid,
            description="Lost item cost",
        )
        db_session.add(fine)
        await db_session.commit()

        return patron, item, checkout, fine

    async def test_get_estate_outstanding_items(
        self,
        staff_client: AsyncClient,
        setup_deceased_patron_with_items,
    ):
        """Test retrieving outstanding items for estate."""
        patron, item, checkout, fine = setup_deceased_patron_with_items

        response = await staff_client.get(
            f"/api/v1/staff/patrons/{patron.id}/estate-outstanding",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["patron_id"] == patron.id
        assert data["patron_name"] == "Estate Test"
        assert data["estate_contact_name"] == "Family Contact"
        assert len(data["checkouts"]) == 1
        assert len(data["fines"]) == 1
        assert float(data["total_fines_amount"]) == 25.00

    async def test_estate_outstanding_only_for_deceased(
        self,
        staff_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that endpoint only works for deceased patrons."""
        active_patron = User(
            email="active_patron@example.com",
            password_hash="fakehash",
            first_name="Active",
            last_name="User",
            role=UserRole.PATRON,
            patron_status=PatronStatus.ACTIVE,
            is_active=True,
        )
        db_session.add(active_patron)
        await db_session.commit()

        response = await staff_client.get(
            f"/api/v1/staff/patrons/{active_patron.id}/estate-outstanding",
        )

        assert response.status_code == 400
        assert "deceased" in response.json()["error"]["message"].lower()


# =============================================================================
# Error Code Tests
# =============================================================================


class TestPatronDeceasedErrorCode:
    """Test PATRON_DECEASED error code is properly defined."""

    async def test_error_code_exists(self):
        """Verify PATRON_DECEASED error code exists."""
        assert hasattr(ErrorCode, "PATRON_DECEASED")
        assert ErrorCode.PATRON_DECEASED == "PATRON_DECEASED"

    async def test_error_code_has_message(self):
        """Verify PATRON_DECEASED has an error message."""
        from app.core.error_codes import ERROR_MESSAGES

        assert ErrorCode.PATRON_DECEASED in ERROR_MESSAGES
        assert "deceased" in ERROR_MESSAGES[ErrorCode.PATRON_DECEASED].lower()

    async def test_error_code_has_status(self):
        """Verify PATRON_DECEASED maps to correct HTTP status."""
        from app.core.error_codes import ERROR_CODE_TO_STATUS

        assert ErrorCode.PATRON_DECEASED in ERROR_CODE_TO_STATUS
        assert ERROR_CODE_TO_STATUS[ErrorCode.PATRON_DECEASED] == 403


# =============================================================================
# Suspension Service Tests
# =============================================================================


@pytest.mark.asyncio
class TestSuspensionServiceDeceasedHandling:
    """Test that suspension service correctly handles deceased patrons."""

    async def test_check_patron_suspension_status_deceased(self, db_session: AsyncSession):
        """Test check_patron_suspension_status returns correct values for deceased."""
        from app.services.suspension_service import check_patron_suspension_status

        patron = User(
            email="deceased_check@example.com",
            password_hash="fakehash",
            first_name="Check",
            last_name="Deceased",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
        )
        db_session.add(patron)
        await db_session.flush()

        can_circulate, reason, error_code = await check_patron_suspension_status(patron, db_session)

        assert can_circulate is False
        assert "deceased" in reason.lower()
        assert error_code == ErrorCode.PATRON_DECEASED

    async def test_cannot_suspend_deceased_patron(self, db_session: AsyncSession):
        """Test that deceased patrons cannot be suspended."""
        from app.services.suspension_service import suspend_patron
        from app.core.exceptions import ConflictError

        patron = User(
            email="deceased_suspend@example.com",
            password_hash="fakehash",
            first_name="Suspend",
            last_name="Deceased",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
        )
        db_session.add(patron)
        await db_session.flush()

        with pytest.raises(ConflictError) as exc_info:
            await suspend_patron(patron, db_session, reason="Test suspension")

        assert "deceased" in exc_info.value.message.lower()

    async def test_cannot_block_deceased_patron(self, db_session: AsyncSession):
        """Test that deceased patrons cannot be blocked."""
        from app.services.suspension_service import block_patron
        from app.core.exceptions import ConflictError

        patron = User(
            email="deceased_block@example.com",
            password_hash="fakehash",
            first_name="Block",
            last_name="Deceased",
            role=UserRole.PATRON,
            patron_status=PatronStatus.DECEASED,
            is_active=False,
        )
        db_session.add(patron)
        await db_session.flush()

        with pytest.raises(ConflictError) as exc_info:
            await block_patron(patron, db_session, reason="Test block", blocked_by_id=1)

        assert "deceased" in exc_info.value.message.lower()
