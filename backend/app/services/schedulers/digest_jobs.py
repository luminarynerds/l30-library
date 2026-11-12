# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import contextlib
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from ...core.database import AsyncSessionLocal
from ...core.email import COLORS, send_email
from ...core.logging import get_logger
from ...models.job_failure import JobSeverity
from ...models.notification import NotificationDigestQueue
from ...models.notification_preference import UserNotificationPreference
from ...models.user import User
from ..job_failure_service import JobExecutionContext

logger = get_logger(__name__)


def _digest_due_now(pref: UserNotificationPreference, now: datetime) -> bool:
    if not pref.digest_enabled:
        return False

    preferred = pref.digest_preferred_time or "09:00"
    try:
        preferred_hour = int(preferred.split(":")[0])
    except (ValueError, AttributeError, IndexError):
        preferred_hour = 9

    if now.hour != preferred_hour:
        return False

    if (pref.digest_frequency or "daily") == "weekly":
        # digest_preferred_day: 0=Monday .. 6=Sunday
        return now.weekday() == (pref.digest_preferred_day or 0)

    return True


def _render_digest_email(user: User, items: list[NotificationDigestQueue]) -> str:
    rows = "".join(
        f'<li style="margin: 8px 0; color: {COLORS["body"]};">{item.summary}</li>'
        for item in items
    )
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Your library activity digest</h2>
        <p>Hi {user.first_name},</p>
        <p>Here is a summary of the library notifications collected since your
           last digest:</p>
        <ul style="padding-left: 20px;">{rows}</ul>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            You are receiving one digest instead of separate emails because
            Digest Mode is on. Change this any time on your notification
            preferences page. Urgent notices (holds ready, overdue items) are
            always sent right away.
        </p>
    </div>
    """


async def send_notification_digests() -> None:
    async with JobExecutionContext(
        "notification_digests",
        "Notification Digest Batching",
        severity=JobSeverity.LOW,
    ) as ctx:
        now = datetime.now(timezone.utc)
        digests_sent = 0

        async with AsyncSessionLocal() as db:
            # Patrons whose digest is due this hour.
            prefs = (
                (
                    await db.execute(
                        select(UserNotificationPreference).where(
                            UserNotificationPreference.digest_enabled.is_(True)
                        )
                    )
                )
                .scalars()
                .all()
            )
            due_user_ids = [p.user_id for p in prefs if _digest_due_now(p, now)]

            if not due_user_ids:
                logger.info("No digests due this hour")
                return

            for user_id in due_user_ids:
                try:
                    items = (
                        (
                            await db.execute(
                                select(NotificationDigestQueue)
                                .where(NotificationDigestQueue.user_id == user_id)
                                .order_by(NotificationDigestQueue.created_at)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if not items:
                        continue

                    user = (
                        await db.execute(select(User).where(User.id == user_id))
                    ).scalar_one_or_none()
                    if not user or not user.email:
                        # Orphaned queue rows (user deleted or has no email):
                        # clear them so they do not accumulate.
                        await db.execute(
                            delete(NotificationDigestQueue).where(
                                NotificationDigestQueue.user_id == user_id
                            )
                        )
                        await db.commit()
                        continue

                    subject = (
                        f"Your library digest: {len(items)} "
                        f"update{'s' if len(items) != 1 else ''}"
                    )
                    html = _render_digest_email(user, items)

                    sent = await send_email(
                        user.email,
                        subject,
                        html,
                        patron_id=user.id,
                        notification_type="digest",
                    )

                    if sent:
                        # Delete only the rows that were in this digest, so a
                        # row enqueued mid-send is not silently dropped.
                        await db.execute(
                            delete(NotificationDigestQueue).where(
                                NotificationDigestQueue.id.in_(
                                    [item.id for item in items]
                                )
                            )
                        )
                        await db.commit()
                        digests_sent += 1
                        ctx.record_success()
                        logger.info(
                            "Sent notification digest",
                            extra={"user_id": user_id, "item_count": len(items)},
                        )
                    else:
                        # Leave the queue intact for the next hourly retry.
                        await db.rollback()
                        ctx.record_failure(
                            Exception("send_email returned False"),
                            entity_type="user",
                            entity_id=user_id,
                        )
                except Exception as e:
                    with contextlib.suppress(SQLAlchemyError):
                        await db.rollback()
                    logger.error(
                        "Failed to send notification digest",
                        extra={"user_id": user_id, "error": str(e)},
                        exc_info=True,
                    )
                    ctx.record_failure(e, entity_type="user", entity_id=user_id)
                    continue

        ctx.add_metric("digests_sent", digests_sent)
        logger.info(
            "Notification digest job completed",
            extra={"digests_sent": digests_sent},
        )
