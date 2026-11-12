# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for card expiration in circulation operations.

Tests for:
- Checkout blocked for expired cards
- Renewal blocked for expired cards
- Hold placement blocked for expired cards
- Staff override for expired cards
- Grace period handling in circulation
- Consortium patron expiration
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole
from app.core.datetime_utils import utc_now


@pytest.mark.integration
class TestCheckoutCardExpiration:
    """Test card expiration during checkout operations."""

    @pytest.mark.asyncio
    async def test_checkout_blocked_for_expired_card(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that checkout is blocked for patrons with expired cards."""
        from app.core.security import hash_password
        from app.services.unified_circulation_service import checkout_item
        from app.core.exceptions import ForbiddenError
        from app.core.error_codes import ErrorCode

        # Create patron with expired card (30 days ago, past any grace period)
        patron = User(
            email="expired_card_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Expired",
            last_name="Card",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() - timedelta(days=30),
        )
        test_db.add(patron)
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()
        # No patron refresh: SQLite reloads card_expires_at tz-naive, which
        # breaks is_card_expired; expire_on_commit=False keeps the aware value

        # Attempt checkout should fail
        with pytest.raises(ForbiddenError) as exc_info:
            await checkout_item(
                patron=patron,
                item_id=test_catalog_item.id,
                db=test_db,
                is_staff_operation=False,
            )

        assert exc_info.value.code == ErrorCode.PATRON_CARD_EXPIRED
        assert "expired" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_checkout_allowed_within_grace_period(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that checkout is allowed within grace period."""
        from app.core.security import hash_password
        from app.services.unified_circulation_service import checkout_item

        # Create patron with recently expired card (3 days ago, within default 7-day grace)
        patron = User(
            email="grace_period_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Grace",
            last_name="Period",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() - timedelta(days=3),
        )
        test_db.add(patron)
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()
        # No patron refresh: SQLite reloads card_expires_at tz-naive

        # Checkout should succeed within grace period
        checkout_response, item = await checkout_item(
            patron=patron,
            item_id=test_catalog_item.id,
            db=test_db,
            is_staff_operation=False,
        )

        assert checkout_response is not None
        assert checkout_response.status == CheckoutStatus.active

    @pytest.mark.asyncio
    async def test_checkout_allowed_for_valid_card(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that checkout is allowed for patrons with valid cards."""
        from app.core.security import hash_password
        from app.services.unified_circulation_service import checkout_item

        # Create patron with valid card (expires in 1 year)
        patron = User(
            email="valid_card_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Valid",
            last_name="Card",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() + timedelta(days=365),
        )
        test_db.add(patron)
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()
        # No patron refresh: SQLite reloads card_expires_at tz-naive

        # Checkout should succeed
        checkout_response, item = await checkout_item(
            patron=patron,
            item_id=test_catalog_item.id,
            db=test_db,
            is_staff_operation=False,
        )

        assert checkout_response is not None
        assert checkout_response.status == CheckoutStatus.active

    @pytest.mark.asyncio
    async def test_checkout_allowed_without_expiration_date(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that checkout is allowed for patrons without expiration date set."""
        from app.core.security import hash_password
        from app.services.unified_circulation_service import checkout_item

        # Create patron without card expiration date
        patron = User(
            email="no_expiry_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="No",
            last_name="Expiry",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=None,
        )
        test_db.add(patron)
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()
        await test_db.refresh(patron)

        # Checkout should succeed
        checkout_response, item = await checkout_item(
            patron=patron,
            item_id=test_catalog_item.id,
            db=test_db,
            is_staff_operation=False,
        )

        assert checkout_response is not None
        assert checkout_response.status == CheckoutStatus.active


@pytest.mark.integration
class TestStaffOverrideExpiredCard:
    """Test staff override capability for expired cards."""

    @pytest.mark.asyncio
    async def test_staff_checkout_allowed_for_expired_card(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that staff can checkout for patrons with expired cards."""
        from app.core.security import hash_password
        from app.services.unified_circulation_service import checkout_item

        # Create patron with expired card
        patron = User(
            email="staff_override_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Staff",
            last_name="Override",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() - timedelta(days=60),  # Expired 60 days ago
        )
        test_db.add(patron)
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()
        await test_db.refresh(patron)

        # Staff checkout should succeed (is_staff_operation=True)
        checkout_response, item = await checkout_item(
            patron=patron,
            item_id=test_catalog_item.id,
            db=test_db,
            is_staff_operation=True,  # Staff override
        )

        assert checkout_response is not None
        assert checkout_response.status == CheckoutStatus.active


@pytest.mark.integration
class TestRenewalCardExpiration:
    """Test card expiration during renewal operations."""

    @pytest.mark.asyncio
    async def test_renewal_blocked_for_expired_card(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that renewal is blocked for patrons with expired cards."""
        from app.core.security import hash_password
        from app.services.checkout_service import renew_checkout
        from app.core.exceptions import ForbiddenError
        from app.core.error_codes import ErrorCode

        # Create patron with expired card
        patron = User(
            email="renewal_expired_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Renewal",
            last_name="Expired",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() - timedelta(days=30),
        )
        test_db.add(patron)
        await test_db.flush()

        # Create an active checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            due_date=utc_now() + timedelta(days=7),
            status=CheckoutStatus.active,
            checked_out_at=utc_now() - timedelta(days=14),
            renewal_count=0,
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        # Renewal should fail
        with pytest.raises(ForbiddenError) as exc_info:
            await renew_checkout(checkout, patron, db=test_db)

        assert exc_info.value.code == ErrorCode.PATRON_CARD_EXPIRED


@pytest.mark.integration
class TestHoldPlacementCardExpiration:
    """Test card expiration during hold placement."""

    @pytest.mark.asyncio
    async def test_hold_blocked_for_expired_card(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that hold placement is blocked for patrons with expired cards."""
        from app.core.security import hash_password
        from app.services.unified_circulation_service import place_hold
        from app.core.exceptions import ForbiddenError
        from app.core.error_codes import ErrorCode

        # Create patron with expired card
        patron = User(
            email="hold_expired_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Hold",
            last_name="Expired",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() - timedelta(days=30),
        )
        test_db.add(patron)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()
        # No patron refresh: SQLite reloads card_expires_at tz-naive

        # Hold placement should fail
        with pytest.raises(ForbiddenError) as exc_info:
            await place_hold(
                patron=patron,
                item_id=test_catalog_item.id,
                db=test_db,
            )

        assert exc_info.value.code == ErrorCode.PATRON_CARD_EXPIRED


@pytest.mark.integration
class TestCardExpirationMidSession:
    """Test card expiration edge cases during active checkout sessions."""

    @pytest.mark.asyncio
    async def test_existing_checkout_not_affected_by_expiration(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """
        Test that existing checkouts are not automatically affected
        when a card expires mid-session (user can still return items).
        """
        from app.core.security import hash_password

        # Create patron whose card will "expire" after checkout
        patron = User(
            email="mid_session_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Mid",
            last_name="Session",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            card_expires_at=utc_now() + timedelta(days=365),  # Valid for now
        )
        test_db.add(patron)
        await test_db.flush()

        # Create an existing checkout
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            due_date=utc_now() + timedelta(days=21),
            status=CheckoutStatus.active,
            checked_out_at=utc_now(),
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Simulate card expiration
        patron.card_expires_at = utc_now() - timedelta(days=1)
        await test_db.commit()

        # Verify checkout still exists and is active
        await test_db.refresh(checkout)
        assert checkout.status == CheckoutStatus.active

        # Patron can still return items (no card check on checkin)
        # This is intentional - we don't want to block returns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
