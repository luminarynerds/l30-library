# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preference import UserNotificationPreference
from app.schemas.notification_preferences import (
    NotificationChannelPreference,
    NotificationPreferencesResponse,
    DigestConfig,
    QuietHoursConfig,
    FullNotificationSettings,
)


# Default notification types with their labels
DEFAULT_NOTIFICATION_TYPES = [
    ("checkout_receipt", "Checkout Receipt", "Email confirmation when you check out items"),
    ("due_date_reminder", "Due Date Reminder", "Reminder before items are due"),
    ("overdue_notice", "Overdue Notice", "Notification when items become overdue"),
    ("hold_ready", "Hold Ready", "When holds are ready for pickup"),
    ("hold_expiring", "Hold Expiring", "Reminder before holds expire"),
    ("hold_cancelled", "Hold Cancelled", "When a hold is cancelled"),
    ("fine_notice", "Fine Notice", "Notifications about fines"),
    ("event_reminder", "Event Reminder", "Reminders for registered events"),
    ("reading_program", "Reading Program", "Updates on reading program progress"),
    ("new_arrivals", "New Arrivals", "When new items match your interests"),
    ("indie_author_release_digest", "Indie Author Release Digest", "Weekly summary when indie authors you follow publish new books"),
    ("book_club", "Book Club", "Book club discussions and meetings"),
    ("system_announcement", "System Announcements", "Library-wide announcements"),
]

# Lookup for label/description by type key
_TYPE_META = {ntype: (label, desc) for ntype, label, desc in DEFAULT_NOTIFICATION_TYPES}


def _build_default_pref(ntype: str, label: str, desc: str) -> NotificationChannelPreference:
    return NotificationChannelPreference(
        notification_type=ntype,
        label=label,
        description=desc,
        channel_email=True,
        channel_in_app=True,
        channel_sms=False,
        is_digest=False,
    )


def _merge_preferences(saved: dict) -> List[NotificationChannelPreference]:
    result = []
    for ntype, label, desc in DEFAULT_NOTIFICATION_TYPES:
        if ntype in saved:
            s = saved[ntype]
            result.append(NotificationChannelPreference(
                notification_type=ntype,
                label=label,
                description=desc,
                channel_email=s.get("email", True),
                channel_in_app=s.get("in_app", True),
                channel_sms=s.get("sms", False),
                is_digest=s.get("is_digest", False),
            ))
        else:
            result.append(_build_default_pref(ntype, label, desc))
    return result


async def _get_or_none(db: AsyncSession, user_id: int) -> UserNotificationPreference | None:
    stmt = select(UserNotificationPreference).where(
        UserNotificationPreference.user_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


class NotificationPreferencesService:

    @staticmethod
    async def get_preferences(user_id: int, db: AsyncSession) -> NotificationPreferencesResponse:
        row = await _get_or_none(db, user_id)
        saved = row.channel_preferences if row else {}
        prefs = _merge_preferences(saved or {})
        return NotificationPreferencesResponse(preferences=prefs)

    @staticmethod
    async def update_preferences(
        user_id: int,
        preferences: List[NotificationChannelPreference],
        db: AsyncSession,
    ) -> NotificationPreferencesResponse:
        row = await _get_or_none(db, user_id)

        # Build the JSON blob from the incoming preferences list
        channel_data = {}
        for p in preferences:
            channel_data[p.notification_type] = {
                "email": p.channel_email,
                "in_app": p.channel_in_app,
                "sms": p.channel_sms,
                "is_digest": p.is_digest,
            }

        if row is None:
            row = UserNotificationPreference(
                user_id=user_id,
                channel_preferences=channel_data,
            )
            db.add(row)
        else:
            row.channel_preferences = channel_data

        await db.flush()

        # Return merged view (includes defaults for types not in the update)
        merged = _merge_preferences(channel_data)
        return NotificationPreferencesResponse(preferences=merged)

    @staticmethod
    async def get_digest_config(user_id: int, db: AsyncSession) -> DigestConfig:
        row = await _get_or_none(db, user_id)
        if row is None:
            return DigestConfig()
        return DigestConfig(
            enabled=row.digest_enabled,
            frequency=row.digest_frequency,
            preferred_time=row.digest_preferred_time,
            preferred_day=row.digest_preferred_day,
        )

    @staticmethod
    async def update_digest_config(
        user_id: int, config: DigestConfig, db: AsyncSession
    ) -> DigestConfig:
        row = await _get_or_none(db, user_id)
        if row is None:
            row = UserNotificationPreference(
                user_id=user_id,
                channel_preferences={},
            )
            db.add(row)

        row.digest_enabled = config.enabled
        row.digest_frequency = config.frequency
        row.digest_preferred_time = config.preferred_time
        row.digest_preferred_day = config.preferred_day

        await db.flush()
        return config

    @staticmethod
    async def get_quiet_hours(user_id: int, db: AsyncSession) -> QuietHoursConfig:
        row = await _get_or_none(db, user_id)
        if row is None:
            return QuietHoursConfig()
        return QuietHoursConfig(
            enabled=row.quiet_hours_enabled,
            start_time=row.quiet_hours_start,
            end_time=row.quiet_hours_end,
            days=row.quiet_hours_days or [0, 1, 2, 3, 4, 5, 6],
        )

    @staticmethod
    async def update_quiet_hours(
        user_id: int, config: QuietHoursConfig, db: AsyncSession
    ) -> QuietHoursConfig:
        row = await _get_or_none(db, user_id)
        if row is None:
            row = UserNotificationPreference(
                user_id=user_id,
                channel_preferences={},
            )
            db.add(row)

        row.quiet_hours_enabled = config.enabled
        row.quiet_hours_start = config.start_time
        row.quiet_hours_end = config.end_time
        row.quiet_hours_days = config.days

        await db.flush()
        return config

    @staticmethod
    async def get_full_settings(user_id: int, db: AsyncSession) -> FullNotificationSettings:
        prefs = await NotificationPreferencesService.get_preferences(user_id, db)
        digest = await NotificationPreferencesService.get_digest_config(user_id, db)
        quiet = await NotificationPreferencesService.get_quiet_hours(user_id, db)
        return FullNotificationSettings(
            preferences=prefs.preferences,
            digest=digest,
            quiet_hours=quiet,
        )
