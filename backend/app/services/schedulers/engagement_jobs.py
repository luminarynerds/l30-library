# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.engagement import (Survey, SurveyPlacement, SurveyResponse,
                                  SurveyResponseStatus)
from ...models.learning import Enrollment
from ...models.notification import (Notification, NotificationStatus,
                                    NotificationType)

settings = get_settings()
logger = get_logger(__name__)

# Tokens live this long after dispatch. Keep generous (real-world delivery
# delays + people opening email weeks later) but bounded to limit exposure.
TOKEN_TTL_DAYS = 21


def _make_token() -> str:
    return secrets.token_urlsafe(32)


def _survey_link(token: str) -> str:
    base = (settings.frontend_url or "").rstrip("/")
    # Frontend mounts SurveyResponsePage at /survey/respond/:token
    return f"{base}/survey/respond/{token}"


async def _dispatch_for_survey(
    db: AsyncSession, survey: Survey, now: datetime
) -> int:
    if survey.trigger_offset_days is None:
        return 0
    target_window_end = now - timedelta(days=survey.trigger_offset_days)
    # 1-day window keeps the daily job picking up everyone exactly once.
    target_window_start = target_window_end - timedelta(days=1)

    enrollment_stmt = select(Enrollment).where(
        Enrollment.completed_at.isnot(None),
        Enrollment.completed_at >= target_window_start,
        Enrollment.completed_at < target_window_end,
    )
    if survey.course_id is not None:
        enrollment_stmt = enrollment_stmt.where(
            Enrollment.course_id == survey.course_id
        )
    enrollments = (await db.execute(enrollment_stmt)).scalars().all()

    sent = 0
    for enrollment in enrollments:
        # Skip if user already has any response for this survey.
        already = (await db.execute(
            select(SurveyResponse.id).where(
                SurveyResponse.user_id == enrollment.user_id,
                SurveyResponse.survey_id == survey.id,
            )
        )).scalar_one_or_none()
        if already is not None:
            continue

        token = _make_token()
        response = SurveyResponse(
            user_id=enrollment.user_id,
            survey_id=survey.id,
            course_id=enrollment.course_id,
            enrollment_id=enrollment.id,
            status=SurveyResponseStatus.PENDING.value,
            delivery_token=token,
            delivery_token_expires_at=now + timedelta(days=TOKEN_TTL_DAYS),
        )
        db.add(response)

        notification = Notification(
            user_id=enrollment.user_id,
            notification_type=NotificationType.TRAINING_WEEKLY_DIGEST,
            status=NotificationStatus.PENDING,
            subject="Quick check-in: how have those AI skills served you?",
            message=(
                f"It's been {survey.trigger_offset_days} days since you "
                "finished the course. We'd love to know if these skills "
                "helped your career or community. Your success stories are "
                "what keep these programs free for everyone.\n\n"
                f"Take the 3-minute survey: {_survey_link(token)}"
            ),
            context_data={
                "survey_id": survey.id,
                "course_id": enrollment.course_id,
                "delivery_token": token,
            },
        )
        db.add(notification)
        sent += 1

    if sent:
        logger.info(
            "engagement.longitudinal: survey_id=%s dispatched=%d",
            survey.id, sent,
        )
    return sent


async def dispatch_longitudinal_surveys() -> dict:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        survey_stmt = select(Survey).where(
            Survey.is_published.is_(True),
            Survey.deleted_at.is_(None),
            Survey.placement == SurveyPlacement.LONGITUDINAL.value,
            Survey.trigger_offset_days.isnot(None),
        )
        surveys = (await db.execute(survey_stmt)).scalars().all()
        total = 0
        for survey in surveys:
            try:
                total += await _dispatch_for_survey(db, survey, now)
                await db.commit()
            except Exception:
                logger.exception("engagement.longitudinal: failed survey_id=%s", survey.id)
                await db.rollback()
    return {"surveys_processed": len(surveys), "dispatches_created": total}
