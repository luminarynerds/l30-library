# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the in-app due-date reminder notification wiring.

Pins ``patron_notifications._record_due_date_reminder_in_app``: the courtesy
sweep emits an in-app PatronNotification row alongside the reminder email,
keyed for idempotency on patron id + due-date window.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus
from app.models.notification import PatronNotification, PatronNotificationCategory
from app.models.user import User


@pytest.mark.asyncio
async def test_due_date_reminder_creates_in_app_notification(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """The courtesy sweep stages one in-app DUE_DATE_REMINDER row per patron."""
    from app.services.patron_notifications import _record_due_date_reminder_in_app

    due = datetime.now(timezone.utc) + timedelta(days=3)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=due,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    checkout.item = test_catalog_item
    await _record_due_date_reminder_in_app(test_db, test_patron.id, [checkout])
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
    assert notif.category == PatronNotificationCategory.DUE_DATE_REMINDER
    assert notif.source_event_id == (
        f"due_date_reminder:{test_patron.id}:{due.date().isoformat()}"
    )
    assert notif.related_loan_id == str(checkout.id)
    assert notif.action_label == "View checkouts"


@pytest.mark.asyncio
async def test_due_date_reminder_in_app_idempotent_within_window(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """A second sweep in the same due-date window does not duplicate the row."""
    from app.services.patron_notifications import _record_due_date_reminder_in_app

    due = datetime.now(timezone.utc) + timedelta(days=3)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=due,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    checkout.item = test_catalog_item

    await _record_due_date_reminder_in_app(test_db, test_patron.id, [checkout])
    await test_db.commit()
    await _record_due_date_reminder_in_app(test_db, test_patron.id, [checkout])
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
