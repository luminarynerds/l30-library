# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for database models.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole


@pytest.mark.unit
class TestUserModel:
    """Test User model."""

    async def test_user_creation(self, test_db, test_patron):
        """Test creating a user."""
        assert test_patron.email == "testuser@example.com"
        assert test_patron.role == UserRole.PATRON
        assert test_patron.is_active is True

    async def test_user_full_name(self, test_db, test_patron):
        """Test user full name property."""
        assert test_patron.full_name == "Test User"

    async def test_user_role_types(self, test_db):
        """Test different user role types."""
        from app.models.user import UserRole

        assert hasattr(UserRole, "PATRON")
        assert hasattr(UserRole, "STAFF")
        assert hasattr(UserRole, "ADMIN")


@pytest.mark.unit
class TestCheckoutModel:
    """Test Checkout model."""

    async def test_checkout_creation(self, test_db, test_checkout):
        """Test creating a checkout."""
        assert test_checkout.user_id > 0
        assert test_checkout.item_id > 0
        assert test_checkout.status == CheckoutStatus.active

    async def test_checkout_status_enum(self, test_db):
        """Test checkout status enum values."""
        assert CheckoutStatus.active.value == "active"
        assert CheckoutStatus.returned.value == "returned"
        assert CheckoutStatus.overdue.value == "overdue"
        assert CheckoutStatus.lost.value == "lost"

    async def test_checkout_due_date(self, test_db, test_checkout):
        """Test checkout has valid due date."""
        # due_date is a DateTime(timezone=True) column -- comparing to a
        # naive datetime.now() raises TypeError once it's loaded back
        # tz-aware from the DB.
        assert test_checkout.due_date > datetime.now(timezone.utc)

    async def test_checkout_returned_at_nullable(self, test_db, test_checkout):
        """Test checkout returned_at is initially null."""
        assert test_checkout.returned_at is None


@pytest.mark.unit
class TestHoldModel:
    """Test Hold model."""

    async def test_hold_creation(self, test_db, test_hold):
        """Test creating a hold."""
        assert test_hold.user_id > 0
        assert test_hold.item_id > 0
        assert test_hold.status == HoldStatus.pending

    async def test_hold_status_enum(self, test_db):
        """Test hold status enum values."""
        assert HoldStatus.pending.value == "pending"
        assert HoldStatus.ready.value == "ready"
        assert HoldStatus.fulfilled.value == "fulfilled"
        assert HoldStatus.cancelled.value == "cancelled"

    async def test_hold_position_default(self, test_db, test_hold):
        """Test hold starts at position 1."""
        assert test_hold.position >= 1


@pytest.mark.unit
class TestFineModel:
    """Test Fine model."""

    async def test_fine_creation(self, test_db, test_fine):
        """Test creating a fine."""
        assert test_fine.user_id > 0
        assert test_fine.status == FineStatus.unpaid
        assert test_fine.amount == Decimal("10.00")

    async def test_fine_status_enum(self, test_db):
        """Test fine status enum values."""
        assert FineStatus.unpaid.value == "unpaid"
        assert FineStatus.paid.value == "paid"
        assert FineStatus.waived.value == "waived"
        assert FineStatus.partial.value == "partial"

    async def test_fine_type_enum(self, test_db):
        """Test fine type enum values."""
        assert FineType.overdue.value == "overdue"
        assert FineType.lost_item.value == "lost_item"
        assert FineType.damaged_item.value == "damaged_item"
        assert FineType.other.value == "other"

    async def test_fine_amount_decimal(self, test_db, test_fine):
        """Test fine amount is Decimal type."""
        assert isinstance(test_fine.amount, Decimal)
        assert test_fine.amount_paid == Decimal("0.00")


@pytest.mark.unit
class TestCatalogItemModel:
    """Test CatalogItem model."""

    async def test_catalog_item_creation(self, test_db, test_catalog_item):
        """Test creating a catalog item."""
        assert test_catalog_item.title == "Test Book"
        assert test_catalog_item.author == "Test Author"
        assert test_catalog_item.status == ItemStatus.available

    async def test_catalog_item_isbn(self, test_db, test_catalog_item):
        """Test catalog item ISBN."""
        assert test_catalog_item.isbn == "978-0-123456-78-9"

    @pytest.mark.skip(
        reason="Stale test, not a bug: CatalogItem never had a `language` column "
        "(confirmed -- no such field in app/models/catalog.py). Language now lives on "
        "the separate, optionally-linked BibframeWork.language (app/models/bibframe.py:193, "
        "ISO 639-2/B 3-letter default 'eng', not the 2-letter 'en' this test asserted). "
        "No default-language concept exists directly on CatalogItem to test."
    )
    async def test_catalog_item_language_default(self, test_db, test_catalog_item):
        """Test catalog item language."""
        assert test_catalog_item.language == "en"
