# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-level tests for the next-up hold info returned by checkin_by_barcode.

Covers the staff hold-trap card feature: when a returned item is the next
available copy for an active pending hold, the service must return a
NextHoldInfo payload (patron initials + shelf slot) alongside the checkout.
"""
from datetime import datetime, timedelta

import pytest

from app.core.security import hash_password
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole
from app.services import checkout_service as cs
from app.services.unified_circulation_service import checkin_by_barcode


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _bypass_catalog_cache(monkeypatch):
    """Skip Redis-dependent cache invalidation in unit tests.

    The cache module raises AttributeError when no Redis is reachable
    (client is None). Tests don't care about cache state, so stub it.
    """
    async def _noop():
        return 0

    # Cache invalidation now lives in the circulation core (return_checkout).
    monkeypatch.setattr(cs, "invalidate_catalog_cache", _noop)


async def _make_item(db, barcode: str = "TRAP-CARD-001") -> CatalogItem:
    item = CatalogItem(
        title="Trap Card Test Book",
        author="Trap Author",
        status=ItemStatus.checked_out,
        barcode=barcode,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_patron(db, email: str, first: str, last: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("TrapPass123!"),
        first_name=first,
        last_name=last,
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_active_checkout(db, user_id: int, item_id: int) -> Checkout:
    now = datetime.now()
    checkout = Checkout(
        user_id=user_id,
        item_id=item_id,
        status=CheckoutStatus.active,
        checked_out_at=now,
        due_date=now + timedelta(days=21),
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)
    return checkout


async def test_checkin_returns_next_hold_when_one_is_queued(test_db):
    """Checkin of an item with a single pending hold returns NextHoldInfo."""
    item = await _make_item(test_db, barcode="TRAP-WITH-HOLD-001")
    item_barcode = item.barcode  # cache before any later expiration
    borrower = await _make_patron(test_db, "borrower-trap@example.com", "Borrow", "Borrower")
    await _make_active_checkout(test_db, borrower.id, item.id)

    next_patron = await _make_patron(test_db, "next-trap@example.com", "Felicity", "Trapsworth")
    hold = Hold(
        user_id=next_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    hold_id = hold.id

    _, _, next_hold_info, _ = await checkin_by_barcode(
        barcode=item_barcode, db=test_db
    )

    assert next_hold_info is not None
    assert next_hold_info.hold_id == hold_id
    assert next_hold_info.patron_first_name == "Felicity"
    assert next_hold_info.patron_last_initial == "T."
    assert next_hold_info.item_title == "Trap Card Test Book"
    # shelf_slot is null until staff assigns one (matches current
    # _process_hold_queue behaviour); the FE renders a graceful fallback.
    assert next_hold_info.shelf_slot is None
    # expires_at gets set by the service when the hold is promoted to ready.
    assert next_hold_info.expires_at is not None



async def test_checkin_returns_no_next_hold_when_queue_empty(test_db):
    """Checkin of an item with no pending holds returns None for next_hold."""
    item = await _make_item(test_db, barcode="TRAP-NO-HOLD-001")
    item_barcode = item.barcode
    borrower = await _make_patron(test_db, "solo-borrower@example.com", "Solo", "Borrower")
    await _make_active_checkout(test_db, borrower.id, item.id)

    _, _, next_hold_info, _ = await checkin_by_barcode(
        barcode=item_barcode, db=test_db
    )

    assert next_hold_info is None
