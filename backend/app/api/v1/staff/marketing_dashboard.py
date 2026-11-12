# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Marketing dashboard API endpoint."""
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/marketing", tags=["staff-marketing-dashboard"])
logger = get_logger(__name__)


# -- Response schemas ----------------------------------------------------------


class NewsletterStatus(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    section_progress: float = 0.0


class SocialQueueSummary(BaseModel):
    scheduled_count: int = 0
    draft_count: int = 0


class InFlight(BaseModel):
    newsletter: NewsletterStatus = NewsletterStatus()
    social_queue: SocialQueueSummary = SocialQueueSummary()


class Last30Days(BaseModel):
    newsletter_open_rate: float = 0.0
    posts_published: int = 0
    subscriber_count: int = 0


class NeedsPromoProgram(BaseModel):
    id: int
    title: str
    program_date: str
    audience: str
    location: Optional[str] = None
    has_marketing_campaign: bool = False


class MarketingDashboardResponse(BaseModel):
    in_flight: InFlight = InFlight()
    last_30_days: Last30Days = Last30Days()
    needs_promo: list[NeedsPromoProgram] = []


# -- Endpoint ------------------------------------------------------------------


@router.get("/dashboard", response_model=MarketingDashboardResponse)
async def get_marketing_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> MarketingDashboardResponse:
    """Aggregate marketing metrics for the staff dashboard."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    thirty_days_from_now = now + timedelta(days=30)

    in_flight = InFlight()
    last_30 = Last30Days()
    needs_promo: list[NeedsPromoProgram] = []

    # --- Current newsletter (latest draft or scheduled) ---
    try:
        result = await db.execute(
            text("""
                SELECT id, name, subject, status, scheduled_for
                FROM marketing_campaigns
                WHERE campaign_type = 'newsletter'
                  AND status IN ('draft', 'scheduled')
                ORDER BY
                    CASE WHEN status = 'scheduled' THEN 0 ELSE 1 END,
                    COALESCE(scheduled_for, created_at) DESC
                LIMIT 1
            """),
        )
        row = result.fetchone()
        if row:
            in_flight.newsletter = NewsletterStatus(
                id=row[0],
                name=row[1],
                subject=row[2],
                status=row[3],
                scheduled_for=row[4],
                section_progress=0.0,
            )
    except SQLAlchemyError:
        logger.warning("Failed to load newsletter status")

    # --- Social queue (event distributions pending/scheduled) ---
    try:
        result = await db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'scheduled') AS scheduled_count,
                    COUNT(*) FILTER (WHERE status = 'pending') AS draft_count
                FROM event_distributions
                WHERE status IN ('scheduled', 'pending')
            """),
        )
        row = result.fetchone()
        if row:
            in_flight.social_queue = SocialQueueSummary(
                scheduled_count=row[0] or 0,
                draft_count=row[1] or 0,
            )
    except SQLAlchemyError:
        logger.warning("Failed to load social queue summary")

    # --- Last 30 days metrics ---
    try:
        result = await db.execute(
            text("""
                SELECT
                    CASE
                        WHEN SUM(recipients_count) > 0
                        THEN ROUND(
                            SUM(opens_count)::numeric / SUM(recipients_count) * 100, 1
                        )
                        ELSE 0
                    END AS open_rate,
                    COUNT(*) FILTER (WHERE status = 'sent') AS posts_published
                FROM marketing_campaigns
                WHERE sent_at >= :since
            """),
            {"since": thirty_days_ago},
        )
        row = result.fetchone()
        if row:
            last_30.newsletter_open_rate = float(row[0] or 0)
            last_30.posts_published = row[1] or 0
    except SQLAlchemyError:
        logger.warning("Failed to load 30-day marketing metrics")

    # --- Subscriber count ---
    try:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM newsletter_subscriptions WHERE status = 'active'"
            ),
        )
        row = result.fetchone()
        if row:
            last_30.subscriber_count = row[0] or 0
    except SQLAlchemyError:
        logger.warning("Failed to load subscriber count")

    # --- Upcoming programs needing promo ---
    try:
        result = await db.execute(
            text("""
                SELECT
                    p.id, p.title, p.program_date, p.audience, p.location_name,
                    EXISTS (
                        SELECT 1 FROM event_marketing_campaigns emc
                        JOIN events e ON emc.event_id = e.id
                        WHERE e.title = p.title
                          AND DATE(e.start_datetime) = p.program_date
                    ) AS has_campaign
                FROM programs p
                WHERE p.program_date BETWEEN :today AND :horizon
                  AND p.status NOT IN ('cancelled', 'completed')
                ORDER BY p.program_date ASC
                LIMIT 20
            """),
            {"today": now.date(), "horizon": thirty_days_from_now.date()},
        )
        for row in result.fetchall():
            needs_promo.append(NeedsPromoProgram(
                id=row[0],
                title=row[1],
                program_date=str(row[2]),
                audience=row[3] or "all_ages",
                location=row[4],
                has_marketing_campaign=row[5] or False,
            ))
    except SQLAlchemyError:
        logger.warning("Failed to load upcoming programs for promo")

    return MarketingDashboardResponse(
        in_flight=in_flight,
        last_30_days=last_30,
        needs_promo=needs_promo,
    )
