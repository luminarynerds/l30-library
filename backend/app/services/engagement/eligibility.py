# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.engagement import (Survey, SurveyPlacement, SurveyResponse,
                                  SurveyResponseStatus)


async def has_completed(
    db: AsyncSession, user_id: int, survey_id: int
) -> bool:
    stmt = select(SurveyResponse.id).where(
        SurveyResponse.user_id == user_id,
        SurveyResponse.survey_id == survey_id,
        SurveyResponse.status.in_(
            [SurveyResponseStatus.COMPLETED.value,
             SurveyResponseStatus.SKIPPED.value]
        ),
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def list_pending_for_user(
    db: AsyncSession,
    user_id: int,
    course_id: Optional[int] = None,
) -> List[Survey]:
    # 1) Platform-wide and (optionally) course-scoped Entry Pulses
    pulse_clauses = [Survey.course_id.is_(None)]
    if course_id is not None:
        pulse_clauses.append(Survey.course_id == course_id)

    pulse_stmt = select(Survey).where(
        Survey.is_published.is_(True),
        Survey.deleted_at.is_(None),
        Survey.placement == SurveyPlacement.ENTRY_PULSE.value,
        or_(*pulse_clauses),
    )
    candidates = (await db.execute(pulse_stmt)).scalars().all()

    pending: List[Survey] = []
    for survey in candidates:
        if not await has_completed(db, user_id, survey.id):
            pending.append(survey)

    # 2) Surveys with an existing pending response (longitudinal magic-links,
    # in-progress checkins). These were created by the scheduler or a
    # prior session; we surface them here so the dashboard can render them.
    pending_stmt = (
        select(Survey)
        .join(SurveyResponse, SurveyResponse.survey_id == Survey.id)
        .where(
            Survey.is_published.is_(True),
            Survey.deleted_at.is_(None),
            SurveyResponse.user_id == user_id,
            SurveyResponse.status == SurveyResponseStatus.PENDING.value,
        )
    )
    seen_ids = {s.id for s in pending}
    for survey in (await db.execute(pending_stmt)).scalars().all():
        if survey.id not in seen_ids:
            pending.append(survey)
            seen_ids.add(survey.id)

    return pending


async def get_pending_response(
    db: AsyncSession, user_id: int, survey_id: int
) -> Optional[SurveyResponse]:
    stmt = select(SurveyResponse).where(
        SurveyResponse.user_id == user_id,
        SurveyResponse.survey_id == survey_id,
        SurveyResponse.status.in_(
            [SurveyResponseStatus.PENDING.value,
             SurveyResponseStatus.IN_PROGRESS.value]
        ),
    )
    return (await db.execute(stmt)).scalar_one_or_none()
