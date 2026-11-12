# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the notification preference gate (should_send_email).

Covers per-channel toggle enforcement, Quiet Hours (including midnight wrap),
Digest Mode suppression, and the REQUIRED-type always-send guarantee.
"""

from datetime import datetime, timezone

import pytest

from app.models.notification_preference import UserNotificationPreference
from app.services.notifications.preference_gate import (
    REQUIRED_NOTIFICATION_TYPES,
    _in_quiet_hours,
    should_send_email,
    should_send_email_by_email,
)


# --- Pure quiet-hours window logic ---


def _pref(**kwargs) -> UserNotificationPreference:
    base = dict(
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        quiet_hours_days=[0, 1, 2, 3, 4, 5, 6],
    )
    base.update(kwargs)
    return UserNotificationPreference(**base)


def test_quiet_hours_disabled_is_never_quiet():
    pref = _pref(quiet_hours_enabled=False)
    # 02:00 Monday would otherwise be inside a 22:00->08:00 window
    now = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
    assert _in_quiet_hours(pref, now) is False


def test_quiet_hours_wrapping_window_inside():
    pref = _pref(quiet_hours_start="22:00", quiet_hours_end="08:00")
    # 02:00 Monday is inside the overnight window
    now = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
    assert _in_quiet_hours(pref, now) is True


def test_quiet_hours_wrapping_window_outside():
    pref = _pref(quiet_hours_start="22:00", quiet_hours_end="08:00")
    # 12:00 Monday is outside the overnight window
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    assert _in_quiet_hours(pref, now) is False


def test_quiet_hours_same_day_window():
    pref = _pref(quiet_hours_start="09:00", quiet_hours_end="17:00")
    inside = datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc)
    outside = datetime(2026, 5, 18, 20, 0, tzinfo=timezone.utc)
    assert _in_quiet_hours(pref, inside) is True
    assert _in_quiet_hours(pref, outside) is False


def test_quiet_hours_respects_day_filter():
    # Weekdays only (Mon-Fri). 2026-05-17 is a Sunday (weekday 6).
    pref = _pref(quiet_hours_days=[0, 1, 2, 3, 4])
    sunday_night = datetime(2026, 5, 17, 2, 0, tzinfo=timezone.utc)
    monday_night = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
    assert _in_quiet_hours(pref, sunday_night) is False
    assert _in_quiet_hours(pref, monday_night) is True


def test_quiet_hours_malformed_times_fail_open():
    pref = _pref(quiet_hours_start="nope", quiet_hours_end="08:00")
    now = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
    assert _in_quiet_hours(pref, now) is False


# --- should_send_email DB-backed behavior ---


@pytest.mark.asyncio
async def test_required_types_always_send(test_db, test_patron):
    """Required types send even when the patron has the channel turned off."""
    pref = UserNotificationPreference(
        user_id=test_patron.id,
        channel_preferences={
            "hold_ready": {"email": False, "in_app": False, "sms": False},
            "overdue_notice": {"email": False},
            "hold_expiring": {"email": False},
        },
        digest_enabled=True,
        quiet_hours_enabled=True,
        quiet_hours_start="00:00",
        quiet_hours_end="23:59",
    )
    test_db.add(pref)
    await test_db.commit()

    for ntype in REQUIRED_NOTIFICATION_TYPES:
        assert await should_send_email(test_patron.id, ntype, test_db) is True


@pytest.mark.asyncio
async def test_no_saved_prefs_allows_email(test_db, test_patron):
    """A patron with no saved preferences gets email by default."""
    assert (
        await should_send_email(test_patron.id, "due_date_reminder", test_db) is True
    )


@pytest.mark.asyncio
async def test_email_channel_off_blocks_send(test_db, test_patron):
    """Turning the email channel off for a non-required type blocks the send."""
    pref = UserNotificationPreference(
        user_id=test_patron.id,
        channel_preferences={"due_date_reminder": {"email": False}},
    )
    test_db.add(pref)
    await test_db.commit()

    assert (
        await should_send_email(test_patron.id, "due_date_reminder", test_db) is False
    )


@pytest.mark.asyncio
async def test_digest_mode_suppresses_non_required(test_db, test_patron):
    """Digest Mode suppresses immediate email for non-required types."""
    pref = UserNotificationPreference(
        user_id=test_patron.id,
        channel_preferences={"due_date_reminder": {"email": True}},
        digest_enabled=True,
    )
    test_db.add(pref)
    await test_db.commit()

    assert (
        await should_send_email(test_patron.id, "due_date_reminder", test_db) is False
    )


@pytest.mark.asyncio
async def test_quiet_hours_blocks_non_required(test_db, test_patron):
    """A non-required email is held when 'now' falls inside Quiet Hours."""
    pref = UserNotificationPreference(
        user_id=test_patron.id,
        channel_preferences={"due_date_reminder": {"email": True}},
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        quiet_hours_days=[0, 1, 2, 3, 4, 5, 6],
    )
    test_db.add(pref)
    await test_db.commit()

    quiet = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
    awake = datetime(2026, 5, 18, 14, 0, tzinfo=timezone.utc)
    assert (
        await should_send_email(
            test_patron.id, "due_date_reminder", test_db, now=quiet
        )
        is False
    )
    assert (
        await should_send_email(
            test_patron.id, "due_date_reminder", test_db, now=awake
        )
        is True
    )


# --- should_send_email_by_email (email-resolve variant) ---


@pytest.mark.asyncio
async def test_by_email_channel_off_blocks_send(test_db, test_patron):
    """Resolved-by-email: event channel off for the patron blocks the send."""
    pref = UserNotificationPreference(
        user_id=test_patron.id,
        channel_preferences={"event_reminder": {"email": False}},
    )
    test_db.add(pref)
    await test_db.commit()

    assert (
        await should_send_email_by_email(
            test_patron.email, "event_reminder", test_db
        )
        is False
    )


@pytest.mark.asyncio
async def test_by_email_quiet_hours_blocks_authenticated(test_db, test_patron):
    """Resolved-by-email: Quiet Hours suppresses the send when 'now' is inside."""
    pref = UserNotificationPreference(
        user_id=test_patron.id,
        channel_preferences={"event_reminder": {"email": True}},
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        quiet_hours_days=[0, 1, 2, 3, 4, 5, 6],
    )
    test_db.add(pref)
    await test_db.commit()

    quiet = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
    awake = datetime(2026, 5, 18, 14, 0, tzinfo=timezone.utc)
    assert (
        await should_send_email_by_email(
            test_patron.email, "event_reminder", test_db, now=quiet
        )
        is False
    )
    assert (
        await should_send_email_by_email(
            test_patron.email, "event_reminder", test_db, now=awake
        )
        is True
    )


@pytest.mark.asyncio
async def test_by_email_guest_registration_sends_freely(test_db):
    """Resolved-by-email: a guest (no matching user) has no prefs to honor."""
    assert (
        await should_send_email_by_email(
            "unknown-guest@example.com", "event_reminder", test_db
        )
        is True
    )
