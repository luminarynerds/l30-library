# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the in-app overdue notice notification wiring.

Pins ``patron_notifications._record_overdue_notice_in_app``: the overdue
sweep emits an in-app PatronNotification row alongside the overdue email,
keyed for idempotency on patron id + the day the notice fires.
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


@pytest.mark.asyncio
async def test_overdue_notice_creates_in_app_notification(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """The overdue sweep stages one in-app OVERDUE_NOTICE row per patron."""
    from app.services.patron_notifications import _record_overdue_notice_in_app

    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.overdue,
        checked_out_at=now - timedelta(days=30),
        due_date=now - timedelta(days=10),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    checkout.item = test_catalog_item
    await _record_overdue_notice_in_app(
        test_db, test_patron.id, [checkout], Decimal("0.25"), now
    )
    await test_db.commit()

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
    assert notif.related_loan_id == str(checkout.id)
    assert notif.action_label == "View checkouts"


@pytest.mark.asyncio
async def test_overdue_notice_in_app_idempotent_within_day(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """A second sweep on the same day does not duplicate the row."""
    from app.services.patron_notifications import _record_overdue_notice_in_app

    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.overdue,
        checked_out_at=now - timedelta(days=30),
        due_date=now - timedelta(days=10),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    checkout.item = test_catalog_item

    await _record_overdue_notice_in_app(
        test_db, test_patron.id, [checkout], Decimal("0.25"), now
    )
    await test_db.commit()
    await _record_overdue_notice_in_app(
        test_db, test_patron.id, [checkout], Decimal("0.25"), now
    )
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
