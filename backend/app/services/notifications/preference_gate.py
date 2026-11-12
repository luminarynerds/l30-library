# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.notification import NotificationDigestQueue
from ...models.notification_preference import UserNotificationPreference
from ...models.user import User, email_blind_hash

logger = get_logger(__name__)


# Notification types that must ALWAYS be delivered regardless of channel
# toggles, Quiet Hours, or Digest Mode. Must stay in sync with the frontend
# CRITICAL_NOTIFICATION_TYPES (NotificationPreferencesPage.tsx).
REQUIRED_NOTIFICATION_TYPES: frozenset[str] = frozenset(
    {"hold_ready", "hold_expiring", "overdue_notice"}
)


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    try:
        hh, mm = value.split(":")
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (ValueError, AttributeError):
        pass
    return None


def _in_quiet_hours(pref: UserNotificationPreference, now: datetime) -> bool:
    if not pref.quiet_hours_enabled:
        return False

    days = pref.quiet_hours_days or [0, 1, 2, 3, 4, 5, 6]
    if now.weekday() not in days:
        return False

    start = _parse_hhmm(pref.quiet_hours_start or "22:00")
    end = _parse_hhmm(pref.quiet_hours_end or "08:00")
    if start is None or end is None:
        return False

    now_minutes = now.hour * 60 + now.minute
    start_minutes = start[0] * 60 + start[1]
    end_minutes = end[0] * 60 + end[1]

    if start_minutes == end_minutes:
        # Zero-length window: never quiet.
        return False
    if start_minutes < end_minutes:
        # Same-day window, e.g. 09:00 -> 17:00.
        return start_minutes <= now_minutes < end_minutes
    # Wrapping window, e.g. 22:00 -> 08:00.
    return now_minutes >= start_minutes or now_minutes < end_minutes


async def _enqueue_digest_item(
    db: AsyncSession,
    user_id: int,
    notification_type: str,
    summary: str,
    context_data: dict | None,
    dedup_key: str,
) -> None:
    item = NotificationDigestQueue(
        user_id=user_id,
        notification_type=notification_type,
        summary=summary[:500],
        context_data=context_data,
        dedup_key=(dedup_key or "")[:128],
    )
    try:
        async with db.begin_nested():
            db.add(item)
            await db.flush()
    except IntegrityError:
        # Most likely a duplicate (already queued this event). Suppression is
        # still correct -- the patron will get the already-queued copy.
        logger.debug(
            "Digest item not enqueued (likely duplicate)",
            extra={"user_id": user_id, "notification_type": notification_type},
        )


async def should_send_email(
    user_id: int,
    notification_type: str,
    db: AsyncSession,
    *,
    now: datetime | None = None,
    summary: str | None = None,
    context_data: dict | None = None,
    dedup_key: str | None = None,
) -> bool:
    if notification_type in REQUIRED_NOTIFICATION_TYPES:
        return True

    try:
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id
        )
        result = await db.execute(stmt)
        pref = result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.warning(
            "Notification preference lookup failed; failing open",
            extra={"user_id": user_id, "notification_type": notification_type},
            exc_info=True,
        )
        return True

    if pref is None:
        # No saved preferences: defaults allow email (matches the UI default).
        return True

    channels = pref.channel_preferences or {}
    type_prefs = channels.get(notification_type, {})

    if type_prefs.get("email", True) is False:
        return False

    if pref.digest_enabled:
        # Digest Mode: suppress the immediate per-event email. When the caller
        # supplies digest content, enqueue it for the batched summary email
        # built by the send_notification_digests job.
        if summary is not None:
            await _enqueue_digest_item(
                db, user_id, notification_type, summary, context_data, dedup_key or ""
            )
        return False

    if _in_quiet_hours(pref, now or datetime.now(timezone.utc)):
        return False

    return True


async def should_send_email_by_email(
    email: str | None,
    notification_type: str,
    db: AsyncSession,
    *,
    now: datetime | None = None,
    summary: str | None = None,
    context_data: dict | None = None,
    dedup_key: str | None = None,
) -> bool:
    if notification_type in REQUIRED_NOTIFICATION_TYPES:
        return True

    if not email:
        return True

    try:
        stmt = select(User.id).where(User.email_hash == email_blind_hash(email))
        result = await db.execute(stmt)
        user_id = result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.warning(
            "User-by-email lookup failed; failing open",
            extra={"notification_type": notification_type},
            exc_info=True,
        )
        return True

    if user_id is None:
        # Guest registration -- no account, no preferences to honor.
        return True

    return await should_send_email(
        user_id,
        notification_type,
        db,
        now=now,
        summary=summary,
        context_data=context_data,
        dedup_key=dedup_key,
    )
