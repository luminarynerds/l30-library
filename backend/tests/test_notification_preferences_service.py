# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for NotificationPreferencesService persistence.
"""

import pytest

from app.services.notification_preferences_service import (
    NotificationPreferencesService,
    DEFAULT_NOTIFICATION_TYPES,
)
from app.schemas.notification_preferences import (
    NotificationChannelPreference,
    DigestConfig,
    QuietHoursConfig,
)


@pytest.mark.asyncio
async def test_get_preferences_returns_defaults_for_new_user(test_db, test_patron):
    """A user with no saved prefs should get every default type."""
    result = await NotificationPreferencesService.get_preferences(
        user_id=test_patron.id, db=test_db
    )

    assert len(result.preferences) == len(DEFAULT_NOTIFICATION_TYPES)

    for pref in result.preferences:
        assert pref.channel_email is True
        assert pref.channel_in_app is True
        assert pref.channel_sms is False
        assert pref.is_digest is False

    # Verify all expected types are present
    types_returned = {p.notification_type for p in result.preferences}
    types_expected = {t[0] for t in DEFAULT_NOTIFICATION_TYPES}
    assert types_returned == types_expected


@pytest.mark.asyncio
async def test_update_preferences_persists_and_is_retrievable(test_db, test_patron):
    """Updating preferences should persist them and be retrievable."""
    updates = [
        NotificationChannelPreference(
            notification_type="checkout_receipt",
            label="Checkout Receipt",
            description="Email confirmation when you check out items",
            channel_email=False,
            channel_in_app=True,
            channel_sms=True,
            is_digest=False,
        ),
        NotificationChannelPreference(
            notification_type="hold_ready",
            label="Hold Ready",
            description="When holds are ready for pickup",
            channel_email=True,
            channel_in_app=False,
            channel_sms=True,
            is_digest=True,
        ),
    ]

    await NotificationPreferencesService.update_preferences(
        user_id=test_patron.id, preferences=updates, db=test_db
    )
    await test_db.commit()

    # Re-fetch and verify
    result = await NotificationPreferencesService.get_preferences(
        user_id=test_patron.id, db=test_db
    )

    # Should still have every type (defaults fill in the rest)
    assert len(result.preferences) == len(DEFAULT_NOTIFICATION_TYPES)

    by_type = {p.notification_type: p for p in result.preferences}

    checkout = by_type["checkout_receipt"]
    assert checkout.channel_email is False
    assert checkout.channel_sms is True

    hold = by_type["hold_ready"]
    assert hold.channel_in_app is False
    assert hold.channel_sms is True
    assert hold.is_digest is True

    # Unsaved type should still have defaults
    fine = by_type["fine_notice"]
    assert fine.channel_email is True
    assert fine.channel_sms is False


@pytest.mark.asyncio
async def test_digest_config_persists(test_db, test_patron):
    """Updating digest config should persist and be retrievable."""
    # Defaults first
    defaults = await NotificationPreferencesService.get_digest_config(
        user_id=test_patron.id, db=test_db
    )
    assert defaults.enabled is False
    assert defaults.frequency == "daily"

    # Update
    new_config = DigestConfig(
        enabled=True,
        frequency="weekly",
        preferred_time="18:00",
        preferred_day=4,
    )
    await NotificationPreferencesService.update_digest_config(
        user_id=test_patron.id, config=new_config, db=test_db
    )
    await test_db.commit()

    # Retrieve
    result = await NotificationPreferencesService.get_digest_config(
        user_id=test_patron.id, db=test_db
    )
    assert result.enabled is True
    assert result.frequency == "weekly"
    assert result.preferred_time == "18:00"
    assert result.preferred_day == 4


@pytest.mark.asyncio
async def test_quiet_hours_persists(test_db, test_patron):
    """Updating quiet hours should persist and be retrievable."""
    # Defaults first
    defaults = await NotificationPreferencesService.get_quiet_hours(
        user_id=test_patron.id, db=test_db
    )
    assert defaults.enabled is False
    assert defaults.start_time == "22:00"

    # Update
    new_config = QuietHoursConfig(
        enabled=True,
        start_time="23:00",
        end_time="07:00",
        days=[0, 1, 2, 3, 4],  # Weekdays only
    )
    await NotificationPreferencesService.update_quiet_hours(
        user_id=test_patron.id, config=new_config, db=test_db
    )
    await test_db.commit()

    # Retrieve
    result = await NotificationPreferencesService.get_quiet_hours(
        user_id=test_patron.id, db=test_db
    )
    assert result.enabled is True
    assert result.start_time == "23:00"
    assert result.end_time == "07:00"
    assert result.days == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_get_full_settings(test_db, test_patron):
    """get_full_settings should return preferences, digest, and quiet hours together."""
    result = await NotificationPreferencesService.get_full_settings(
        user_id=test_patron.id, db=test_db
    )

    assert len(result.preferences) == len(DEFAULT_NOTIFICATION_TYPES)
    assert result.digest.enabled is False
    assert result.quiet_hours.enabled is False


@pytest.mark.asyncio
async def test_update_preferences_upsert(test_db, test_patron):
    """Calling update twice should upsert, not create duplicate rows."""
    first = [
        NotificationChannelPreference(
            notification_type="checkout_receipt",
            label="Checkout Receipt",
            channel_email=False,
            channel_sms=True,
        ),
    ]
    await NotificationPreferencesService.update_preferences(
        user_id=test_patron.id, preferences=first, db=test_db
    )
    await test_db.commit()

    second = [
        NotificationChannelPreference(
            notification_type="checkout_receipt",
            label="Checkout Receipt",
            channel_email=True,
            channel_sms=False,
        ),
    ]
    await NotificationPreferencesService.update_preferences(
        user_id=test_patron.id, preferences=second, db=test_db
    )
    await test_db.commit()

    result = await NotificationPreferencesService.get_preferences(
        user_id=test_patron.id, db=test_db
    )
    by_type = {p.notification_type: p for p in result.preferences}
    assert by_type["checkout_receipt"].channel_email is True
    assert by_type["checkout_receipt"].channel_sms is False
