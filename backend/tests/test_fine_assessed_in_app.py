# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the in-app fine-assessed notification wiring.

Pins ``fine_service.record_fine_assessed_in_app``: a newly created fine
stages an in-app PatronNotification row pointing the patron at the fine
payment page, idempotent on the fine id so the per-day overdue sweep
re-running (which updates rather than re-creates the fine) cannot duplicate
the row.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.notification import PatronNotification, PatronNotificationCategory
from app.models.user import User


async def _make_checkout(
    db: AsyncSession, patron: User, item: CatalogItem
) -> Checkout:
    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=patron.id,
        item_id=item.id,
        status=CheckoutStatus.overdue,
        checked_out_at=now - timedelta(days=30),
        due_date=now - timedelta(days=10),
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)
    return checkout


async def _make_fine(db: AsyncSession, patron: User, checkout: Checkout) -> Fine:
    fine = Fine(
        user_id=patron.id,
        checkout_id=checkout.id,
        amount=Decimal("2.50"),
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        description="Overdue by 10 day(s)",
    )
    db.add(fine)
    await db.flush()
    return fine


@pytest.mark.asyncio
async def test_fine_assessed_creates_in_app_notification(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """Assessing a new fine stages an in-app FINE_ASSESSED row."""
    from app.services.fine_service import record_fine_assessed_in_app

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item)
    fine = await _make_fine(test_db, test_patron, checkout)

    await record_fine_assessed_in_app(fine, checkout, test_db)
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
    assert notif.category == PatronNotificationCategory.FINE_ASSESSED
    assert notif.source_event_id == f"fine_assessed:{fine.id}"
    assert notif.related_fine_id == str(fine.id)
    assert notif.related_loan_id == str(checkout.id)
    assert notif.action_label == "Pay fine"
    assert notif.action_url


@pytest.mark.asyncio
async def test_fine_assessed_in_app_idempotent(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """Re-recording the same fine does not duplicate the in-app row.

    The daily overdue sweep updates an existing fine rather than creating a
    new one; keying idempotency on the fine id keeps the patron from getting
    a fresh notification every day the fine grows.
    """
    from app.services.fine_service import record_fine_assessed_in_app

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item)
    fine = await _make_fine(test_db, test_patron, checkout)

    await record_fine_assessed_in_app(fine, checkout, test_db)
    await test_db.commit()
    await record_fine_assessed_in_app(fine, checkout, test_db)
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_fine_assessed_in_app_skips_unflushed_fine(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """A fine with no id (not yet flushed) stages no row rather than crashing."""
    from app.services.fine_service import record_fine_assessed_in_app

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item)
    fine = Fine(
        user_id=test_patron.id,
        checkout_id=checkout.id,
        amount=Decimal("2.50"),
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        description="Overdue by 10 day(s)",
    )

    await record_fine_assessed_in_app(fine, checkout, test_db)
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id
            )
        )
    ).scalars().all()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_apply_fine_policy_wires_in_app_notification(
    test_db: AsyncSession,
    test_patron: User,
    test_catalog_item: CatalogItem,
):
    """apply_fine_policy emits an in-app row on new-fine creation, not on update.

    Pins the integration wiring: the daily overdue job goes through
    apply_fine_policy. A first call creates the fine and the notification; a
    second call updates the same fine (more days overdue) and must not produce
    a duplicate notification row.
    """
    from app.models.fine import FinePolicyType
    from app.models.permission import RoleSettings
    from app.models.user import UserRole
    from app.services.fine_policy_service import (
        apply_fine_policy,
        create_or_update_fine_policy,
    )

    test_db.add(
        RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            checkout_duration_days=21,
            fine_exempt=False,
            use_reading_minutes=False,
        )
    )
    await create_or_update_fine_policy(
        test_db,
        name="Standard Daily Rate",
        policy_type=FinePolicyType.daily_rate,
        fine_per_day=Decimal("0.25"),
        applies_to_item_types="all",
        applies_to_user_roles="all",
        grace_period_hours=0,
    )
    await test_db.commit()

    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=30),
        due_date=now - timedelta(days=3),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    fine1, _ = await apply_fine_policy(checkout, test_patron, test_catalog_item, test_db)
    await test_db.commit()
    assert fine1 is not None

    # A later run sees the item more overdue and updates the same fine.
    checkout.due_date = now - timedelta(days=5)
    fine2, _ = await apply_fine_policy(checkout, test_patron, test_catalog_item, test_db)
    await test_db.commit()
    assert fine2.id == fine1.id

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == test_patron.id,
                PatronNotification.category == PatronNotificationCategory.FINE_ASSESSED,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].source_event_id == f"fine_assessed:{fine1.id}"
