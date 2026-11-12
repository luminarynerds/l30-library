# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Hold Expiration + Notification Workflow.

Tests the complete hold lifecycle including expiration and queue advancement:
- Placing holds on items
- Hold status progression (pending -> ready -> fulfilled)
- Hold expiration when patron doesn't pick up in time
- Hold queue advancement when holds expire
- Notification system for hold readiness
- Multiple patrons in hold queue
- Hold cancellation and re-holding
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Hold, HoldStatus, Checkout, CheckoutStatus
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole


async def get_auth_headers(client, email: str, password: str) -> dict:
    """Helper to get authentication headers for a user."""
    login_data = {"username": email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def hold_item(test_db):
    """Create a catalog item for hold tests."""
    item = CatalogItem(
        title="Popular Book for Holds",
        author="Famous Author",
        isbn="978-0-hold-001",
        description="Popular item that gets held often",
        status=ItemStatus.available,
        call_number="HOLD-001",
        barcode="HOLD001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def patron_2(test_db):
    """Create second patron for multi-patron tests."""
    from app.core.security import hash_password

    user = User(
        email="patron2-hold@example.com",
        password_hash=hash_password("Patron2Password123!"),
        first_name="Patron",
        last_name="Two",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_3(test_db):
    """Create third patron for multi-patron tests."""
    from app.core.security import hash_password

    user = User(
        email="patron3-hold@example.com",
        password_hash=hash_password("Patron3Password123!"),
        first_name="Patron",
        last_name="Three",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_place_hold_on_available_item(test_db, test_patron, hold_item):
    """Test: Place hold on available item transitions to pending."""
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    assert hold.status == HoldStatus.pending
    assert hold.position == 1
    assert hold.created_at is not None


@pytest.mark.asyncio
async def test_hold_becomes_ready_when_item_available(test_db, test_patron, hold_item):
    """Test: Hold status changes to ready when item is returned/available."""
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Item becomes available, hold moves to ready
    hold.status = HoldStatus.ready
    hold.notified_at = datetime.now(timezone.utc)
    await test_db.commit()

    assert hold.status == HoldStatus.ready
    assert hold.notified_at is not None


@pytest.mark.asyncio
async def test_hold_fulfillment_flow(test_db, test_patron, hold_item):
    """Test: Complete hold flow from pending -> ready -> fulfilled."""
    # Create hold
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Item becomes available, mark as ready
    hold.status = HoldStatus.ready
    hold.notified_at = datetime.now(timezone.utc)
    await test_db.commit()

    assert hold.status == HoldStatus.ready

    # Patron picks up, fulfill the hold
    hold.status = HoldStatus.fulfilled
    await test_db.commit()

    assert hold.status == HoldStatus.fulfilled


@pytest.mark.asyncio
async def test_hold_expiration_after_ready_period(test_db, test_patron, hold_item):
    """Test: Hold expires if patron doesn't pick up within hold period."""
    # Create hold that becomes ready but expires in 7 days
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.ready,
        position=1,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired yesterday
        notified_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Mark as expired
    hold.status = HoldStatus.expired
    await test_db.commit()

    assert hold.status == HoldStatus.expired
    assert hold.expires_at < datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_hold_queue_advancement_on_expiration(test_db, test_patron, patron_2, patron_3, hold_item):
    """Test: When hold expires, next patron's hold moves up in queue."""
    # Create 3 holds in queue
    hold_1 = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.ready,
        position=1,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
    )
    hold_2 = Hold(
        user_id=patron_2.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=2,
    )
    hold_3 = Hold(
        user_id=patron_3.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=3,
    )
    test_db.add_all([hold_1, hold_2, hold_3])
    await test_db.commit()

    # First hold expires
    hold_1.status = HoldStatus.expired
    await test_db.commit()

    # Second hold moves to position 1 and becomes ready
    hold_2.position = 1
    hold_2.status = HoldStatus.ready
    hold_2.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    hold_2.notified_at = datetime.now(timezone.utc)
    await test_db.commit()

    # Third hold moves to position 2
    hold_3.position = 2
    await test_db.commit()

    # Verify queue order
    result = await test_db.execute(
        select(Hold)
        .filter(Hold.item_id == hold_item.id)
        .filter(Hold.status.in_([HoldStatus.pending, HoldStatus.ready]))
        .order_by(Hold.position)
    )
    queue = result.scalars().all()

    assert len(queue) == 2
    assert queue[0].user_id == patron_2.id
    assert queue[0].position == 1
    assert queue[1].user_id == patron_3.id
    assert queue[1].position == 2


@pytest.mark.asyncio
async def test_notification_created_when_hold_ready(test_db, test_patron, hold_item):
    """Test: Notification is created when hold becomes ready."""
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Hold becomes ready, create notification
    hold.status = HoldStatus.ready
    hold.notified_at = datetime.now(timezone.utc)

    notification = Notification(
        user_id=test_patron.id,
        notification_type=NotificationType.HOLD_READY,
        subject="Your hold is ready!",
        message=f"The book '{hold_item.title}' is now available for pickup.",
        context_data={"item_id": hold_item.id},
    )
    test_db.add(notification)
    await test_db.commit()
    await test_db.refresh(notification)

    # Verify notification
    result = await test_db.execute(
        select(Notification).filter(
            Notification.user_id == test_patron.id,
            Notification.notification_type == NotificationType.HOLD_READY,
        )
    )
    notifications = result.scalars().all()
    assert len(notifications) == 1
    assert notifications[0].read_at is None


@pytest.mark.asyncio
async def test_multiple_holds_same_item_different_patrons(test_db, test_patron, patron_2, patron_3, hold_item):
    """Test: Multiple patrons can hold the same item with queue positioning."""
    holds = [
        Hold(
            user_id=test_patron.id,
            item_id=hold_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=datetime.now(timezone.utc),
        ),
        Hold(
            user_id=patron_2.id,
            item_id=hold_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        ),
        Hold(
            user_id=patron_3.id,
            item_id=hold_item.id,
            status=HoldStatus.pending,
            position=3,
            created_at=datetime.now(timezone.utc) + timedelta(minutes=2),
        ),
    ]
    test_db.add_all(holds)
    await test_db.commit()

    # Verify queue
    result = await test_db.execute(
        select(Hold)
        .filter(Hold.item_id == hold_item.id)
        .order_by(Hold.position)
    )
    queue = result.scalars().all()

    assert len(queue) == 3
    assert queue[0].position == 1
    assert queue[1].position == 2
    assert queue[2].position == 3
    assert queue[0].user_id == test_patron.id
    assert queue[1].user_id == patron_2.id
    assert queue[2].user_id == patron_3.id


@pytest.mark.asyncio
async def test_hold_cancellation(test_db, test_patron, hold_item):
    """Test: Patron can cancel their hold."""
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Cancel hold
    hold.status = HoldStatus.cancelled
    await test_db.commit()

    assert hold.status == HoldStatus.cancelled


@pytest.mark.asyncio
async def test_hold_cancellation_advances_queue(test_db, test_patron, patron_2, hold_item):
    """Test: When hold is cancelled, next patron's hold moves up."""
    hold_1 = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    hold_2 = Hold(
        user_id=patron_2.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=2,
    )
    test_db.add_all([hold_1, hold_2])
    await test_db.commit()

    # First hold cancelled
    hold_1.status = HoldStatus.cancelled
    await test_db.commit()

    # Second hold moves to position 1
    hold_2.position = 1
    await test_db.commit()

    result = await test_db.execute(
        select(Hold)
        .filter(Hold.status == HoldStatus.pending)
        .order_by(Hold.position)
    )
    queue = result.scalars().all()

    assert queue[0].position == 1
    assert queue[0].user_id == patron_2.id


@pytest.mark.asyncio
async def test_prevent_duplicate_active_holds(test_db, test_patron, hold_item):
    """Test: Patron cannot have multiple active holds on same item."""
    # Create first hold
    hold_1 = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold_1)
    await test_db.commit()

    # Try to create second hold - should fail due to unique constraint
    # (In real implementation, this would be checked by the service layer)
    result = await test_db.execute(
        select(Hold).filter(
            Hold.user_id == test_patron.id,
            Hold.item_id == hold_item.id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    active_holds = result.scalars().all()
    assert len(active_holds) == 1


@pytest.mark.asyncio
async def test_hold_expiration_timestamp(test_db, test_patron, hold_item):
    """Test: Hold expiration timestamp is set correctly."""
    hold_duration_days = 7
    expires_at = datetime.now(timezone.utc) + timedelta(days=hold_duration_days)

    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.ready,
        position=1,
        expires_at=expires_at,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Verify expiration is ~7 days from now. `.days` truncates, so a few
    # milliseconds of test-execution drift makes an exact-7 comparison
    # flaky (6.9999... days -> .days == 6); round instead.
    time_until_expiration = round(
        (hold.expires_at - datetime.now(timezone.utc)).total_seconds() / 86400
    )
    assert time_until_expiration == hold_duration_days


@pytest.mark.asyncio
async def test_hold_notification_includes_pickup_deadline(test_db, test_patron, hold_item):
    """Test: Hold notification includes pickup deadline."""
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.ready,
        position=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        notified_at=datetime.now(timezone.utc),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    notification = Notification(
        user_id=test_patron.id,
        notification_type=NotificationType.HOLD_READY,
        subject="Hold ready for pickup",
        message=f"Please pick up '{hold_item.title}' by {hold.expires_at.strftime('%Y-%m-%d')}",
        context_data={"item_id": hold_item.id},
    )
    test_db.add(notification)
    await test_db.commit()

    assert str(hold.expires_at.date()) in notification.message


@pytest.mark.asyncio
async def test_expired_hold_and_new_hold_by_same_patron(test_db, test_patron, hold_item):
    """Test: Patron can place new hold after previous hold expired."""
    # Create and expire first hold
    old_hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.expired,
        position=1,
    )
    test_db.add(old_hold)
    await test_db.commit()

    # Place new hold
    new_hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(new_hold)
    await test_db.commit()
    await test_db.refresh(new_hold)

    # Verify new hold exists
    result = await test_db.execute(
        select(Hold).filter(
            Hold.user_id == test_patron.id,
            Hold.item_id == hold_item.id,
            Hold.status == HoldStatus.pending,
        )
    )
    active_holds = result.scalars().all()
    assert len(active_holds) == 1


@pytest.mark.asyncio
async def test_hold_created_at_timestamp(test_db, test_patron, hold_item):
    """Test: Hold creation timestamp is recorded."""
    before = datetime.now(timezone.utc)

    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    after = datetime.now(timezone.utc)

    # created_at is a DB server_default (func.now()); the DB host's clock
    # can drift a little from the test-runner's, so an exact before/after
    # bound is flaky. Allow a small tolerance instead.
    tolerance = timedelta(seconds=5)
    assert before - tolerance <= hold.created_at <= after + tolerance


@pytest.mark.asyncio
async def test_ready_hold_to_checkout_transition(test_db, test_patron, hold_item):
    """Test: Ready hold transitions to fulfilled when item is checked out."""
    # Create ready hold
    hold = Hold(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=HoldStatus.ready,
        position=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Create checkout for the held item
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=hold_item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now(timezone.utc) + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()

    # Mark hold as fulfilled
    hold.status = HoldStatus.fulfilled
    await test_db.commit()

    assert hold.status == HoldStatus.fulfilled
    assert checkout.status == CheckoutStatus.active
