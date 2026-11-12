# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.core.logging import get_logger

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func as sa_func

from ..models.ebook_access_card import EbookAccessCard, EbookCardStatus
from ..models.ebook_checkout_log import EbookCheckoutLog
from ..core.database import get_db
from ..core.email import send_email

logger = get_logger(__name__)


async def reset_monthly_borrows(db: AsyncSession) -> dict:
    try:
        # Get all active cards
        query = select(EbookAccessCard).where(
            EbookAccessCard.status == EbookCardStatus.ACTIVE
        )
        result = await db.execute(query)
        cards = result.scalars().all()

        count = 0
        for card in cards:
            if hasattr(card, 'borrows_this_month'):
                card.borrows_this_month = 0
                count += 1

        await db.commit()
        logger.info(f"Reset monthly borrow counters for {count} active cards")

        return {
            "status": "success",
            "cards_reset": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:  # noqa: BLE001 - scheduler job boundary — must not crash scheduler
        logger.error(f"Failed to reset monthly borrows: {str(e)}")
        await db.rollback()
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def expire_and_notify_cards(db: AsyncSession) -> dict:
    try:
        now = datetime.now(timezone.utc)
        expired_count = 0
        reminded_count = 0

        # 1. Expire cards past their expiration date
        query = select(EbookAccessCard).where(
            and_(
                EbookAccessCard.status == EbookCardStatus.ACTIVE,
                EbookAccessCard.expires_at < now,
            )
        )
        result = await db.execute(query)
        expired_cards = result.scalars().all()

        for card in expired_cards:
            card.status = EbookCardStatus.EXPIRED
            expired_count += 1

            # Send expiration notification
            if card.user and card.user.email:
                await send_email(
                    to=card.user.email,
                    subject="Your Ebook Access Card Has Expired",
                    template="ebook_card_expired",
                    context={
                        "user_name": card.user.display_name or card.user.email,
                        "card_number": card.card_number,
                        "tier": card.tier,
                        "renewal_url": f"https://l30.org/indie/vault/subscribe",
                    },
                )

        # 2. Send renewal reminders to cards expiring in 7 days
        reminder_date = now + timedelta(days=7)
        query = select(EbookAccessCard).where(
            and_(
                EbookAccessCard.status == EbookCardStatus.ACTIVE,
                EbookAccessCard.expires_at <= reminder_date,
                EbookAccessCard.expires_at > now,
            )
        )
        result = await db.execute(query)
        expiring_soon = result.scalars().all()

        for card in expiring_soon:
            if card.user and card.user.email:
                days_left = (card.expires_at - now).days
                await send_email(
                    to=card.user.email,
                    subject=f"Your Ebook Access Card Expires in {days_left} Days",
                    template="ebook_card_renewal_reminder",
                    context={
                        "user_name": card.user.display_name or card.user.email,
                        "card_number": card.card_number,
                        "tier": card.tier,
                        "days_left": days_left,
                        "renewal_url": f"https://l30.org/indie/vault/subscribe",
                    },
                )
                reminded_count += 1

        await db.commit()
        logger.info(
            f"Expired {expired_count} cards, sent {reminded_count} renewal reminders"
        )

        return {
            "status": "success",
            "expired": expired_count,
            "reminders_sent": reminded_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:  # noqa: BLE001 - scheduler job boundary — must not crash scheduler
        logger.error(f"Failed to expire and notify cards: {str(e)}")
        await db.rollback()
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def send_monthly_digest(db: AsyncSession) -> dict:
    try:
        # Get all active Standard and Unlimited cards
        query = select(EbookAccessCard).where(
            and_(
                EbookAccessCard.status == EbookCardStatus.ACTIVE,
                EbookAccessCard.tier.in_(["standard", "unlimited"]),
            )
        )
        result = await db.execute(query)
        cards = result.scalars().all()

        now = datetime.now(timezone.utc)
        sent_count = 0
        for card in cards:
            if card.user and card.user.email:
                # Get reading stats for the previous month
                last_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                last_month_end = now.replace(day=1)

                # Count borrows last month
                borrows_last_month_q = select(sa_func.count()).where(
                    and_(
                        EbookCheckoutLog.user_id == card.user_id,
                        EbookCheckoutLog.action == "borrow",
                        EbookCheckoutLog.recorded_at >= last_month_start,
                        EbookCheckoutLog.recorded_at < last_month_end,
                    )
                )
                borrows_last_month_result = await db.execute(borrows_last_month_q)
                borrows_last_month = borrows_last_month_result.scalar() or 0

                # Get 5 most recent borrows
                recent_borrows_q = (
                    select(EbookCheckoutLog)
                    .where(
                        and_(
                            EbookCheckoutLog.user_id == card.user_id,
                            EbookCheckoutLog.action == "borrow",
                        )
                    )
                    .order_by(EbookCheckoutLog.recorded_at.desc())
                    .limit(5)
                )
                recent_borrows_result = await db.execute(recent_borrows_q)
                recent_borrows = [
                    {
                        "title": row.ebook_title,
                        "author": row.ebook_author,
                        "source": row.source,
                        "borrowed_at": row.recorded_at.isoformat(),
                    }
                    for row in recent_borrows_result.scalars().all()
                ]

                await send_email(
                    to=card.user.email,
                    subject="Your Monthly Reading Digest",
                    template="monthly_reading_digest",
                    context={
                        "user_name": card.user.display_name or card.user.email,
                        "card_number": card.card_number,
                        "tier": card.tier,
                        "borrows_last_month": borrows_last_month,
                        "total_borrows": card.total_borrows,
                        "recent_borrows": recent_borrows,
                    },
                )
                sent_count += 1

        logger.info(f"Sent {sent_count} monthly digests")
        return {
            "status": "success",
            "digests_sent": sent_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:  # noqa: BLE001 - scheduler job boundary — must not crash scheduler
        logger.error(f"Failed to send monthly digests: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
