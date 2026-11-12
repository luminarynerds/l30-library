# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for POST /circulation/holds/{hold_id}/checkout (one-click
staff checkout of a ready hold from the patron record)."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.core.security import hash_password
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.inventory import ItemCopy
from app.models.user import User, UserRole


# ============================================================================
# Helpers
# ============================================================================


async def _noop(*_args, **_kwargs):
    """No-op stub for invalidate_catalog_cache in no-Redis test env."""
    return 0


async def _make_patron(db, email="holdtest.patron@example.com"):
    """Create a basic active patron."""
    user = User(
        email=email,
        password_hash=hash_password("TestPass123!"),
        first_name="Hold",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_item(db, status=ItemStatus.on_hold, title="Hold Test Book"):
    """Create a catalog item with the given status."""
    item = CatalogItem(
        title=title,
        author="Test Author",
        status=status,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_hold(db, user_id, item_id, status=HoldStatus.ready):
    """Create a hold for a patron on an item."""
    hold = Hold(
        user_id=user_id,
        item_id=item_id,
        status=status,
        position=1,
    )
    db.add(hold)
    await db.commit()
    await db.refresh(hold)
    return hold


@pytest.fixture
async def patron_with_ready_hold(db):
    """A patron + a ready hold on an on_hold item (the standard happy path)."""
    patron = await _make_patron(db)
    item = await _make_item(db, status=ItemStatus.on_hold)
    hold = await _make_hold(db, patron.id, item.id, status=HoldStatus.ready)
    return patron, hold


@pytest.fixture
async def pending_hold(db):
    """A hold in pending status (not ready for checkout)."""
    patron = await _make_patron(db, email="holdtest.pending@example.com")
    item = await _make_item(db, status=ItemStatus.on_hold, title="Pending Hold Book")
    hold = await _make_hold(db, patron.id, item.id, status=HoldStatus.pending)
    return hold


@pytest.fixture
async def ready_hold_no_available_copy(db):
    """A ready hold where the item's only copy is ALREADY on loan to a
    different patron.

    Control flow inside the circulation core (checkout_service.create_checkout):
      1. item.status == ItemStatus.on_hold  -> enters the on_hold block
      2. Finds THIS patron's ready Hold     -> sets hold.status = HoldStatus.fulfilled (in-memory)
      3. Copy-count availability gate       -> all copies out
                                             -> raises ConflictError(ITEM_CHECKED_OUT)
      4. Exception propagates; endpoint never commits.

    This exercises the real fail-safe: the fulfilled mutation happens BEFORE the
    ConflictError, so the test must rollback to assert the hold stayed ready.
    """
    patron = await _make_patron(db, email="holdtest.nocopy@example.com")
    other_patron = await _make_patron(db, email="holdtest.otherpatron@example.com")
    # Item is on_hold (not checked_out) so the service enters the on_hold branch
    item = await _make_item(db, status=ItemStatus.on_hold, title="No Copy Book")
    # The sole physical copy: with it already on loan below, the copy-count
    # availability gate ("All copies are checked out") is what blocks checkout.
    only_copy = ItemCopy(catalog_item_id=item.id, barcode="NO-COPY-0001")
    db.add(only_copy)
    hold = await _make_hold(db, patron.id, item.id, status=HoldStatus.ready)
    # Pre-existing active checkout by a different patron takes the only copy
    other_checkout = Checkout(
        user_id=other_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now() + timedelta(days=14),
    )
    db.add(other_checkout)
    await db.commit()
    await db.refresh(other_checkout)
    return patron, hold


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_checkout_ready_hold_creates_loan_and_fulfills(
    staff_client, db, patron_with_ready_hold, monkeypatch
):
    """Happy path: POST checkout on a ready hold creates a loan and
    transitions the hold to fulfilled."""
    monkeypatch.setattr(
        "app.services.checkout_service.invalidate_catalog_cache", _noop
    )
    monkeypatch.setattr(
        "app.api.v1.circulation.hold_shelf.invalidate_catalog_cache", _noop
    )

    patron, hold = patron_with_ready_hold
    resp = await staff_client.post(f"/api/v1/circulation/holds/{hold.id}/checkout")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["hold_id"] == hold.id
    assert body["checkout"]["item_id"] == hold.item_id

    await db.refresh(hold)
    assert hold.status == HoldStatus.fulfilled

    result = await db.execute(
        select(Checkout).where(
            (Checkout.user_id == patron.id)
            & (Checkout.item_id == hold.item_id)
            & (Checkout.status == CheckoutStatus.active)
        )
    )
    loans = result.fetchall()
    assert len(loans) == 1


@pytest.mark.asyncio
async def test_checkout_non_ready_hold_rejected(staff_client, db, pending_hold):
    """A pending hold must be rejected with 400; hold stays pending."""
    resp = await staff_client.post(
        f"/api/v1/circulation/holds/{pending_hold.id}/checkout"
    )
    assert resp.status_code == 400

    await db.refresh(pending_hold)
    assert pending_hold.status == HoldStatus.pending

    result = await db.execute(
        select(Checkout).where(Checkout.user_id == pending_hold.user_id)
    )
    assert len(result.fetchall()) == 0


@pytest.mark.asyncio
async def test_checkout_hold_not_found(staff_client):
    """Non-existent hold_id must return 404."""
    resp = await staff_client.post("/api/v1/circulation/holds/99999999/checkout")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_checkout_no_available_copy_keeps_hold_ready(
    staff_client, db, ready_hold_no_available_copy
):
    """Genuine fail-safe: the service sets hold.status = HoldStatus.fulfilled in-memory
    (checkout_service._handle_on_hold_item), then raises ConflictError(ITEM_CHECKED_OUT)
    at the copy-count availability gate before any commit.

    The endpoint never commits, so the hold must revert to ready after rollback.
    This test verifies the no-commit fail-safe by explicitly rolling back (mirroring
    what production's get_db does on exception) before asserting hold state.
    """
    patron, hold = ready_hold_no_available_copy
    # Capture IDs before rollback — ORM instances become detached after rollback
    # and attribute access raises DetachedInstanceError on lazy-load attempts.
    patron_id = patron.id
    hold_item_id = hold.item_id
    resp = await staff_client.post(
        f"/api/v1/circulation/holds/{hold.id}/checkout"
    )
    assert resp.status_code >= 400  # expect 409 ConflictError

    # Production get_db rolls back the session on any exception (database.py ~lines 88-90),
    # discarding the autoflushed-but-uncommitted fulfilled mutation.
    # The test harness shares one session and does NOT auto-rollback, so we do it
    # explicitly here to assert the same committed/rolled-back state as production.
    await db.rollback()

    await db.refresh(hold)
    assert hold.status == HoldStatus.ready

    # No active Checkout must exist for this patron on this item
    result = await db.execute(
        select(Checkout).where(
            Checkout.user_id == patron_id,
            Checkout.item_id == hold_item_id,
            Checkout.status == CheckoutStatus.active,
        )
    )
    assert len(result.fetchall()) == 0


@pytest.mark.asyncio
async def test_checkout_requires_staff(db, patron_with_ready_hold):
    """Non-staff caller (patron role) must receive 401 or 403 on hold checkout."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    patron, hold = patron_with_ready_hold

    async def override_get_db():
        yield db

    async def override_get_current_user():
        return patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(f"/api/v1/circulation/holds/{hold.id}/checkout")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code in (401, 403)
