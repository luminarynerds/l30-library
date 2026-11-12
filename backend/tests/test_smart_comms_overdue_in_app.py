# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the smart-comms overdue-escalation in-app notification wiring.

Pins ``schedulers.notification_jobs._send_due_date_communications``: when
it emails an ``overdue_day_{1,7,14,30}`` escalation, it ALSO stages an
in-app ``PatronNotification`` row using the same
``overdue_notice:{user_id}:{date}`` key namespace as the daily
``_sweep_overdue_notices`` emitter, so the two paths together produce
at most one in-app row per patron per UTC day.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus
from app.models.notification import PatronNotification, PatronNotificationCategory
from app.models.user import User


async def _make_overdue_checkout(
    db: AsyncSession,
    patron: User,
    item: CatalogItem,
    *,
    days_overdue: int,
    now: datetime,
) -> Checkout:
    checkout = Checkout(
        user_id=patron.id,
        item_id=item.id,
        status=CheckoutStatus.overdue,
        checked_out_at=now - timedelta(days=days_overdue + 14),
        due_date=now - timedelta(days=days_overdue),
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)
    checkout.item = item
    return checkout


@pytest.mark.asyncio
async def test_smart_comms_overdue_stages_in_app_when_sweep_has_not(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
    monkeypatch,
):
    """When _send_due_date_communications hits an overdue tier and the daily
    sweep has not run yet, it stages exactly one in-app OVERDUE_NOTICE row
    with the shared overdue_notice:{user_id}:{date} key."""
    from app.services.schedulers import notification_jobs

    async def _fake_send_email(*args, **kwargs):
        return True

    monkeypatch.setattr(notification_jobs, "send_email", _fake_send_email)

    now = datetime.now(timezone.utc)
    await _make_overdue_checkout(
        test_db, test_patron, test_catalog_item, days_overdue=1, now=now
    )

    sent = await notification_jobs._send_due_date_communications(test_db, now)
    assert sent == 1

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    notif = rows[0]
    assert notif.category == PatronNotificationCategory.OVERDUE_NOTICE
    assert notif.source_event_id == (
        f"overdue_notice:{test_patron.id}:{now.date().isoformat()}"
    )
    assert notif.action_label == "View checkouts"


@pytest.mark.asyncio
async def test_smart_comms_and_sweep_share_key_one_row_per_day(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
    monkeypatch,
):
    """If the daily sweep emitter has already staged today's overdue row,
    the smart-comms emitter sees the same source_event_id and does not
    create a duplicate."""
    from app.services.patron_notifications import _record_overdue_notice_in_app
    from app.services.schedulers import notification_jobs

    async def _fake_send_email(*args, **kwargs):
        return True

    monkeypatch.setattr(notification_jobs, "send_email", _fake_send_email)

    now = datetime.now(timezone.utc)
    checkout = await _make_overdue_checkout(
        test_db, test_patron, test_catalog_item, days_overdue=7, now=now
    )

    # Simulate the daily sweep emitter firing first.
    await _record_overdue_notice_in_app(
        test_db, test_patron.id, [checkout], Decimal("0.25"), now
    )
    await test_db.commit()

    # Smart-comms then fires the day-7 tier later in the same UTC day.
    sent = await notification_jobs._send_due_date_communications(test_db, now)
    assert sent == 1

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].source_event_id == (
        f"overdue_notice:{test_patron.id}:{now.date().isoformat()}"
    )


@pytest.mark.asyncio
async def test_smart_comms_repeated_tiers_same_day_no_duplicate(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
    monkeypatch,
):
    """Smart-comms escalation can fire multiple times per day (e.g.,
    re-run after a crash). The shared idempotency key keeps it at one
    in-app row even without help from the daily sweep."""
    from app.services.schedulers import notification_jobs

    async def _fake_send_email(*args, **kwargs):
        return True

    monkeypatch.setattr(notification_jobs, "send_email", _fake_send_email)

    now = datetime.now(timezone.utc)
    await _make_overdue_checkout(
        test_db, test_patron, test_catalog_item, days_overdue=14, now=now
    )

    await notification_jobs._send_due_date_communications(test_db, now)
    await notification_jobs._send_due_date_communications(test_db, now)

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
