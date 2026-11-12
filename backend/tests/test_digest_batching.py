# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Digest Mode notification batching.

Covers the preference gate's digest-enqueue side effect, the digest job's
time-window matching and rendering, and the end-to-end aggregate/send/clear
behavior of send_notification_digests.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.notification import NotificationDigestQueue
from app.models.notification_preference import UserNotificationPreference
from app.services.notifications.preference_gate import should_send_email
from app.services.schedulers.digest_jobs import (
    _digest_due_now,
    _render_digest_email,
    send_notification_digests,
)


# --- Gate enqueue behavior ---


@pytest.mark.asyncio
async def test_digest_mode_enqueues_when_summary_given(test_db, test_patron):
    """A digest-mode patron's suppressed email is enqueued for batching."""
    test_db.add(
        UserNotificationPreference(user_id=test_patron.id, digest_enabled=True)
    )
    await test_db.commit()

    allowed = await should_send_email(
        test_patron.id,
        "due_date_reminder",
        test_db,
        summary="2 items due in 3 days",
        dedup_key="courtesy:2026-05-22",
    )
    assert allowed is False

    rows = (
        (
            await test_db.execute(
                select(NotificationDigestQueue).where(
                    NotificationDigestQueue.user_id == test_patron.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].notification_type == "due_date_reminder"
    assert rows[0].summary == "2 items due in 3 days"


@pytest.mark.asyncio
async def test_digest_mode_without_summary_suppresses_only(test_db, test_patron):
    """Callers that pass no summary keep plain suppress behavior (no row)."""
    test_db.add(
        UserNotificationPreference(user_id=test_patron.id, digest_enabled=True)
    )
    await test_db.commit()

    allowed = await should_send_email(
        test_patron.id, "due_date_reminder", test_db
    )
    assert allowed is False

    rows = (
        (
            await test_db.execute(
                select(NotificationDigestQueue).where(
                    NotificationDigestQueue.user_id == test_patron.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_digest_enqueue_is_idempotent_on_dedup_key(test_db, test_patron):
    """Re-enqueuing the same source event does not duplicate the digest row."""
    test_db.add(
        UserNotificationPreference(user_id=test_patron.id, digest_enabled=True)
    )
    await test_db.commit()

    for _ in range(2):
        await should_send_email(
            test_patron.id,
            "hold_cancelled",
            test_db,
            summary="Your hold expired",
            dedup_key="hold_expired:42",
        )

    rows = (
        (
            await test_db.execute(
                select(NotificationDigestQueue).where(
                    NotificationDigestQueue.user_id == test_patron.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_required_type_never_enqueued(test_db, test_patron):
    """REQUIRED types always send and are never queued, even in Digest Mode."""
    test_db.add(
        UserNotificationPreference(user_id=test_patron.id, digest_enabled=True)
    )
    await test_db.commit()

    allowed = await should_send_email(
        test_patron.id,
        "hold_ready",
        test_db,
        summary="should be ignored",
        dedup_key="hold:1",
    )
    assert allowed is True

    rows = (
        (
            await test_db.execute(
                select(NotificationDigestQueue).where(
                    NotificationDigestQueue.user_id == test_patron.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


# --- _digest_due_now time-window matching ---


def _pref(**kw) -> UserNotificationPreference:
    base = dict(
        digest_enabled=True,
        digest_frequency="daily",
        digest_preferred_time="09:00",
        digest_preferred_day=0,
    )
    base.update(kw)
    return UserNotificationPreference(**base)


def test_digest_due_daily_matches_hour():
    pref = _pref(digest_frequency="daily", digest_preferred_time="09:30")
    assert _digest_due_now(pref, datetime(2026, 5, 22, 9, 5, tzinfo=timezone.utc))
    assert not _digest_due_now(
        pref, datetime(2026, 5, 22, 10, 5, tzinfo=timezone.utc)
    )


def test_digest_due_weekly_requires_day_and_hour():
    # 2026-05-18 is a Monday (weekday 0).
    pref = _pref(
        digest_frequency="weekly",
        digest_preferred_time="08:00",
        digest_preferred_day=0,
    )
    monday = datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc)
    tuesday = datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc)
    assert _digest_due_now(pref, monday)
    assert not _digest_due_now(pref, tuesday)


def test_digest_not_due_when_disabled():
    pref = _pref(digest_enabled=False)
    assert not _digest_due_now(
        pref, datetime(2026, 5, 22, 9, 0, tzinfo=timezone.utc)
    )


# --- Rendering ---


def test_render_digest_email_lists_all_items(test_patron):
    items = [
        NotificationDigestQueue(
            user_id=test_patron.id,
            notification_type="due_date_reminder",
            summary="2 items due in 3 days",
            dedup_key="a",
        ),
        NotificationDigestQueue(
            user_id=test_patron.id,
            notification_type="hold_cancelled",
            summary="Your hold expired",
            dedup_key="b",
        ),
    ]
    html = _render_digest_email(test_patron, items)
    assert "2 items due in 3 days" in html
    assert "Your hold expired" in html
    assert test_patron.first_name in html


# --- End-to-end job ---


@pytest.mark.asyncio
async def test_send_notification_digests_aggregates_and_clears(test_db, test_patron):
    """The job batches a due patron's rows into one email and clears the queue."""
    now_hour = datetime.now(timezone.utc).hour
    test_db.add(
        UserNotificationPreference(
            user_id=test_patron.id,
            digest_enabled=True,
            digest_frequency="daily",
            digest_preferred_time=f"{now_hour:02d}:00",
        )
    )
    test_db.add_all(
        [
            NotificationDigestQueue(
                user_id=test_patron.id,
                notification_type="due_date_reminder",
                summary="2 items due in 3 days",
                dedup_key="x",
            ),
            NotificationDigestQueue(
                user_id=test_patron.id,
                notification_type="hold_cancelled",
                summary="Your hold expired",
                dedup_key="y",
            ),
        ]
    )
    await test_db.commit()

    @asynccontextmanager
    async def _fake_session():
        yield test_db

    sent_emails = []

    async def _fake_send_email(to_email, subject, html, **kw):
        sent_emails.append((to_email, subject, html))
        return True

    with patch(
        "app.services.schedulers.digest_jobs.AsyncSessionLocal", _fake_session
    ), patch(
        "app.services.schedulers.digest_jobs.send_email",
        new=AsyncMock(side_effect=_fake_send_email),
    ), patch(
        "app.services.schedulers.digest_jobs.JobExecutionContext"
    ) as mock_ctx:
        mock_ctx.return_value.__aenter__ = AsyncMock(
            return_value=AsyncMock(
                record_success=lambda: None,
                record_failure=lambda *a, **k: None,
                add_metric=lambda *a, **k: None,
            )
        )
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        await send_notification_digests()

    # One batched email, listing both items.
    assert len(sent_emails) == 1
    _, subject, html = sent_emails[0]
    assert "2 items due in 3 days" in html
    assert "Your hold expired" in html

    # Queue cleared.
    remaining = (
        (
            await test_db.execute(
                select(NotificationDigestQueue).where(
                    NotificationDigestQueue.user_id == test_patron.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert remaining == []
