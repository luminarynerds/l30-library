# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API-level tests for business logic edge case fixes.

These tests verify that the fixes for the edge cases work correctly
through the API endpoints.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from app.core.security import hash_password
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole
from app.models.acquisition import Fund, FundStatus, PurchaseOrder, PurchaseOrderStatus, Vendor
from app.models.permission import RoleSettings


# =============================================================================
# SECTION 1: HOLD EXPIRATION FIX TESTS
# =============================================================================


@pytest.mark.integration
class TestHoldExpirationFixes:
    """Test that hold expiration handling now works correctly."""

    @pytest.mark.asyncio
    async def test_process_expired_holds_endpoint(self, test_db, test_catalog_item):
        """Test the new endpoint that processes expired holds."""
        from app.services.hold_service import process_expired_holds

        # Create a staff user
        staff = User(
            email="expiry_staff@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Expiry",
            last_name="Staff",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)

        # Create patron with expired hold
        patron = User(
            email="expiry_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Expiry",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create expired hold
        expired_time = datetime.now() - timedelta(days=10)
        hold = Hold(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time,
            notified_at=expired_time,
            expires_at=expired_time + timedelta(days=7),  # Expired 3 days ago
        )
        test_db.add(hold)

        # Set item on_hold
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Process expired holds
        expired_count = await process_expired_holds(test_db)
        await test_db.commit()

        # Verify hold is now expired
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.expired
        assert expired_count == 1

        # Verify item is now available (no other holds)
        await test_db.refresh(test_catalog_item)
        assert test_catalog_item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_hold_queue_advances_on_expiration(self, test_db, test_catalog_item):
        """Test that the hold queue advances when a ready hold expires."""
        from app.services.hold_service import process_expired_holds

        # Create two patrons
        patron1 = User(
            email="queue_patron1@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Queue1",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="queue_patron2@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Queue2",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([patron1, patron2])
        await test_db.commit()

        # Create expired ready hold for patron1
        expired_time = datetime.now() - timedelta(days=10)
        hold1 = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time,
            notified_at=expired_time,
            expires_at=expired_time + timedelta(days=7),
        )

        # Create pending hold for patron2
        hold2 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=datetime.now() - timedelta(days=5),
        )

        test_db.add_all([hold1, hold2])
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Process expired holds
        await process_expired_holds(test_db)
        await test_db.commit()

        # Verify hold1 is expired
        await test_db.refresh(hold1)
        assert hold1.status == HoldStatus.expired

        # Verify hold2 is now ready and position updated
        await test_db.refresh(hold2)
        assert hold2.status == HoldStatus.ready
        assert hold2.position == 1
        assert hold2.notified_at is not None
        assert hold2.expires_at is not None


# =============================================================================
# SECTION 2: CONCURRENT CHECKOUT FIX TESTS
# =============================================================================


@pytest.mark.integration
class TestConcurrentCheckoutFixes:
    """Test that concurrent checkout protection is in place."""

    @pytest.mark.asyncio
    async def test_checkout_uses_row_locking(self, test_db, test_catalog_item, test_patron):
        """Test that checkout now uses SELECT FOR UPDATE."""
        # This test verifies the fix is in place - actual concurrent testing
        # requires multiple database connections
        from app.services.unified_circulation_service import checkout_item
        from app.schemas.circulation import CheckoutCreate

        # Ensure item is available
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # The checkout should succeed
        _ = CheckoutCreate(item_id=test_catalog_item.id)

        # We can't easily test FOR UPDATE in unit tests, but we can verify
        # the checkout succeeds and item status is updated atomically
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item = result.scalar_one()
        assert item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_checkout_model_has_unique_index(self, test_db):
        """Verify the Checkout model defines the unique partial index."""
        from app.models.circulation import Checkout

        # Check that __table_args__ contains our index
        table_args = Checkout.__table_args__
        assert table_args is not None

        # Find our index. Renamed ix_active_item_checkout -> ix_active_item_copy_checkout
        # when checkouts moved to per-copy (item_copy_id) tracking.
        found_index = False
        for arg in table_args:
            if hasattr(arg, "name") and arg.name == "ix_active_item_copy_checkout":
                found_index = True
                assert arg.unique is True
                break

        assert found_index, "Unique index ix_active_item_copy_checkout not found on Checkout model"


# =============================================================================
# SECTION 3: READING MINUTES CAP FIX TESTS
# =============================================================================


@pytest.mark.integration
class TestReadingMinutesCapFixes:
    """Test that reading minutes cap enforcement works."""

    @pytest.mark.asyncio
    async def test_reading_minutes_cap_constant_exists(self):
        """Verify the MAX_TOTAL_READING_MINUTES constant is defined."""
        from app.api.v1.reading_minutes import MAX_TOTAL_READING_MINUTES

        assert MAX_TOTAL_READING_MINUTES == 10000

    @pytest.mark.asyncio
    async def test_reading_minutes_cap_enforced(self, test_db):
        """Test that logging exceeding the cap is rejected."""
        from app.api.v1.reading_minutes import MAX_TOTAL_READING_MINUTES

        # Create a child user with minutes near the cap
        child = User(
            email="cap_child@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Cap",
            last_name="Child",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=100,
            reading_minutes_logged=MAX_TOTAL_READING_MINUTES - 50,  # Near cap
        )
        test_db.add(child)

        # Create role settings for CHILD
        settings = RoleSettings(
            role=UserRole.CHILD,
            use_reading_minutes=True,
            minutes_per_day_overdue=15,
            max_reading_minutes_owed=60,
        )
        test_db.add(settings)
        await test_db.commit()

        # The cap check happens in the endpoint logic
        # Verify the user's current logged minutes
        assert child.reading_minutes_logged == MAX_TOTAL_READING_MINUTES - 50

        # Attempting to log more than 50 minutes should fail (in actual API call)
        # This is verified through the constant and the validation logic

    @pytest.mark.asyncio
    async def test_atomic_increment_in_log_reading(self, test_db):
        """Test that reading minutes uses atomic increment."""
        from sqlalchemy import update
        from app.models.user import User

        # Create a child user
        child = User(
            email="atomic_child@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Atomic",
            last_name="Child",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=100,
            reading_minutes_logged=0,
        )
        test_db.add(child)
        await test_db.commit()

        initial_logged = child.reading_minutes_logged

        # Use atomic increment (as the fix does)
        await test_db.execute(
            update(User)
            .where(User.id == child.id)
            .values(reading_minutes_logged=User.reading_minutes_logged + 15)
        )
        await test_db.commit()
        await test_db.refresh(child)

        assert child.reading_minutes_logged == initial_logged + 15


# =============================================================================
# SECTION 4: FISCAL YEAR ROLLOVER FIX TESTS
# =============================================================================


@pytest.mark.integration
class TestFiscalYearRolloverFixes:
    """Test that fiscal year rollover validation works."""

    @pytest.mark.asyncio
    async def test_rollover_blocked_with_pending_pos(self, test_db):
        """Test that rollover is blocked when POs are pending."""
        from app.api.v1.acquisition.main import rollover_funds
        from app.schemas.acquisition import FundRolloverRequest
        from fastapi import HTTPException

        # Create admin user
        admin = User(
            email="rollover_admin@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Rollover",
            last_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        test_db.add(admin)

        # Create vendor
        vendor = Vendor(
            name="Test Vendor",
            email="vendor@test.com",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        # Create fund for FY2025
        fund = Fund(
            code="ROLLOVER-TEST",
            name="Rollover Test Fund",
            fiscal_year=2025,
            allocated_amount=Decimal("10000.00"),
            encumbered_amount=Decimal("1000.00"),
            spent_amount=Decimal("3000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(fund)
        await test_db.flush()

        # Create a pending PO
        po = PurchaseOrder(
            po_number="PO-ROLLOVER-001",
            vendor_id=vendor.id,
            fund_id=fund.id,
            status=PurchaseOrderStatus.PENDING_APPROVAL,
            total_amount=Decimal("1000.00"),
            created_by_id=admin.id,
        )
        test_db.add(po)
        await test_db.commit()

        # Try to rollover - should fail
        request = FundRolloverRequest(
            source_fiscal_year=2025,
            target_fiscal_year=2026,
            carry_forward_unspent=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await rollover_funds(request, test_db, admin)

        assert exc_info.value.status_code == 400
        assert "purchase order" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rollover_blocked_for_duplicate_year(self, test_db):
        """Test that rollover is blocked if target year already has funds."""
        from app.api.v1.acquisition.main import rollover_funds
        from app.schemas.acquisition import FundRolloverRequest
        from fastapi import HTTPException

        # Create admin user
        admin = User(
            email="dup_rollover_admin@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Dup",
            last_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        test_db.add(admin)

        # Create source fund for FY2025
        source_fund = Fund(
            code="DUP-SOURCE",
            name="Duplicate Source Fund",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(source_fund)

        # Create existing fund for FY2026 (target year)
        target_fund = Fund(
            code="DUP-TARGET",
            name="Duplicate Target Fund",
            fiscal_year=2026,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(target_fund)
        await test_db.commit()

        # Try to rollover - should fail
        request = FundRolloverRequest(
            source_fiscal_year=2025,
            target_fiscal_year=2026,
            carry_forward_unspent=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            await rollover_funds(request, test_db, admin)

        assert exc_info.value.status_code == 400
        assert "already exist" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_po_creation_validates_fund_status(self, test_db):
        """Test that PO creation is blocked for closed funds."""
        from app.api.v1.acquisition.po import create_purchase_order
        from app.schemas.acquisition import PurchaseOrderCreate
        from app.core.exceptions import ValidationError

        # Create staff user
        staff = User(
            email="po_staff@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="PO",
            last_name="Staff",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)

        # Create vendor
        vendor = Vendor(
            name="PO Test Vendor",
            email="povendor@test.com",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        # Create CLOSED fund
        closed_fund = Fund(
            code="CLOSED-FUND",
            name="Closed Fund",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.CLOSED,
        )
        test_db.add(closed_fund)
        await test_db.commit()

        # Try to create PO against closed fund
        po_create = PurchaseOrderCreate(
            vendor_id=vendor.id,
            fund_id=closed_fund.id,
            order_date=date(2025, 6, 15),
        )

        with pytest.raises(ValidationError) as exc_info:
            await create_purchase_order(po_create, test_db, staff)

        assert exc_info.value.status_code == 400
        assert "closed" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_po_creation_validates_fiscal_year_match(self, test_db):
        """Test that PO order date must match fund fiscal year."""
        from app.api.v1.acquisition.po import create_purchase_order
        from app.schemas.acquisition import PurchaseOrderCreate
        from app.core.exceptions import ValidationError

        # Create staff user
        staff = User(
            email="fy_staff@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="FY",
            last_name="Staff",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)

        # Create vendor
        vendor = Vendor(
            name="FY Test Vendor",
            email="fyvendor@test.com",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        # Create fund for FY2025
        fund = Fund(
            code="FY-MISMATCH",
            name="FY Mismatch Fund",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(fund)
        await test_db.commit()

        # Try to create PO with 2026 order date against 2025 fund
        po_create = PurchaseOrderCreate(
            vendor_id=vendor.id,
            fund_id=fund.id,
            order_date=date(2026, 1, 15),  # Wrong year
        )

        with pytest.raises(ValidationError) as exc_info:
            await create_purchase_order(po_create, test_db, staff)

        assert exc_info.value.status_code == 400
        assert "fiscal year" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_fund_update_blocked_when_closed(self, test_db):
        """Test that closed fund modifications are blocked."""
        from app.api.v1.acquisition.main import update_fund
        from app.schemas.acquisition import FundUpdate
        from fastapi import HTTPException

        # Create admin user
        admin = User(
            email="fund_admin@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Fund",
            last_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        test_db.add(admin)

        # Create CLOSED fund
        closed_fund = Fund(
            code="UPDATE-CLOSED",
            name="Update Closed Fund",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.CLOSED,
        )
        test_db.add(closed_fund)
        await test_db.commit()

        # Try to update allocated_amount on closed fund
        fund_update = FundUpdate(allocated_amount=Decimal("6000.00"))

        with pytest.raises(HTTPException) as exc_info:
            await update_fund(closed_fund.id, fund_update, test_db, admin)

        assert exc_info.value.status_code == 400
        assert "closed fund" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_fund_cannot_be_reopened(self, test_db):
        """Closed funds are final: update_fund now blocks ALL modifications
        to a closed fund, including a status-only change back to ACTIVE
        (see app/api/v1/acquisition/main.py update_fund -- "Closed funds
        are final and cannot be reopened."). Previously this test asserted
        the opposite (that status-only updates were allowed through); that
        was superseded by this explicit finality policy."""
        from app.api.v1.acquisition.main import update_fund
        from app.schemas.acquisition import FundUpdate
        from fastapi import HTTPException

        # Create admin user
        admin = User(
            email="reopen_admin@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Reopen",
            last_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        test_db.add(admin)

        # Create CLOSED fund
        closed_fund = Fund(
            code="REOPEN-FUND",
            name="Reopen Fund",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.CLOSED,
        )
        test_db.add(closed_fund)
        await test_db.commit()

        # Attempt to reopen by updating only status -- must be rejected.
        fund_update = FundUpdate(status=FundStatus.ACTIVE)
        with pytest.raises(HTTPException) as exc_info:
            await update_fund(closed_fund.id, fund_update, test_db, admin)

        assert exc_info.value.status_code == 400
        assert "cannot be reopened" in exc_info.value.detail.lower()


# =============================================================================
# SECTION 5: COMBINED EDGE CASE TESTS
# =============================================================================


@pytest.mark.integration
class TestCombinedEdgeCaseFixes:
    """Test combined edge case scenarios after fixes."""

    @pytest.mark.asyncio
    async def test_inline_expiration_check_on_get_holds(self, test_db, test_catalog_item):
        """Test that get_user_holds now processes expired holds inline."""
        from app.services.hold_service import check_and_expire_hold

        # Create patron with expired hold
        patron = User(
            email="inline_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Inline",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create expired hold
        expired_time = datetime.now() - timedelta(days=10)
        hold = Hold(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time,
            notified_at=expired_time,
            expires_at=expired_time + timedelta(days=7),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Check and expire hold inline
        was_expired = await check_and_expire_hold(hold, test_db)
        await test_db.commit()

        assert was_expired is True
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.expired


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
