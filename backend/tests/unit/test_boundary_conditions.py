# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Boundary condition tests for the LSC Library system.

Tests critical boundary conditions throughout the system:
- Max checkout limit behavior
- Max holds limit behavior
- Max renewals limit behavior
- Fine calculations at maximum amounts
- Integer overflow in counts and amounts
- Empty states handling (no results, no history)
- Very long titles, names, and descriptions

Note: Service layer tests that require database connections are in a separate class.
Tests that only use models or the InputValidator can run without full app initialization.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set required environment variables before any app imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://lsc:lsc_dev_pwd@localhost:5432/lsc_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("SENTRY_DSN", "")

# Import input validator first (standalone, no circular imports)
from app.core.authorization import clear_permissions_cache
from app.core.input_validation import InputValidator, ValidationResult

# Import models
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType, FinePolicy, FinePolicyType
from app.models.permission import RoleSettings
from app.models.user import User, UserRole


# Helper to lazily import service functions to avoid circular imports at module load
def get_checkout_service_functions():
    """Lazily import checkout service functions."""
    from app.services.checkout_service import check_checkout_limit, renew_checkout
    return check_checkout_limit, renew_checkout


def get_fine_service_functions():
    """Lazily import fine service functions."""
    from app.services.fine_service import (
        get_user_fines_summary,
        record_fine_payment,
        get_user_fines,
    )
    return get_user_fines_summary, record_fine_payment, get_user_fines


@pytest.fixture(autouse=True)
def _clear_auth_cache():
    """Clear the authorization module's in-memory caches between every test.

    Role settings are cached module-wide with a TTL, so settings created by
    one test would otherwise leak into the next.
    """
    clear_permissions_cache()
    yield
    clear_permissions_cache()


# =============================================================================
# MAX CHECKOUT LIMIT BOUNDARY CONDITIONS
# =============================================================================


@pytest.mark.unit
class TestMaxCheckoutLimitBoundary:
    """Test behavior when patron hits max checkout limit."""

    async def test_checkout_at_exactly_max_limit(self, test_db, test_catalog_item):
        """Test that checkout fails when patron is at exactly max limit."""
        from app.core.security import hash_password
        from app.core.exceptions import BusinessLogicError

        # Create patron
        patron = User(
            email="max_checkout_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Max",
            last_name="Checkout",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create role settings with max_checkouts = 3
        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=3,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create 3 catalog items and check them all out
        items = []
        for i in range(3):
            item = CatalogItem(
                title=f"Test Book {i}",
                author="Test Author",
                isbn=f"978-0-{i:09d}-{i}",
                status=ItemStatus.available,
            )
            test_db.add(item)
            items.append(item)
        await test_db.commit()

        # Check out all 3 items. Keep references: the session's identity map
        # is weak, and rows reloaded from SQLite come back timezone-naive,
        # which crashes the limit problem-resolver's date math.
        checkouts = []
        for item in items:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(timezone.utc),
                due_date=datetime.now(timezone.utc) + timedelta(days=21),
            )
            test_db.add(checkout)
            checkouts.append(checkout)
            item.status = ItemStatus.checked_out
        await test_db.commit()

        # Now try to check out a 4th item - should fail
        new_item = CatalogItem(
            title="Fourth Book",
            author="Test Author",
            isbn="978-0-999999999-9",
            status=ItemStatus.available,
        )
        test_db.add(new_item)
        await test_db.commit()

        check_checkout_limit, _ = get_checkout_service_functions()
        with pytest.raises(BusinessLogicError) as exc_info:
            await check_checkout_limit(patron, test_db)

        assert "limit of 3 borrowed items" in str(exc_info.value.message)
        assert "(3/3)" in str(exc_info.value.message)

    async def test_checkout_one_below_max_limit_succeeds(self, test_db, test_catalog_item):
        """Test that checkout succeeds when patron is one below max limit."""
        from app.core.security import hash_password

        patron = User(
            email="below_limit_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Below",
            last_name="Limit",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=5,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create 4 active checkouts (one below max of 5)
        for i in range(4):
            item = CatalogItem(
                title=f"Book {i}",
                author="Author",
                isbn=f"978-1-{i:09d}-{i}",
                status=ItemStatus.checked_out,
            )
            test_db.add(item)
            await test_db.flush()

            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(timezone.utc),
                due_date=datetime.now(timezone.utc) + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Should not raise - patron can still checkout one more
        check_checkout_limit, _ = get_checkout_service_functions()
        await check_checkout_limit(patron, test_db)

    async def test_checkout_limit_includes_overdue_items(self, test_db, test_catalog_item):
        """Test that overdue items count toward checkout limit."""
        from app.core.security import hash_password
        from app.core.exceptions import BusinessLogicError

        patron = User(
            email="overdue_limit_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Overdue",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=2,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create 1 active and 1 overdue checkout. Keep references: the
        # session's identity map is weak, and rows reloaded from SQLite come
        # back timezone-naive, which crashes the limit problem-resolver.
        items = []
        checkouts = []
        for i, status in enumerate([CheckoutStatus.active, CheckoutStatus.overdue]):
            item = CatalogItem(
                title=f"Book {i}",
                author="Author",
                isbn=f"978-2-{i:09d}-{i}",
                status=ItemStatus.checked_out,
            )
            test_db.add(item)
            await test_db.flush()
            items.append(item)

            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=status,
                checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
                due_date=datetime.now(timezone.utc) - timedelta(days=9),
            )
            test_db.add(checkout)
            checkouts.append(checkout)
        await test_db.commit()

        # Should fail - both active and overdue count toward limit
        check_checkout_limit, _ = get_checkout_service_functions()
        with pytest.raises(BusinessLogicError) as exc_info:
            await check_checkout_limit(patron, test_db)

        assert "limit of 2 borrowed items" in str(exc_info.value.message)

    async def test_checkout_limit_excludes_returned_items(self, test_db):
        """Test that returned items don't count toward checkout limit."""
        from app.core.security import hash_password

        patron = User(
            email="returned_items_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Returned",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=2,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create 5 returned checkouts
        for i in range(5):
            item = CatalogItem(
                title=f"Returned Book {i}",
                author="Author",
                isbn=f"978-3-{i:09d}-{i}",
                status=ItemStatus.available,
            )
            test_db.add(item)
            await test_db.flush()

            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.returned,
                checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
                due_date=datetime.now(timezone.utc) - timedelta(days=9),
                returned_at=datetime.now(timezone.utc) - timedelta(days=8),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Should not raise - returned items don't count
        check_checkout_limit, _ = get_checkout_service_functions()
        await check_checkout_limit(patron, test_db)

    async def test_checkout_limit_zero(self, test_db):
        """Test behavior when max_checkouts is set to 0."""
        from app.core.security import hash_password
        from app.core.exceptions import BusinessLogicError

        patron = User(
            email="zero_limit_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Zero",
            last_name="Limit",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=0,  # No checkouts allowed
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        check_checkout_limit, _ = get_checkout_service_functions()
        with pytest.raises(BusinessLogicError) as exc_info:
            await check_checkout_limit(patron, test_db)

        assert "limit of 0 borrowed items" in str(exc_info.value.message)


# =============================================================================
# MAX HOLDS LIMIT BOUNDARY CONDITIONS
# =============================================================================


@pytest.mark.unit
class TestMaxHoldsLimitBoundary:
    """Test behavior when patron hits max holds limit."""

    async def test_hold_at_exactly_max_limit(self, test_db):
        """Test creating a hold when patron is at exactly max limit."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron = User(
            email="max_holds_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Max",
            last_name="Holds",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=3,  # Max 3 holds
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create 3 holds (at max)
        for i in range(3):
            item = CatalogItem(
                title=f"Hold Book {i}",
                author="Author",
                isbn=f"978-4-{i:09d}-{i}",
                status=ItemStatus.checked_out,
            )
            test_db.add(item)
            await test_db.flush()

            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=1,
                created_at=datetime.now(timezone.utc),
            )
            test_db.add(hold)
        await test_db.commit()

        # Count active holds
        result = await test_db.execute(
            select(Hold).where(
                Hold.user_id == patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        active_holds = result.scalars().all()
        assert len(active_holds) == 3

    async def test_hold_includes_pending_and_ready(self, test_db):
        """Test that both pending and ready holds count toward limit."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron = User(
            email="pending_ready_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Pending",
            last_name="Ready",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create 1 pending and 1 ready hold
        statuses = [HoldStatus.pending, HoldStatus.ready]
        for i, status in enumerate(statuses):
            item = CatalogItem(
                title=f"Hold Type Book {i}",
                author="Author",
                isbn=f"978-5-{i:09d}-{i}",
                status=ItemStatus.on_hold if status == HoldStatus.ready else ItemStatus.checked_out,
            )
            test_db.add(item)
            await test_db.flush()

            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=status,
                position=1,
                created_at=datetime.now(timezone.utc),
                notified_at=datetime.now(timezone.utc) if status == HoldStatus.ready else None,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7) if status == HoldStatus.ready else None,
            )
            test_db.add(hold)
        await test_db.commit()

        # Both should count toward active holds
        result = await test_db.execute(
            select(Hold).where(
                Hold.user_id == patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        active_holds = result.scalars().all()
        assert len(active_holds) == 2

    async def test_hold_excludes_fulfilled_cancelled_expired(self, test_db):
        """Test that fulfilled, cancelled, and expired holds don't count."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron = User(
            email="inactive_holds_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Inactive",
            last_name="Holds",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create holds with inactive statuses
        inactive_statuses = [HoldStatus.fulfilled, HoldStatus.cancelled, HoldStatus.expired]
        for i, status in enumerate(inactive_statuses):
            item = CatalogItem(
                title=f"Inactive Hold Book {i}",
                author="Author",
                isbn=f"978-6-{i:09d}-{i}",
                status=ItemStatus.available,
            )
            test_db.add(item)
            await test_db.flush()

            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=status,
                position=1,  # ck_hold_position_positive: position must be >= 1
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
            )
            test_db.add(hold)
        await test_db.commit()

        # None should count toward active holds
        result = await test_db.execute(
            select(Hold).where(
                Hold.user_id == patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        active_holds = result.scalars().all()
        assert len(active_holds) == 0


# =============================================================================
# MAX RENEWALS BOUNDARY CONDITIONS
# =============================================================================


@pytest.mark.unit
class TestMaxRenewalsBoundary:
    """Test behavior when patron hits max renewals limit."""

    async def test_renewal_at_exactly_max_limit(self, test_db, test_catalog_item):
        """Test that renewal fails when checkout is at exactly max renewals."""
        from app.core.security import hash_password
        from app.core.exceptions import BusinessLogicError

        patron = User(
            email="max_renewals_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Max",
            last_name="Renewals",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=2,  # Max 2 renewals
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create checkout that has already been renewed twice
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=60),
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            renewal_count=2,  # Already at max
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        _, renew_checkout = get_checkout_service_functions()
        with pytest.raises(BusinessLogicError) as exc_info:
            await renew_checkout(checkout, patron, test_db)

        assert "renewed this item the maximum number of times (2)" in str(exc_info.value.message)

    async def test_renewal_one_below_max_succeeds(self, test_db, test_catalog_item):
        """Test that renewal succeeds when one below max renewals."""
        from app.core.security import hash_password

        patron = User(
            email="below_max_renewals@example.com",
            password_hash=hash_password("password123"),
            first_name="Below",
            last_name="MaxRenewals",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=3,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create checkout with 2 renewals (one below max of 3)
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=60),
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            renewal_count=2,
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Should succeed
        _, renew_checkout = get_checkout_service_functions()
        await renew_checkout(checkout, patron, test_db)
        assert checkout.renewal_count == 3

    async def test_renewal_zero_limit(self, test_db, test_catalog_item):
        """Test behavior when max_renewals is 0."""
        from app.core.security import hash_password
        from app.core.exceptions import BusinessLogicError

        patron = User(
            email="zero_renewals_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="Zero",
            last_name="Renewals",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=0,  # No renewals allowed
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            renewal_count=0,
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        _, renew_checkout = get_checkout_service_functions()
        with pytest.raises(BusinessLogicError) as exc_info:
            await renew_checkout(checkout, patron, test_db)

        assert "maximum number of times (0)" in str(exc_info.value.message)

    async def test_renewal_blocked_by_hold(self, test_db, test_catalog_item):
        """Test that renewal fails when item has a pending hold."""
        from app.core.security import hash_password
        from app.core.exceptions import ConflictError

        patron = User(
            email="renewal_hold_blocked@example.com",
            password_hash=hash_password("password123"),
            first_name="Renewal",
            last_name="Blocked",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        other_patron = User(
            email="hold_placer@example.com",
            password_hash=hash_password("password123"),
            first_name="Hold",
            last_name="Placer",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        test_db.add(other_patron)
        await test_db.commit()

        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=5,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()

        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            renewal_count=0,
        )
        test_db.add(checkout)

        # Another patron has a hold on this item
        hold = Hold(
            user_id=other_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        _, renew_checkout = get_checkout_service_functions()
        with pytest.raises(ConflictError) as exc_info:
            await renew_checkout(checkout, patron, test_db)

        assert "someone else is waiting" in str(exc_info.value.message)


# =============================================================================
# FINE CALCULATIONS AT MAXIMUM AMOUNTS
# =============================================================================


@pytest.mark.unit
class TestFineCalculationMaximums:
    """Test fine calculations at maximum amounts and edge cases."""

    async def test_fine_for_very_long_overdue_period(self, test_db, test_patron, test_catalog_item):
        """Test fine amount calculation for extremely long overdue period (1000 days)."""
        # Calculate expected fine for 1000 days overdue at $0.25/day
        overdue_days = 1000
        fine_per_day = Decimal("0.25")
        expected_amount = fine_per_day * overdue_days  # $250.00

        # Create a fine record representing 1000 days overdue
        fine = Fine(
            user_id=test_patron.id,
            checkout_id=None,  # Can be None for manual fines
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=expected_amount,
            amount_paid=Decimal("0.00"),
            description=f"Overdue fine for {overdue_days} days",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        # Verify the large fine amount is stored correctly
        assert fine.amount == Decimal("250.00")
        assert fine.balance == Decimal("250.00")

    async def test_fine_policy_maximum_cap(self, test_db):
        """Test that fine policies with maximum_cap work correctly."""
        policy = FinePolicy(
            name="Capped Fine Policy",
            policy_type=FinePolicyType.daily_rate,
            fine_per_day=Decimal("0.50"),
            maximum_cap=Decimal("10.00"),  # Max $10 regardless of days
            is_active=True,
        )
        test_db.add(policy)
        await test_db.commit()

        assert policy.maximum_cap == Decimal("10.00")
        assert policy.fine_per_day == Decimal("0.50")

    async def test_fine_amount_decimal_precision(self, test_db, test_patron):
        """Test fine amount handles decimal precision correctly."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("123456.99"),  # Large amount with cents
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.amount == Decimal("123456.99")
        assert fine.balance == Decimal("123456.99")

    async def test_fine_payment_at_exact_balance(self, test_db, test_patron):
        """Test payment of exact remaining balance."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        # Pay exact balance
        _, record_fine_payment, _ = get_fine_service_functions()
        result = await record_fine_payment(fine.id, Decimal("10.00"), test_db)

        assert result.status == FineStatus.paid
        assert result.balance == Decimal("0.00")
        assert result.amount_paid == Decimal("10.00")

    async def test_fine_overpayment_capped(self, test_db, test_patron):
        """Test that overpayment is capped at balance."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        # Try to pay more than balance
        _, record_fine_payment, _ = get_fine_service_functions()
        result = await record_fine_payment(fine.id, Decimal("100.00"), test_db)

        # Should only pay up to balance
        assert result.amount_paid == Decimal("5.00")
        assert result.status == FineStatus.paid

    async def test_max_fine_amount_per_role_in_cents(self, test_db):
        """Test max_fine_amount is stored in cents (integer)."""
        role_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=99999,  # $999.99 in cents
            fine_exempt=False,
        )
        test_db.add(role_settings)
        await test_db.commit()
        await test_db.refresh(role_settings)

        assert role_settings.max_fine_amount == 99999
        # Convert to dollars
        max_fine_dollars = Decimal(str(role_settings.max_fine_amount)) / 100
        assert max_fine_dollars == Decimal("999.99")


# =============================================================================
# INTEGER OVERFLOW IN COUNTS AND AMOUNTS
# =============================================================================


@pytest.mark.unit
class TestIntegerOverflowProtection:
    """Test protection against integer overflow in counts and amounts."""

    async def test_renewal_count_large_value(self, test_db, test_catalog_item, test_patron):
        """Test that renewal_count handles large values correctly."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            renewal_count=2147483647,  # Max 32-bit signed integer
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        assert checkout.renewal_count == 2147483647

    async def test_hold_position_large_value(self, test_db, test_catalog_item, test_patron):
        """Test that hold position handles large values."""
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=999999999,  # Very large position
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        assert hold.position == 999999999

    async def test_reading_minutes_owed_large_value(self, test_db):
        """Test that reading_minutes_owed handles large values."""
        from app.core.security import hash_password

        user = User(
            email="large_minutes@example.com",
            password_hash=hash_password("password123"),
            first_name="Large",
            last_name="Minutes",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=2147483647,  # Max 32-bit signed int
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert user.reading_minutes_owed == 2147483647

    async def test_fine_amount_maximum_decimal(self, test_db, test_patron):
        """Test fine amount at maximum decimal precision."""
        # Numeric(10, 2) can store up to 99999999.99
        max_amount = Decimal("99999999.99")
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=max_amount,
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.amount == max_amount

    async def test_fine_partial_payment_precision(self, test_db, test_patron):
        """Test partial payments maintain decimal precision."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        # Make multiple small payments
        _, record_fine_payment, _ = get_fine_service_functions()
        await record_fine_payment(fine.id, Decimal("0.01"), test_db)
        await record_fine_payment(fine.id, Decimal("0.01"), test_db)
        await record_fine_payment(fine.id, Decimal("0.01"), test_db)

        # refresh() discards pending changes; flush the last payment first
        await test_db.flush()
        await test_db.refresh(fine)
        assert fine.amount_paid == Decimal("0.03")
        assert fine.balance == Decimal("9.97")


# =============================================================================
# EMPTY STATES HANDLING
# =============================================================================


@pytest.mark.unit
class TestEmptyStatesHandling:
    """Test handling of empty states (no results, no history)."""

    async def test_user_fines_summary_no_fines(self, test_db, test_patron):
        """Test fines summary when user has no fines."""
        get_user_fines_summary, _, _ = get_fine_service_functions()
        summary = await get_user_fines_summary(test_patron.id, test_db)

        assert summary["total_outstanding"] == Decimal("0")
        assert summary["total_paid"] == Decimal("0")
        assert summary["outstanding_count"] == 0
        assert summary["paid_count"] == 0
        assert summary["waived_count"] == 0

    async def test_user_fines_empty_list(self, test_db, test_patron):
        """Test get_user_fines returns empty list when no fines."""
        _, _, get_user_fines = get_fine_service_functions()
        fines = await get_user_fines(test_patron.id, test_db)
        assert fines == []

    async def test_checkout_history_empty(self, test_db, test_patron):
        """Test patron with no checkout history."""
        from sqlalchemy import select

        result = await test_db.execute(
            select(Checkout).where(Checkout.user_id == test_patron.id)
        )
        checkouts = result.scalars().all()
        assert len(checkouts) == 0

    async def test_hold_queue_empty(self, test_db, test_catalog_item):
        """Test item with empty hold queue."""
        from sqlalchemy import select

        result = await test_db.execute(
            select(Hold).where(
                Hold.item_id == test_catalog_item.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        holds = result.scalars().all()
        assert len(holds) == 0

    async def test_no_role_settings_defaults(self, test_db):
        """Test default values when no role settings exist."""
        from app.core.authorization import get_checkout_limit, get_max_renewals
        from app.core.security import hash_password

        # Create user without role settings
        patron = User(
            email="no_settings_patron@example.com",
            password_hash=hash_password("password123"),
            first_name="No",
            last_name="Settings",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Should fall back to defaults
        max_checkouts = await get_checkout_limit(patron, test_db)
        max_renewals = await get_max_renewals(patron, test_db)

        assert max_checkouts == 10  # Default
        assert max_renewals == 2  # Default

    async def test_fine_payment_history_empty(self, test_db, test_patron):
        """Test fine with no payment history."""
        from app.models.fine import FinePaymentHistory
        from sqlalchemy import select

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        history = result.scalars().all()
        assert len(history) == 0


# =============================================================================
# VERY LONG TITLES, NAMES, AND DESCRIPTIONS
# =============================================================================


@pytest.mark.unit
class TestVeryLongFieldValues:
    """Test handling of very long titles, names, and descriptions."""

    async def test_catalog_item_max_title_length(self, test_db):
        """Test catalog item with maximum title length (500 chars)."""
        max_title = "A" * 500  # Max length per model

        item = CatalogItem(
            title=max_title,
            author="Test Author",
            isbn="978-7-000000000-0",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert len(item.title) == 500
        assert item.title == max_title

    async def test_catalog_item_max_author_length(self, test_db):
        """Test catalog item with maximum author length (255 chars)."""
        max_author = "B" * 255  # Max length per model

        item = CatalogItem(
            title="Test Title",
            author=max_author,
            isbn="978-7-000000001-1",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert len(item.author) == 255

    async def test_catalog_item_max_description_length(self, test_db):
        """Test catalog item with very long description (Text field)."""
        # Text field can hold very large amounts
        long_description = "D" * 10000

        item = CatalogItem(
            title="Test Title",
            author="Test Author",
            isbn="978-7-000000002-2",
            description=long_description,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert len(item.description) == 10000

    async def test_user_name_max_lengths(self, test_db):
        """Test user with maximum name lengths."""
        from app.core.security import hash_password

        # String(100) for first_name and last_name
        max_first = "F" * 100
        max_last = "L" * 100

        user = User(
            email="long_name@example.com",
            password_hash=hash_password("password123"),
            first_name=max_first,
            last_name=max_last,
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert len(user.first_name) == 100
        assert len(user.last_name) == 100

    async def test_fine_description_max_length(self, test_db, test_patron):
        """Test fine with very long description (Text field)."""
        long_description = "Fine description: " + "X" * 5000

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.other,
            status=FineStatus.unpaid,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
            description=long_description,
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert len(fine.description) > 5000

    async def test_fine_notes_max_length(self, test_db, test_patron):
        """Test fine with very long notes (Text field)."""
        long_notes = "Notes: " + "N" * 10000

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.other,
            status=FineStatus.unpaid,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
            notes=long_notes,
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert len(fine.notes) > 10000

    async def test_input_validator_title_max_length(self):
        """Test input validator rejects titles exceeding max length."""
        validator = InputValidator()

        # Title max is 500 per InputValidator.MAX_LENGTHS
        too_long_title = "T" * 501

        result = validator._validate_string_field("title", too_long_title)

        assert not result.is_valid
        assert any("exceeds maximum length" in err for err in result.errors)

    async def test_input_validator_description_max_length(self):
        """Test input validator rejects descriptions exceeding max length."""
        validator = InputValidator()

        # Description max is 10000 per InputValidator.MAX_LENGTHS
        too_long_desc = "D" * 10001

        result = validator._validate_string_field("description", too_long_desc)

        assert not result.is_valid
        assert any("exceeds maximum length" in err for err in result.errors)

    async def test_input_validator_name_max_length(self):
        """Test input validator rejects names exceeding max length."""
        validator = InputValidator()

        # Name max is 255 per InputValidator.MAX_LENGTHS
        too_long_name = "N" * 256

        result = validator._validate_string_field("name", too_long_name)

        assert not result.is_valid
        assert any("exceeds maximum length" in err for err in result.errors)

    async def test_unicode_in_long_fields(self, test_db):
        """Test handling of unicode characters in long fields."""
        # Mix of unicode characters
        unicode_title = "书籍标题 " * 50 + "📚" * 50  # Chinese + emoji

        item = CatalogItem(
            title=unicode_title[:500],  # Truncate to max
            author="作者名",
            isbn="978-7-000000003-3",
            description="描述 " * 1000,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert "书籍" in item.title or "📚" in item.title


# =============================================================================
# ADDITIONAL EDGE CASES
# =============================================================================


@pytest.mark.unit
class TestAdditionalEdgeCases:
    """Additional boundary condition tests."""

    async def test_checkout_with_past_due_date(self, test_db, test_patron, test_catalog_item):
        """Test creating checkout with due date in the past (should be overdue)."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Verify the checkout exists with past due date
        assert checkout.due_date < datetime.now(timezone.utc)

    async def test_hold_with_far_future_expiration(self, test_db, test_patron, test_catalog_item):
        """Test hold with expiration far in the future."""
        from app.core.datetime_utils import ensure_utc

        future_date = datetime.now(timezone.utc) + timedelta(days=365 * 10)  # 10 years

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=datetime.now(timezone.utc),
            notified_at=datetime.now(timezone.utc),
            expires_at=future_date,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        # SQLite reloads the refreshed value timezone-naive
        assert ensure_utc(hold.expires_at) > datetime.now(timezone.utc)

    async def test_fine_with_zero_amount(self, test_db, test_patron):
        """Test fine with zero amount."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.other,
            status=FineStatus.unpaid,
            amount=Decimal("0.00"),
            amount_paid=Decimal("0.00"),
            description="Zero amount fine",
        )
        test_db.add(fine)
        await test_db.commit()

        assert fine.amount == Decimal("0.00")
        assert fine.balance == Decimal("0.00")

    async def test_payment_plan_progress_at_100_percent(self, test_db, test_patron):
        """Test payment plan at exactly 100% progress."""
        from app.models.fine import PaymentPlan, PaymentPlanStatus, PaymentPlanFrequency

        plan = PaymentPlan(
            user_id=test_patron.id,
            total_amount=Decimal("100.00"),
            installment_amount=Decimal("25.00"),
            frequency=PaymentPlanFrequency.monthly,
            status=PaymentPlanStatus.completed,
            amount_paid=Decimal("100.00"),
            payments_made=4,
            total_payments_expected=4,
        )
        test_db.add(plan)
        await test_db.commit()

        assert plan.progress_percentage == 100.0
        assert plan.remaining_balance == Decimal("0.00")

    async def test_payment_plan_zero_total_amount(self, test_db, test_patron):
        """Test payment plan with zero total (edge case for division)."""
        from app.models.fine import PaymentPlan, PaymentPlanStatus, PaymentPlanFrequency

        plan = PaymentPlan(
            user_id=test_patron.id,
            total_amount=Decimal("0.00"),
            installment_amount=Decimal("0.00"),
            frequency=PaymentPlanFrequency.monthly,
            status=PaymentPlanStatus.completed,
            amount_paid=Decimal("0.00"),
            payments_made=0,
            total_payments_expected=0,
        )
        test_db.add(plan)
        await test_db.commit()

        # Should return 100% (not divide by zero)
        assert plan.progress_percentage == 100.0

    async def test_special_characters_in_fields(self, test_db):
        """Test handling of special characters in text fields."""
        special_chars = "Test <script>alert('XSS')</script> & \"quotes\" 'apostrophe' @#$%^&*()[]{}|\\;:',.<>?/"

        item = CatalogItem(
            title=special_chars,
            author=special_chars[:200],
            isbn="978-7-000000004-4",
            description=special_chars * 10,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        # Should store special characters (HTML escaping happens at presentation layer)
        assert "<script>" in item.title

    async def test_input_validator_detects_script_injection(self):
        """Test that input validator detects script injection attempts."""
        validator = InputValidator()

        malicious_input = "Normal text <script>alert('XSS')</script> more text"

        result = validator._validate_string_field("title", malicious_input)

        assert not result.is_valid
        assert any("malicious" in err.lower() for err in result.errors)

    async def test_input_validator_detects_sql_injection(self):
        """Test that input validator detects SQL injection attempts."""
        validator = InputValidator()

        sql_injection = "'; DROP TABLE users; --"

        result = validator._validate_string_field("name", sql_injection)

        # SQL injection patterns should be detected
        assert not result.is_valid or len(result.warnings) > 0

    async def test_input_validator_detects_path_traversal(self):
        """Test that input validator detects path traversal attempts."""
        validator = InputValidator()

        path_traversal = "../../../etc/passwd"

        result = validator._validate_string_field("name", path_traversal)

        assert not result.is_valid
        assert any("path traversal" in err.lower() for err in result.errors)

    async def test_null_bytes_rejected(self):
        """Test that null bytes are rejected in input."""
        validator = InputValidator()

        null_byte_input = "normal\x00hidden"

        result = validator._validate_string_field("name", null_byte_input)

        assert not result.is_valid
        assert any("null bytes" in err.lower() for err in result.errors)
