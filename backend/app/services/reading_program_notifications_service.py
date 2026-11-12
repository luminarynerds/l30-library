# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationStatus, NotificationType
from app.models.reading import (
    ReadingLogEntry,
    ReadingProgram,
    ReadingRegistration,
)
from app.services.notification_preferences_service import (
    NotificationPreferencesService,
)

logger = get_logger(__name__)

# Order matters: higher thresholds tested first so we pick the maximum
# crossed in one pass.
PROGRESS_THRESHOLDS = (80, 50)


async def maybe_send_progress_nudge(
    db: AsyncSession, registration_id: int
) -> Optional[Notification]:
    registration = await db.get(ReadingRegistration, registration_id)
    if registration is None:
        return None

    program = await db.get(ReadingProgram, registration.program_id)
    if program is None or not registration.goal_target:
        return None

    pct = await _compute_completion_pct(db, registration, program)
    threshold = _highest_crossed(pct)
    if threshold is None:
        return None

    if not await _user_opted_in(db, registration.user_id):
        logger.debug(
            "rp-notify: user=%s opted out of reading_program; skipping nudge",
            registration.user_id,
        )
        return None

    if await _already_sent(db, registration, threshold):
        return None

    return await _insert_progress_nudge(db, registration, program, threshold, pct)


async def _compute_completion_pct(
    db: AsyncSession,
    registration: ReadingRegistration,
    program: ReadingProgram,
) -> float:
    from sqlalchemy import func

    metric_col = {
        "minutes": func.coalesce(func.sum(ReadingLogEntry.minutes_read), 0),
        "books": func.coalesce(func.sum(ReadingLogEntry.books_read), 0),
        "pages": func.coalesce(func.sum(ReadingLogEntry.pages_read), 0),
    }.get(program.reading_goal_type)

    if metric_col is None or not registration.goal_target:
        return 0.0

    total = (
        await db.execute(
            select(metric_col).where(
                ReadingLogEntry.registration_id == registration.id
            )
        )
    ).scalar() or 0

    return (float(total) / registration.goal_target) * 100.0


def _highest_crossed(pct: float) -> Optional[int]:
    for threshold in PROGRESS_THRESHOLDS:
        if pct >= threshold:
            return threshold
    return None


async def _user_opted_in(db: AsyncSession, user_id: int) -> bool:
    prefs = await NotificationPreferencesService.get_preferences(user_id, db)
    for entry in prefs.preferences:
        if entry.notification_type == "reading_program":
            # Honor email + in-app channels: if either is on, we still create
            # the Notification row. The send worker will pick the channel.
            return bool(entry.channel_email or entry.channel_in_app)
    # No saved preference -> default is on (matches the rest of the
    # notification_preferences_service merge logic).
    return True


async def _already_sent(
    db: AsyncSession, registration: ReadingRegistration, threshold: int
) -> bool:
    rows = (
        (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == registration.user_id,
                    Notification.notification_type
                    == NotificationType.READING_PROGRAM_PROGRESS_NUDGE,
                )
            )
        )
        .scalars()
        .all()
    )
    for n in rows:
        ctx = n.context_data or {}
        if (
            ctx.get("registration_id") == registration.id
            and ctx.get("threshold") == threshold
        ):
            return True
    return False


async def try_send_progress_nudge_safe(
    db: AsyncSession, registration_id: int
) -> Optional[Notification]:
    try:
        notification = await maybe_send_progress_nudge(db, registration_id)
        if notification is not None:
            await db.commit()
        return notification
    except Exception:  # noqa: BLE001 -- best-effort side channel
        logger.exception(
            "rp-notify: progress nudge failed for registration=%s",
            registration_id,
        )
        with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort rollback after nudge failure
            await db.rollback()
        return None


async def _insert_progress_nudge(
    db: AsyncSession,
    registration: ReadingRegistration,
    program: ReadingProgram,
    threshold: int,
    pct: float,
) -> Notification:
    subject = f"You're {threshold}% to your {program.name} goal!"
    message = (
        f"Nice work -- you've logged {round(pct)}% of your reading goal for "
        f"\"{program.name}\". Keep it up!"
    )
    notification = Notification(
        user_id=registration.user_id,
        notification_type=NotificationType.READING_PROGRAM_PROGRESS_NUDGE,
        status=NotificationStatus.PENDING,
        subject=subject,
        message=message,
        context_data={
            "program_id": program.id,
            "registration_id": registration.id,
            "threshold": threshold,
            "completion_pct": round(pct, 2),
        },
    )
    db.add(notification)
    await db.flush()
    return notification
