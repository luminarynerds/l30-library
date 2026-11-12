# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for hold-promotion notification wiring (silent-promotion regression).

Regression coverage for the issue where:
- ``hold_service.process_expired_holds`` flipped the next pending hold to
  ``ready`` but never queued a ``PendingHoldNotification``, so the cron
  promotion path silently transitioned holds and patrons only learned the
  hold was ready after it had already expired.
- ``hold_service.check_and_expire_hold`` and ``hold_service.promote_next_hold``
  shared the same silent-promotion shape.

These tests pin the new "_collecting_notifications" variants so future edits
cannot quietly delete the notification accumulator.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.circulation import Hold, HoldStatus
from app.models.user import User, UserRole


@pytest.fixture
async def waiting_patron(test_db: AsyncSession) -> User:
    """Patron at position 2 in the hold queue (no email collisions)."""
    patron = User(
        email="waiting-patron-hold-promo@example.com",
        password_hash="hashed_password",
        first_name="Waiting",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.mark.asyncio
async def test_process_expired_holds_collecting_notifications_returns_pending(
    test_db: AsyncSession,
    test_patron: User,
    waiting_patron: User,
    test_catalog_item: CatalogItem,
):
    """Cron path: expired ready hold promotes next pending and surfaces a notification."""
    from app.services.hold_service import (
        process_expired_holds_collecting_notifications,
    )

    now = datetime.now(timezone.utc)

    # patron 1: ready and already past expiry
    ready_hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        created_at=now - timedelta(days=8),
        notified_at=now - timedelta(days=8),
        expires_at=now - timedelta(days=1),
    )
    # patron 2: pending behind them
    pending_hold = Hold(
        user_id=waiting_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=2,
        created_at=now - timedelta(days=7),
    )
    test_db.add_all([ready_hold, pending_hold])
    await test_db.commit()
    await test_db.refresh(pending_hold)
    pending_id = pending_hold.id

    processed_count, notifications = await process_expired_holds_collecting_notifications(
        test_db
    )
    await test_db.commit()

    # Original hold expired
    assert processed_count == 1

    # Next-in-line was promoted to ready
    promoted = (
        await test_db.execute(select(Hold).where(Hold.id == pending_id))
    ).scalar_one()
    assert promoted.status == HoldStatus.ready

    # Notification surfaced for the newly-readied patron -- this is the regression test:
    # the legacy ``process_expired_holds`` returned only an int and dropped this.
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif.to_email == waiting_patron.email
    assert notif.first_name == waiting_patron.first_name
    assert notif.book_title == test_catalog_item.title


@pytest.mark.asyncio
async def test_process_expired_holds_collecting_notifications_no_pending_returns_empty(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """No next hold to promote -> no notifications emitted (and no spurious sends)."""
    from app.services.hold_service import (
        process_expired_holds_collecting_notifications,
    )

    now = datetime.now(timezone.utc)
    expired_hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        created_at=now - timedelta(days=8),
        notified_at=now - timedelta(days=8),
        expires_at=now - timedelta(days=1),
    )
    test_db.add(expired_hold)
    await test_db.commit()

    processed_count, notifications = await process_expired_holds_collecting_notifications(
        test_db
    )
    await test_db.commit()

    assert processed_count == 1
    assert notifications == []


@pytest.mark.asyncio
async def test_promote_next_hold_collecting_notification_returns_pending(
    test_db: AsyncSession,
    waiting_patron: User,
    test_catalog_item: CatalogItem,
):
    """Cancellation path: promoting next pending hold surfaces a PendingHoldNotification."""
    from app.services.hold_service import promote_next_hold_collecting_notification

    now = datetime.now(timezone.utc)
    pending_hold = Hold(
        user_id=waiting_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=now,
    )
    test_db.add(pending_hold)
    await test_db.commit()
    await test_db.refresh(pending_hold)
    pending_id = pending_hold.id

    promoted, notification = await promote_next_hold_collecting_notification(
        test_catalog_item.id, test_db
    )
    await test_db.commit()

    assert promoted is True
    promoted_hold = (
        await test_db.execute(select(Hold).where(Hold.id == pending_id))
    ).scalar_one()
    assert promoted_hold.status == HoldStatus.ready

    assert notification is not None
    assert notification.to_email == waiting_patron.email
    assert notification.book_title == test_catalog_item.title


@pytest.mark.asyncio
async def test_check_and_expire_hold_collecting_notifications_returns_pending(
    test_db: AsyncSession,
    test_patron: User,
    waiting_patron: User,
    test_catalog_item: CatalogItem,
):
    """Inline /holds listing path: single-hold expire surfaces a notification for next."""
    from app.services.hold_service import (
        check_and_expire_hold_collecting_notifications,
    )

    now = datetime.now(timezone.utc)
    ready_hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        created_at=now - timedelta(days=8),
        notified_at=now - timedelta(days=8),
        expires_at=now - timedelta(days=1),
    )
    pending_hold = Hold(
        user_id=waiting_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=2,
        created_at=now - timedelta(days=7),
    )
    test_db.add_all([ready_hold, pending_hold])
    await test_db.commit()
    await test_db.refresh(ready_hold)

    expired, notification = await check_and_expire_hold_collecting_notifications(
        ready_hold, test_db
    )
    await test_db.commit()

    assert expired is True
    assert notification is not None
    assert notification.to_email == waiting_patron.email
    assert notification.book_title == test_catalog_item.title


@pytest.mark.asyncio
async def test_legacy_process_expired_holds_still_returns_int(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """Back-compat: the legacy int-returning wrapper is preserved.

    Any caller still on the legacy signature MUST keep working without
    blowing up tests / scheduler code.
    """
    from app.services.hold_service import process_expired_holds

    now = datetime.now(timezone.utc)
    expired_hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
        created_at=now - timedelta(days=8),
        notified_at=now - timedelta(days=8),
        expires_at=now - timedelta(days=1),
    )
    test_db.add(expired_hold)
    await test_db.commit()

    count = await process_expired_holds(test_db)
    await test_db.commit()

    assert count == 1


@pytest.mark.asyncio
async def test_collecting_function_skips_patron_without_email(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """Patron with no email -> no PendingHoldNotification emitted (avoid TypeError on send)."""
    from app.services.hold_service import promote_next_hold_collecting_notification

    no_email_patron = User(
        email="placeholder-no-email@example.com",  # must be unique
        password_hash="hashed_password",
        first_name="NoEmail",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(no_email_patron)
    await test_db.commit()
    await test_db.refresh(no_email_patron)

    # users.email is NOT NULL; empty string is the no-email state
    # (_build_pending_notification checks `if not user.email`)
    no_email_patron.email = ""
    await test_db.commit()

    pending_hold = Hold(
        user_id=no_email_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(pending_hold)
    await test_db.commit()

    promoted, notification = await promote_next_hold_collecting_notification(
        test_catalog_item.id, test_db
    )
    await test_db.commit()

    assert promoted is True
    assert notification is None


@pytest.mark.asyncio
async def test_hold_promotion_creates_in_app_notification(
    test_db: AsyncSession,
    waiting_patron: User,
    test_catalog_item: CatalogItem,
):
    """Promoting a hold to ready stages an in-app PatronNotification row."""
    from app.models.notification import (
        PatronNotification,
        PatronNotificationCategory,
    )
    from app.services.hold_service import promote_next_hold_collecting_notification

    pending_hold = Hold(
        user_id=waiting_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(pending_hold)
    await test_db.commit()
    await test_db.refresh(pending_hold)
    hold_id = pending_hold.id

    promoted, _ = await promote_next_hold_collecting_notification(
        test_catalog_item.id, test_db
    )
    await test_db.commit()
    assert promoted is True

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == waiting_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    notif = rows[0]
    assert notif.category == PatronNotificationCategory.HOLD_AVAILABLE
    assert notif.source_event_id == f"hold_ready:{hold_id}"
    assert notif.related_hold_id == str(hold_id)
    assert notif.related_item_title == test_catalog_item.title
    assert notif.action_url
    assert notif.action_label == "View hold"


@pytest.mark.asyncio
async def test_hold_promotion_in_app_notification_idempotent(
    test_db: AsyncSession,
    waiting_patron: User,
    test_catalog_item: CatalogItem,
):
    """Re-recording the same hold-ready event does not duplicate the in-app row."""
    from app.models.notification import PatronNotification
    from app.models.user import User as UserModel
    from app.models.catalog import CatalogItem as CatalogItemModel
    from app.services.hold_service import record_hold_ready_in_app

    hold = Hold(
        user_id=waiting_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    user = await test_db.get(UserModel, waiting_patron.id)
    item = await test_db.get(CatalogItemModel, test_catalog_item.id)

    await record_hold_ready_in_app(hold, user, item, test_db)
    await test_db.commit()
    await record_hold_ready_in_app(hold, user, item, test_db)
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == waiting_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_hold_promotion_in_app_notification_no_email_patron(
    test_db: AsyncSession,
    test_catalog_item: CatalogItem,
):
    """A patron with no email still gets the in-app feed row on hold promotion."""
    from app.models.notification import PatronNotification
    from app.models.user import User as UserModel
    from app.models.catalog import CatalogItem as CatalogItemModel
    from app.services.hold_service import record_hold_ready_in_app

    patron = UserModel(
        email="in-app-no-email-probe@example.com",
        password_hash="hashed_password",
        first_name="NoEmail",
        last_name="Feed",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)

    hold = Hold(
        user_id=patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    user = await test_db.get(UserModel, patron.id)
    item = await test_db.get(CatalogItemModel, test_catalog_item.id)
    user.email = ""

    await record_hold_ready_in_app(hold, user, item, test_db)
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_return_checkout_promotion_creates_in_app_notification(
    test_db: AsyncSession,
    test_patron: User,
    waiting_patron: User,
    test_catalog_item: CatalogItem,
):
    """return_checkout promoting the next hold stages an in-app row for the waiter.

    return_checkout inlines its own promotion build (it does not call
    _build_pending_notification), so it must wire the in-app row separately.
    """
    from datetime import datetime, timedelta, timezone

    from app.models.circulation import Checkout, CheckoutStatus
    from app.models.notification import (
        PatronNotification,
        PatronNotificationCategory,
    )
    from app.services.checkout_service import return_checkout

    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=5),
        due_date=now + timedelta(days=16),
    )
    test_db.add(checkout)

    waiting_hold = Hold(
        user_id=waiting_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(waiting_hold)
    await test_db.commit()
    await test_db.refresh(checkout)
    await test_db.refresh(waiting_hold)
    hold_id = waiting_hold.id

    await return_checkout(checkout, test_db, user=test_patron)
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == waiting_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].category == PatronNotificationCategory.HOLD_AVAILABLE
    assert rows[0].source_event_id == f"hold_ready:{hold_id}"
