# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.email import send_email
from ..models.ban_tracker import BanReport, BanTrackerSubscription
from ..models.user import User
from .ban_tracker_digest_email import render_digest_email

logger = get_logger(__name__)

# Cap per digest. If we hit this, the email mentions the cap so the
# patron knows there are more reports to see on the site. Picked to
# keep the digest readable and well under Resend's payload limits.
DIGEST_REPORT_CAP = 50


async def compute_digest_for_subscription(
    db: AsyncSession,
    subscription: BanTrackerSubscription,
) -> list[BanReport]:
    # created_at, not date_reported -- date_reported is nullable + Date
    # not DateTime, so it's unreliable as a cursor; created_at is the
    # row's insertion-time and what we actually want for "what's new
    # since the last digest".
    cursor = subscription.last_sent_at or subscription.created_at

    stmt = select(BanReport).where(BanReport.created_at > cursor)

    if subscription.scope == "state":
        if not subscription.state_filter:
            return []
        stmt = stmt.where(BanReport.state == subscription.state_filter)
    elif subscription.scope == "catalog":
        stmt = stmt.where(BanReport.catalog_match_id.isnot(None))
    # 'any' -> no extra filter

    if subscription.ban_type_filter:
        # The enum is stored lowercase (BanType values: 'challenged',
        # 'restricted', 'banned', 'pending') but the BanReport schemas
        # uppercase user input in their validators. Normalize before
        # comparing or this filter silently returns 0 rows.
        stmt = stmt.where(BanReport.ban_type == subscription.ban_type_filter.lower())

    stmt = stmt.order_by(BanReport.created_at.asc()).limit(DIGEST_REPORT_CAP)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def send_digest(
    db: AsyncSession,
    subscription: BanTrackerSubscription,
    dry_run: bool = False,
) -> bool:
    settings = get_settings()

    # Eager-load the user relationship -- accessing subscription.user
    # mid-serialization in async context will MissingGreenlet otherwise.
    user = subscription.user
    if user is None:
        # Could happen mid-cascade if the user was deleted between job
        # tick and now. Skip silently rather than 500 the whole batch.
        return False

    reports = await compute_digest_for_subscription(db, subscription)
    if not reports:
        return False

    capped = len(reports) == DIGEST_REPORT_CAP

    subject_n = len(reports)
    subject = (
        f"This week's ban tracker digest -- {subject_n} new report(s)"
        if subscription.frequency == "weekly"
        else f"Today's ban tracker digest -- {subject_n} new report(s)"
    )

    unsubscribe_url = (
        f"{settings.frontend_url}/api/v1/ban-tracker/unsubscribe"
        f"?token={subscription.unsubscribe_token}"
    )

    html = render_digest_email(
        user=user,
        subscription=subscription,
        reports=reports,
        capped=capped,
        unsubscribe_url=unsubscribe_url,
        site_url=settings.frontend_url,
    )

    if dry_run:
        logger.info(
            "ban_tracker digest dry-run",
            extra={
                "subscription_id": subscription.id,
                "user_id": user.id,
                "report_count": subject_n,
                "capped": capped,
            },
        )
        return True

    sent = await send_email(
        to_email=user.email,
        subject=subject,
        html_content=html,
        unsubscribe_url=unsubscribe_url,
        categories=["ban_tracker_digest", f"sub_{subscription.id}"],
    )

    if not sent:
        # send_email returns False on daily cap, provider error, etc.
        # Leave last_sent_at alone so the next cron tick retries.
        logger.warning(
            "ban_tracker digest send refused",
            extra={"subscription_id": subscription.id, "user_id": user.id},
        )
        return False

    subscription.last_sent_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def run_subscription_digest_job(
    db: AsyncSession, frequency: str
) -> dict[str, int]:
    if frequency not in ("daily", "weekly"):
        raise ValueError(f"invalid frequency: {frequency!r}")

    stmt = (
        select(BanTrackerSubscription)
        .where(
            BanTrackerSubscription.is_active.is_(True),
            BanTrackerSubscription.frequency == frequency,
        )
        .options(selectinload(BanTrackerSubscription.user))
    )
    result = await db.execute(stmt)
    subs = list(result.scalars().all())

    counters = {"sent": 0, "skipped": 0, "errors": 0}
    for sub in subs:
        try:
            ok = await send_digest(db, sub, dry_run=False)
            if ok:
                counters["sent"] += 1
            else:
                counters["skipped"] += 1
        except Exception as exc:  # noqa: BLE001
            counters["errors"] += 1
            logger.exception(
                "ban_tracker digest job: subscription failed",
                extra={"subscription_id": sub.id, "error": str(exc)},
            )

    logger.info(
        "ban_tracker digest job complete",
        extra={"frequency": frequency, **counters, "total": len(subs)},
    )
    return counters
