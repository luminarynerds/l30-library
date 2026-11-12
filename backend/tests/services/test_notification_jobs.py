# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Service-level tests for the send_event_reminders scheduler job.

Covers the four behaviors that matter for go-live:

1. Only rows in the 23h-25h start_time window with
   reminder_requested=True AND reminder_sent_at IS NULL are picked.
2. A successful send sets reminder_sent_at on the row.
3. A row that already has reminder_sent_at set is skipped (no double-send).
4. A failed send (template renders nothing / SMTP raises) does NOT set
   reminder_sent_at, so the next hourly run can retry.

These tests stub EmailSenderService.send_templated rather than exercising
the real SMTP path -- the goal is to verify the scheduler's selection,
dedup, and commit logic, not the template renderer.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.event import Event
from app.models.event_registration import (
    EventRegistration,
    EventRegistrationStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _make_event(db, *, start_offset_hours: float, is_published: bool = True):
    """Create a published Event whose start_time is now + offset hours."""
    event = Event(
        title=f"Test Event {start_offset_hours}h",
        start_time=datetime.now(timezone.utc) + timedelta(hours=start_offset_hours),
        is_published=is_published,
        is_virtual=False,
        location="Main Branch",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _make_registration(
    db,
    *,
    event: Event,
    reminder_requested: bool = True,
    reminder_sent_at: datetime | None = None,
    status: str = EventRegistrationStatus.CONFIRMED.value,
    email: str = "patron@example.com",
):
    reg = EventRegistration(
        event_id=event.id,
        patron_name="Test Patron",
        patron_email=email,
        status=status,
        reminder_requested=reminder_requested,
        reminder_sent_at=reminder_sent_at,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return reg


@pytest.fixture
def patch_session_local(test_db):
    """Make the scheduler use the test_db session instead of opening a new one."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        # Reuse the live test_db session; do NOT close it here -- conftest owns lifecycle.
        yield test_db

    with patch(
        "app.services.schedulers.notification_jobs.AsyncSessionLocal",
        _factory,
    ):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_event_reminders_only_picks_pending_in_window(
    test_db, patch_session_local
):
    """Job must skip rows outside the 23-25h window, opt-outs, and already-sent."""
    # In-window, pending -> should send
    e_in = await _make_event(test_db, start_offset_hours=24)
    in_window = await _make_registration(
        test_db, event=e_in, email="in_window@example.com"
    )

    # In-window but reminder_requested=False -> skip
    opted_out = await _make_registration(
        test_db,
        event=e_in,
        email="opted_out@example.com",
        reminder_requested=False,
    )

    # In-window but already sent -> skip
    already_sent = await _make_registration(
        test_db,
        event=e_in,
        email="already_sent@example.com",
        reminder_sent_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    # Too far in future (48h) -> skip
    e_far = await _make_event(test_db, start_offset_hours=48)
    too_far = await _make_registration(
        test_db, event=e_far, email="too_far@example.com"
    )

    # Too close (2h) -> skip
    e_close = await _make_event(test_db, start_offset_hours=2)
    too_close = await _make_registration(
        test_db, event=e_close, email="too_close@example.com"
    )

    # Unpublished event in window -> skip
    e_unpub = await _make_event(test_db, start_offset_hours=24, is_published=False)
    unpublished = await _make_registration(
        test_db, event=e_unpub, email="unpublished@example.com"
    )

    # Cancelled status in window -> skip
    cancelled = await _make_registration(
        test_db,
        event=e_in,
        email="cancelled@example.com",
        status=EventRegistrationStatus.CANCELLED.value,
    )

    send_mock = AsyncMock(return_value=True)
    with patch(
        "app.services.notifications.email_sender.EmailSenderService.send_templated",
        send_mock,
    ):
        from app.services.schedulers.notification_jobs import send_event_reminders

        await send_event_reminders()

    # Only the in-window pending registration should have been sent to.
    recipients = [
        call.kwargs.get("recipient_email") or call.args[1]
        for call in send_mock.call_args_list
    ]
    assert recipients == ["in_window@example.com"], recipients


@pytest.mark.asyncio
async def test_send_event_reminders_sets_sent_at_on_success(
    test_db, patch_session_local
):
    """A successful send must populate reminder_sent_at."""
    event = await _make_event(test_db, start_offset_hours=24)
    reg = await _make_registration(test_db, event=event)

    assert reg.reminder_sent_at is None

    with patch(
        "app.services.notifications.email_sender.EmailSenderService.send_templated",
        new=AsyncMock(return_value=True),
    ):
        from app.services.schedulers.notification_jobs import send_event_reminders

        await send_event_reminders()

    await test_db.refresh(reg)
    assert reg.reminder_sent_at is not None
    # Should be very recent (within last 60s). Normalize tz because SQLite
    # roundtrips DateTime(timezone=True) as naive.
    sent = reg.reminder_sent_at
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - sent
    assert delta < timedelta(seconds=60), delta


@pytest.mark.asyncio
async def test_send_event_reminders_skips_already_sent(
    test_db, patch_session_local
):
    """Rows with reminder_sent_at set must be skipped (no second email)."""
    event = await _make_event(test_db, start_offset_hours=24)
    sent_at = datetime.now(timezone.utc) - timedelta(hours=2)
    reg = await _make_registration(
        test_db, event=event, reminder_sent_at=sent_at
    )

    send_mock = AsyncMock(return_value=True)
    with patch(
        "app.services.notifications.email_sender.EmailSenderService.send_templated",
        send_mock,
    ):
        from app.services.schedulers.notification_jobs import send_event_reminders

        await send_event_reminders()

    assert send_mock.await_count == 0
    await test_db.refresh(reg)
    # reminder_sent_at must remain set (not overwritten / cleared).
    # Normalize tz because SQLite roundtrips DateTime(timezone=True) as naive.
    persisted = reg.reminder_sent_at
    if persisted is not None and persisted.tzinfo is None:
        persisted = persisted.replace(tzinfo=timezone.utc)
    assert persisted is not None
    assert abs((persisted - sent_at).total_seconds()) < 1


@pytest.mark.asyncio
async def test_send_event_reminders_does_not_set_sent_at_on_email_failure(
    test_db, patch_session_local
):
    """If send_templated returns False, reminder_sent_at must stay NULL."""
    event = await _make_event(test_db, start_offset_hours=24)
    reg = await _make_registration(test_db, event=event)

    with patch(
        "app.services.notifications.email_sender.EmailSenderService.send_templated",
        new=AsyncMock(return_value=False),
    ):
        from app.services.schedulers.notification_jobs import send_event_reminders

        await send_event_reminders()

    await test_db.refresh(reg)
    assert reg.reminder_sent_at is None
