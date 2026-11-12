# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for quick_checkout_for_patron using unified circulation service.

Validates the refactored endpoint correctly delegates to checkout_item()
and covers all validation previously handled inline.
"""

from datetime import datetime, timedelta

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.user import PatronStatus, User, UserRole


@pytest.fixture
async def available_item(test_db):
    item = CatalogItem(
        title="Quick Checkout Test Book",
        author="Test Author",
        isbn="978-0-111111-11-1",
        description="Test book for quick checkout",
        status=ItemStatus.available,
        call_number="QC-001",
        publication_year=2025,
        barcode="QC-BARCODE-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def checked_out_item(test_db):
    """A zero-copy title with an active loan by another patron.

    Title status alone no longer blocks checkout; availability is decided by
    copy/loan counts. A title with no ItemCopy rows circulates as ONE virtual
    copy, so the active loan here makes it unavailable.
    """
    from app.core.security import hash_password

    borrower = User(
        email="current-borrower-qc@test.com",
        password_hash=hash_password("testpass123"),
        first_name="Current",
        last_name="Borrower",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(borrower)
    item = CatalogItem(
        title="Already Checked Out Book",
        author="Busy Author",
        isbn="978-0-222222-22-2",
        description="Already checked out",
        status=ItemStatus.checked_out,
        call_number="QC-002",
        publication_year=2025,
        barcode="QC-BARCODE-002",
    )
    test_db.add(item)
    await test_db.commit()

    checkout = Checkout(
        user_id=borrower.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def blocked_patron(test_db):
    from app.core.security import hash_password

    user = User(
        email="blocked-qc@test.com",
        password_hash=hash_password("testpass123"),
        first_name="Blocked",
        last_name="Patron",
        role=UserRole.PATRON,
        # patron_status is the canonical blocked signal; bare is_active=False
        # trips the legacy "Account is inactive" path instead.
        patron_status=PatronStatus.BLOCKED,
        is_active=False,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_quick_checkout_success(test_db, test_patron, available_item):
    """Successful checkout via unified service returns checkout response."""
    from app.services.unified_circulation_service import checkout_item

    response, item = await checkout_item(
        patron=test_patron,
        item_id=available_item.id,
        db=test_db,
        is_staff_operation=True,
    )

    assert response.item_id == available_item.id
    assert response.user_id == test_patron.id
    assert response.status == CheckoutStatus.active
    assert response.item_title == "Quick Checkout Test Book"
    assert response.due_date is not None


@pytest.mark.asyncio
async def test_quick_checkout_blocked_patron(test_db, blocked_patron, available_item):
    """Blocked patron raises ForbiddenError via unified service."""
    from app.core.exceptions import ForbiddenError
    from app.services.unified_circulation_service import checkout_item

    with pytest.raises(ForbiddenError, match="blocked"):
        await checkout_item(
            patron=blocked_patron,
            item_id=available_item.id,
            db=test_db,
            is_staff_operation=True,
        )


@pytest.mark.asyncio
async def test_quick_checkout_item_not_available(test_db, test_patron, checked_out_item):
    """Unavailable item (all copies on loan) raises ConflictError."""
    from app.core.error_codes import ErrorCode
    from app.core.exceptions import ConflictError
    from app.services.unified_circulation_service import checkout_item

    with pytest.raises(ConflictError) as exc_info:
        await checkout_item(
            patron=test_patron,
            item_id=checked_out_item.id,
            db=test_db,
            is_staff_operation=True,
        )
    assert exc_info.value.code == ErrorCode.ITEM_CHECKED_OUT


@pytest.mark.asyncio
async def test_quick_checkout_item_not_found(test_db, test_patron):
    """Non-existent item raises ResourceNotFoundError."""
    from app.core.exceptions import ResourceNotFoundError
    from app.services.unified_circulation_service import checkout_item

    with pytest.raises(ResourceNotFoundError):
        await checkout_item(
            patron=test_patron,
            item_id=999999,
            db=test_db,
            is_staff_operation=True,
        )


@pytest.mark.asyncio
async def test_quick_checkout_returns_correct_tuple(test_db, test_patron, available_item):
    """checkout_item returns (CheckoutResponse, CatalogItem) tuple."""
    from app.schemas.circulation import CheckoutResponse
    from app.services.unified_circulation_service import checkout_item

    result = await checkout_item(
        patron=test_patron,
        item_id=available_item.id,
        db=test_db,
        is_staff_operation=True,
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    checkout_response, item = result
    assert isinstance(checkout_response, CheckoutResponse)
    assert isinstance(item, CatalogItem)
    assert item.title == "Quick Checkout Test Book"


@pytest.mark.asyncio
async def test_quick_checkout_staff_skips_fine_check(test_db, test_patron, available_item):
    """Staff operations skip fine/card expiration checks."""
    from app.services.unified_circulation_service import checkout_item

    response, item = await checkout_item(
        patron=test_patron,
        item_id=available_item.id,
        db=test_db,
        is_staff_operation=True,
    )
    assert response.status == CheckoutStatus.active
