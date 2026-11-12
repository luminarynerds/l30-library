# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the staff hold-override checkout path."""

import pytest

from app.core.security import hash_password
from app.core.datetime_utils import utc_now
from datetime import timedelta
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Hold, HoldStatus
from app.models.user import User, UserRole


@pytest.fixture
async def held_item(test_db):
    item = CatalogItem(
        title="Held Override Book",
        author="Override Author",
        isbn="978-0-333333-33-3",
        description="Item with a ready hold",
        status=ItemStatus.on_hold,
        call_number="HO-001",
        publication_year=2025,
        barcode="HO-BARCODE-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def hold_owner(test_db):
    user = User(
        email="holdowner@test.com",
        password_hash=hash_password("testpass123"),
        first_name="Holden",
        last_name="Owner",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_member(test_db):
    user = User(
        email="staffmember@test.com",
        password_hash=hash_password("testpass123"),
        first_name="Staff",
        last_name="Member",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def ready_hold(test_db, held_item, hold_owner):
    """A ready hold owned by hold_owner on held_item."""
    hold = Hold(
        user_id=hold_owner.id,
        item_id=held_item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=utc_now(),
        expires_at=utc_now() + timedelta(days=7),
        shelf_slot="A-01",
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.mark.asyncio
async def test_log_hold_overridden_writes_audit_row(test_db, held_item, ready_hold, hold_owner, staff_member):
    """log_hold_overridden persists an audit row attributed to the staff member."""
    from sqlalchemy import select
    from app.models.operations_audit_log import OperationsAuditLog, OperationType
    from app.services.operations_audit_service import log_hold_overridden

    ok = await log_hold_overridden(
        test_db,
        staff=staff_member,
        bumped_patron=hold_owner,
        item=held_item,
        hold=ready_hold,
        disposition="bump_to_front",
    )
    await test_db.commit()
    assert ok is True

    rows = (await test_db.execute(
        select(OperationsAuditLog).where(
            OperationsAuditLog.operation_type == OperationType.HOLD_OVERRIDDEN.value
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].staff_id == staff_member.id
    assert rows[0].patron_id == hold_owner.id
    assert rows[0].hold_id == ready_hold.id


@pytest.mark.asyncio
async def test_staff_checkout_on_held_item_raises_with_override_context(
    test_db, held_item, ready_hold, test_patron, staff_member
):
    """Staff checkout (no override flag) raises ITEM_ON_HOLD carrying a hold_override block."""
    from app.core.exceptions import ConflictError
    from app.services.unified_circulation_service import checkout_item

    with pytest.raises(ConflictError) as exc:
        await checkout_item(
            patron=test_patron,
            item_id=held_item.id,
            db=test_db,
            is_staff_operation=True,
        )
    block = exc.value.details[0]["hold_override"]
    assert block["hold_id"] == ready_hold.id
    assert block["queue_length"] == 1
    assert block["patron_on_way"] is False
    assert block["held_patron_name"].startswith("Holden")


@pytest.mark.asyncio
async def test_override_bump_to_front_checks_out_and_requeues_hold(
    test_db, held_item, ready_hold, test_patron, staff_member
):
    """override_hold + bump_to_front checks the item out and demotes the hold to pending front."""
    from app.models.circulation import CheckoutStatus, HoldStatus
    from app.models.catalog import ItemStatus
    from app.services.unified_circulation_service import checkout_item

    notifications: list = []
    response, item = await checkout_item(
        patron=test_patron,
        item_id=held_item.id,
        db=test_db,
        is_staff_operation=True,
        override_hold=True,
        hold_disposition="bump_to_front",
        staff_user=staff_member,
        deferred_notifications=notifications,
    )

    assert response.user_id == test_patron.id
    assert response.status == CheckoutStatus.active
    assert item.status == ItemStatus.checked_out

    await test_db.refresh(ready_hold)
    assert ready_hold.status == HoldStatus.pending
    assert ready_hold.position == 1
    assert ready_hold.shelf_slot is None
    assert ready_hold.expires_at is None
    assert len(notifications) == 1
    assert notifications[0].disposition == "bump_to_front"


@pytest.mark.asyncio
async def test_override_cancel_checks_out_and_cancels_hold(
    test_db, held_item, ready_hold, test_patron, staff_member
):
    """override_hold + cancel checks the item out and cancels the bumped hold."""
    from app.models.circulation import HoldStatus
    from app.services.unified_circulation_service import checkout_item

    notifications: list = []
    await checkout_item(
        patron=test_patron,
        item_id=held_item.id,
        db=test_db,
        is_staff_operation=True,
        override_hold=True,
        hold_disposition="cancel",
        staff_user=staff_member,
        deferred_notifications=notifications,
    )

    await test_db.refresh(ready_hold)
    assert ready_hold.status == HoldStatus.cancelled
    assert ready_hold.cancelled_by == "staff"
    assert notifications[0].disposition == "cancel"


@pytest.mark.asyncio
async def test_override_rejected_for_non_staff(test_db, held_item, ready_hold, test_patron):
    """A non-staff caller passing override_hold is rejected."""
    from app.core.exceptions import ForbiddenError
    from app.services.unified_circulation_service import checkout_item

    with pytest.raises(ForbiddenError):
        await checkout_item(
            patron=test_patron,
            item_id=held_item.id,
            db=test_db,
            is_staff_operation=False,
            override_hold=True,
            hold_disposition="cancel",
        )


@pytest.mark.asyncio
async def test_override_requires_disposition(test_db, held_item, ready_hold, test_patron, staff_member):
    """override_hold without a disposition is rejected."""
    from app.core.exceptions import BusinessLogicError
    from app.services.unified_circulation_service import checkout_item

    with pytest.raises(BusinessLogicError):
        await checkout_item(
            patron=test_patron,
            item_id=held_item.id,
            db=test_db,
            is_staff_operation=True,
            override_hold=True,
            hold_disposition=None,
            staff_user=staff_member,
        )


@pytest.mark.asyncio
async def test_checkout_for_hold_owner_fulfills_without_override(
    test_db, held_item, ready_hold, hold_owner
):
    """The hold owner's own ready hold is fulfilled on checkout -- the non-override
    path through the rewritten on_hold branch (regression guard)."""
    from app.models.circulation import CheckoutStatus, HoldStatus
    from app.services.unified_circulation_service import checkout_item

    response, item = await checkout_item(
        patron=hold_owner,
        item_id=held_item.id,
        db=test_db,
        is_staff_operation=True,
    )
    assert response.status == CheckoutStatus.active
    await test_db.refresh(ready_hold)
    assert ready_hold.status == HoldStatus.fulfilled


@pytest.fixture
async def queue_patron(test_db):
    user = User(
        email="queuepatron@test.com",
        password_hash=hash_password("testpass123"),
        first_name="Quincy",
        last_name="Queue",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def second_pending_hold(test_db, held_item, queue_patron):
    """A pending hold behind ready_hold at position 2."""
    hold = Hold(
        user_id=queue_patron.id,
        item_id=held_item.id,
        status=HoldStatus.pending,
        position=2,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.mark.asyncio
async def test_orphan_on_hold_status_self_heals_on_checkout(
    test_db, held_item, test_patron, staff_member
):
    """An item stuck on_hold with NO actual ready hold is stale data, not a
    reservation: checkout proceeds (no supervisor required) and the title
    status is rederived from real copy/loan/hold counts."""
    from app.services.unified_circulation_service import checkout_item

    checkout_response, item = await checkout_item(
        patron=test_patron,
        item_id=held_item.id,
        db=test_db,
        is_staff_operation=True,
        override_hold=True,
        hold_disposition="cancel",
        staff_user=staff_member,
        deferred_notifications=[],
    )
    assert checkout_response.item_id == held_item.id
    assert item.status != ItemStatus.on_hold, "stale on_hold flag rederived"


@pytest.mark.asyncio
async def test_override_cancel_renumbers_remaining_queue(
    test_db, held_item, ready_hold, second_pending_hold, test_patron, staff_member
):
    """After a cancel override, the remaining pending hold moves up to position 1."""
    from app.models.circulation import HoldStatus
    from app.services.unified_circulation_service import checkout_item

    await checkout_item(
        patron=test_patron,
        item_id=held_item.id,
        db=test_db,
        is_staff_operation=True,
        override_hold=True,
        hold_disposition="cancel",
        staff_user=staff_member,
        deferred_notifications=[],
    )

    await test_db.refresh(ready_hold)
    await test_db.refresh(second_pending_hold)
    assert ready_hold.status == HoldStatus.cancelled
    assert second_pending_hold.status == HoldStatus.pending
    assert second_pending_hold.position == 1


@pytest.mark.asyncio
async def test_quick_checkout_endpoint_override_bump(
    staff_client, held_item, ready_hold, test_patron, test_db
):
    """POST quick-checkout with override_hold succeeds (201) and bumps the held hold."""
    from app.models.circulation import HoldStatus

    resp = await staff_client.post(
        f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
        json={
            "barcode": held_item.barcode,
            "override_hold": True,
            "hold_disposition": "bump_to_front",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["checkout"]["user_id"] == test_patron.id

    await test_db.refresh(ready_hold)
    assert ready_hold.status == HoldStatus.pending


@pytest.mark.asyncio
async def test_quick_checkout_endpoint_held_item_returns_409_context(
    staff_client, held_item, ready_hold, test_patron
):
    """POST quick-checkout without override returns 409 carrying the hold_override block."""
    resp = await staff_client.post(
        f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
        json={"barcode": held_item.barcode},
    )
    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["details"][0]["hold_override"]["hold_id"] == ready_hold.id
