# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression: hold-expiring scheduler queries must not lock the nullable side
of their joinedload outer joins.

``_send_hold_expiring_tomorrow_communications`` (and its twin
``send_hold_expiration_reminders``) eager-load ``Hold.user`` and ``Hold.item``
as LEFT OUTER JOINs and lock rows with ``FOR UPDATE SKIP LOCKED``. Without
scoping the lock to the holds table (``of=Hold``), Postgres rejects the
statement with::

    FOR UPDATE cannot be applied to the nullable side of an outer join

which kills the smart-automated-communications job and silently stops
hold-expiring reminders. This pins the ``of=Hold`` scoping.
"""

from datetime import datetime, time, timedelta, timezone

import pytest

from app.models.catalog import CatalogItem
from app.models.circulation import Hold, HoldStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_hold_expiring_tomorrow_locks_only_holds_not_outer_join(
    test_db, test_patron: User, test_catalog_item: CatalogItem, monkeypatch
):
    from app.services.schedulers import notification_jobs

    sent_to: list[str] = []

    async def _fake_send_email(to, subject, html):
        sent_to.append(to)
        return True

    monkeypatch.setattr(notification_jobs, "send_email", _fake_send_email)

    now = datetime.now(timezone.utc)
    expires_at = datetime.combine(
        now.date() + timedelta(days=1), time(12, 0), tzinfo=timezone.utc
    )
    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.ready,
        expires_at=expires_at,
        reminder_sent_at=None,
    )
    test_db.add(hold)
    await test_db.commit()

    # Before of=Hold this raised asyncpg FeatureNotSupportedError:
    # "FOR UPDATE cannot be applied to the nullable side of an outer join".
    sent = await notification_jobs._send_hold_expiring_tomorrow_communications(
        test_db, now
    )

    assert sent == 1
    assert sent_to == [test_patron.email]
    await test_db.refresh(hold)
    assert hold.reminder_sent_at is not None
