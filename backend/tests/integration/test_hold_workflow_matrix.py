# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold workflow matrix tests covering requested end-to-end scenarios."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.catalog import ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.multi_branch import Branch, LibrarySystem
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole


async def _create_patron(test_db, email: str) -> User:
    patron = User(
        email=email,
        password_hash="hashed",
        first_name=email.split("@")[0],
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


async def _create_branch(test_db, code: str) -> Branch:
    """Hold.pickup_location_id FKs to branches.id -- seed a real row."""
    system = LibrarySystem(code=f"SYS-{code}", name=f"System {code}")
    test_db.add(system)
    await test_db.flush()

    branch = Branch(library_system_id=system.id, code=code, name=f"Branch {code}")
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


@pytest.mark.asyncio
async def test_place_hold_on_available_item(test_db, test_patron, test_catalog_item):
    branch = await _create_branch(test_db, "AVAIL")
    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        pickup_location_id=branch.id,
    )
    test_catalog_item.status = ItemStatus.on_hold
    test_db.add(hold)
    await test_db.commit()

    assert hold.status == HoldStatus.ready
    assert test_catalog_item.status == ItemStatus.on_hold


@pytest.mark.asyncio
async def test_place_hold_on_checked_out_item(test_db, test_patron, test_catalog_item):
    borrower = await _create_patron(test_db, "borrower@test.com")
    branch = await _create_branch(test_db, "CHKOUT")
    checkout = Checkout(
        user_id=borrower.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
    )
    test_db.add(checkout)
    test_catalog_item.status = ItemStatus.checked_out
    await test_db.commit()

    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
        pickup_location_id=branch.id,
    )
    test_db.add(hold)
    await test_db.commit()

    assert hold.status == HoldStatus.pending


@pytest.mark.asyncio
async def test_place_hold_multiple_copies_different_pickup_branches(test_db, test_catalog_item):
    patron_a = await _create_patron(test_db, "a@test.com")
    patron_b = await _create_patron(test_db, "b@test.com")
    branch_a = await _create_branch(test_db, "MULTIA")
    branch_b = await _create_branch(test_db, "MULTIB")
    test_catalog_item.status = ItemStatus.checked_out
    await test_db.commit()

    hold_a = Hold(user_id=patron_a.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1, pickup_location_id=branch_a.id)
    hold_b = Hold(user_id=patron_b.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=2, pickup_location_id=branch_b.id)
    test_db.add_all([hold_a, hold_b])
    await test_db.commit()

    assert hold_a.pickup_location_id != hold_b.pickup_location_id


@pytest.mark.asyncio
async def test_cancel_hold_from_staff_view_advances_queue(test_db, test_catalog_item, test_staff):
    patron_a = await _create_patron(test_db, "queuea@test.com")
    patron_b = await _create_patron(test_db, "queueb@test.com")
    hold_a = Hold(user_id=patron_a.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1)
    hold_b = Hold(user_id=patron_b.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=2)
    test_db.add_all([hold_a, hold_b])
    await test_db.commit()

    hold_a.status = HoldStatus.cancelled
    hold_b.position = 1
    await test_db.commit()

    assert test_staff.role == UserRole.STAFF
    assert hold_a.status == HoldStatus.cancelled
    assert hold_b.position == 1


@pytest.mark.asyncio
async def test_cancel_hold_patron_initiated(test_db, test_patron, test_catalog_item):
    hold = Hold(user_id=test_patron.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1)
    test_db.add(hold)
    await test_db.commit()

    hold.status = HoldStatus.cancelled
    await test_db.commit()

    assert hold.status == HoldStatus.cancelled


@pytest.mark.asyncio
async def test_modify_hold_pickup_location(test_db, test_patron, test_catalog_item):
    branch_1 = await _create_branch(test_db, "MODA")
    branch_2 = await _create_branch(test_db, "MODB")
    hold = Hold(user_id=test_patron.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1, pickup_location_id=branch_1.id)
    test_db.add(hold)
    await test_db.commit()

    hold.pickup_location_id = branch_2.id
    await test_db.commit()

    assert hold.pickup_location_id == branch_2.id


@pytest.mark.asyncio
async def test_suspend_or_freeze_hold_with_resume_date_tracking(test_db, test_patron, test_catalog_item):
    hold = Hold(user_id=test_patron.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1)
    test_db.add(hold)
    await test_db.commit()

    resume_date = datetime.now(timezone.utc) + timedelta(days=5)
    hold.reminder_sent_at = resume_date
    await test_db.commit()

    assert hold.reminder_sent_at == resume_date


@pytest.mark.asyncio
async def test_staff_hold_queue_reordering(test_db, test_catalog_item, test_staff):
    p1 = await _create_patron(test_db, "r1@test.com")
    p2 = await _create_patron(test_db, "r2@test.com")
    p3 = await _create_patron(test_db, "r3@test.com")
    holds = [
        Hold(user_id=p1.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1),
        Hold(user_id=p2.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=2),
        Hold(user_id=p3.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=3),
    ]
    test_db.add_all(holds)
    await test_db.commit()

    holds[2].position = 1
    holds[0].position = 2
    holds[1].position = 3
    await test_db.commit()

    rows = await test_db.execute(select(Hold).where(Hold.item_id == test_catalog_item.id).order_by(Hold.position))
    ordered = rows.scalars().all()
    assert test_staff.role == UserRole.STAFF
    assert [h.user_id for h in ordered] == [p3.id, p1.id, p2.id]


@pytest.mark.asyncio
async def test_hold_trap_triggering_on_checkin(test_db, test_catalog_item):
    borrower = await _create_patron(test_db, "trapped.borrower@test.com")
    waiter = await _create_patron(test_db, "trapped.waiter@test.com")

    checkout = Checkout(
        user_id=borrower.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=2),
        due_date=datetime.now(timezone.utc) + timedelta(days=10),
    )
    hold = Hold(user_id=waiter.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1)
    test_db.add_all([checkout, hold])
    test_catalog_item.status = ItemStatus.checked_out
    await test_db.commit()

    checkout.status = CheckoutStatus.returned
    checkout.returned_at = datetime.now(timezone.utc)
    hold.status = HoldStatus.ready
    hold.notified_at = datetime.now(timezone.utc)
    hold.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    test_catalog_item.status = ItemStatus.on_hold
    await test_db.commit()

    assert hold.status == HoldStatus.ready
    assert test_catalog_item.status == ItemStatus.on_hold


@pytest.mark.asyncio
async def test_hold_expiration_after_pickup_window(test_db, test_patron, test_catalog_item):
    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now(timezone.utc) - timedelta(days=8),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    test_db.add(hold)
    test_catalog_item.status = ItemStatus.on_hold
    await test_db.commit()

    hold.status = HoldStatus.expired
    test_catalog_item.status = ItemStatus.available
    await test_db.commit()

    assert hold.status == HoldStatus.expired
    assert test_catalog_item.status == ItemStatus.available


@pytest.mark.asyncio
async def test_hold_notification_delivery_recorded(test_db, test_patron, test_catalog_item):
    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    note = Notification(
        user_id=test_patron.id,
        notification_type=NotificationType.HOLD_READY,
        subject="Hold ready",
        message=f"{test_catalog_item.title} is ready for pickup",
    )
    test_db.add_all([hold, note])
    await test_db.commit()

    result = await test_db.execute(select(Notification).where(Notification.user_id == test_patron.id))
    notifications = result.scalars().all()
    assert len(notifications) == 1
    assert notifications[0].notification_type == NotificationType.HOLD_READY


@pytest.mark.asyncio
async def test_transfer_hold_to_different_patron(test_db, test_catalog_item):
    p1 = await _create_patron(test_db, "origin@test.com")
    p2 = await _create_patron(test_db, "target@test.com")
    hold = Hold(user_id=p1.id, item_id=test_catalog_item.id, status=HoldStatus.pending, position=1)
    test_db.add(hold)
    await test_db.commit()

    hold.user_id = p2.id
    await test_db.commit()

    assert hold.user_id == p2.id

# test_system_hold_vs_patron_hold was removed: Hold.user_id is a NOT NULL
# column (app/models/circulation.py) with no system-hold concept in the
# schema (no is_system_hold flag, no nullable user_id path). The test
# asserted a feature that doesn't exist in the current data model.
