# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Engagement survey API.

Public (auth required):
  GET    /engagement/me/pending
  GET    /engagement/me/badges
  GET    /engagement/surveys/{id}
  POST   /engagement/surveys/{id}/responses
  POST   /engagement/me/demographics

Magic-link (NO auth — single-use token):
  GET    /engagement/surveys/respond/{token}
  POST   /engagement/surveys/respond/{token}

Staff:
  POST   /engagement/surveys
  PATCH  /engagement/surveys/{id}
  POST   /engagement/surveys/{id}/publish
  POST   /engagement/surveys/{id}/questions
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.logging import get_logger
from ...models.engagement import (Survey, SurveyOutcome, SurveyPlacement,
                                  SurveyQuestion, SurveyResponse,
                                  SurveyResponseStatus, UserDemographics)
from ...models.learning_platform_enhanced import Badge, UserBadge
from ...models.user import User
from ...schemas.engagement import (BadgeView, PendingSurvey,
                                   SurveyCreate, SurveyListItem,
                                   SurveyOutcomePublic, SurveyQuestionCreate,
                                   SurveyQuestionResponse,
                                   SurveyResponseResult,
                                   SurveyResponseSubmit, SurveyResponse_,
                                   SurveyUpdate, UserBadgeView,
                                   UserDemographicsResponse,
                                   UserDemographicsUpdate)
from ...services.engagement.branching import (evaluate_response,
                                              score_scenario_answer)
from ...services.engagement.dispatcher import apply_actions
from ...services.engagement.eligibility import (get_pending_response,
                                                list_pending_for_user)
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/engagement", tags=["engagement"])


# ============ helpers ============

async def _load_survey(db: AsyncSession, survey_id: int) -> Survey:
    stmt = (
        select(Survey)
        .options(selectinload(Survey.questions))
        .where(Survey.id == survey_id, Survey.deleted_at.is_(None))
    )
    survey = (await db.execute(stmt)).scalar_one_or_none()
    if survey is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


def _answers_to_jsonb(answers) -> list:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"question_id": a.question_id, "value": a.value, "answered_at": now}
        for a in answers
    ]


async def _process_submission(
    db: AsyncSession,
    survey: Survey,
    response: SurveyResponse,
    submission: SurveyResponseSubmit,
) -> SurveyResponseResult:
    answers_by_qid = {a.question_id: a.value for a in submission.answers}
    rules_by_qid = {q.id: q.branching_rules for q in survey.questions}

    actions = evaluate_response(answers_by_qid, rules_by_qid)

    # Score scenario questions (Bias Challenge): count flags identified.
    total_score: Optional[int] = None
    for q in survey.questions:
        if q.question_type == "scenario" and q.options:
            expected = q.options.get("expected_flags") if isinstance(q.options, dict) else None
            if isinstance(expected, list):
                total_score = (total_score or 0) + score_scenario_answer(
                    answers_by_qid.get(q.id), expected
                )

    # Demographic capture: write/update UserDemographics from any flagged
    # questions. Only if response is owned by a user (not anonymous).
    if response.user_id is not None:
        demo_updates = {}
        for q in survey.questions:
            if not q.is_demographic:
                continue
            value = answers_by_qid.get(q.id)
            if value is None:
                continue
            if q.options and isinstance(q.options, dict):
                field = q.options.get("demographic_field")
                if field in {"primary_language", "is_native_english",
                             "age_range", "underserved_self_id", "zip_code"}:
                    demo_updates[field] = value
        if demo_updates:
            await _upsert_demographics(db, response, demo_updates)

    response.answers = _answers_to_jsonb(submission.answers)
    if response.started_at is None:
        response.started_at = datetime.now(timezone.utc)
    response.completed_at = datetime.now(timezone.utc)
    response.status = SurveyResponseStatus.COMPLETED.value
    response.score = total_score
    # Magic-link single-use: clear token on successful submission.
    response.delivery_token = None
    response.delivery_token_expires_at = None

    # Need response.id before writing outcomes; flush to acquire PK.
    await db.flush()

    outcomes = await apply_actions(db, response, actions)
    await db.flush()

    blocked = bool(survey.blocks_progression and
                   total_score is not None and total_score == 0)

    return SurveyResponseResult(
        response_id=response.id,
        status=SurveyResponseStatus(response.status),
        score=response.score,
        derived_track=response.derived_track,
        blocked=blocked,
        outcomes=[
            SurveyOutcomePublic.model_validate(o, from_attributes=True)
            for o in outcomes
        ],
    )


async def _upsert_demographics(
    db: AsyncSession,
    response: SurveyResponse,
    updates: dict,
) -> None:
    existing = (await db.execute(
        select(UserDemographics).where(
            UserDemographics.user_id == response.user_id
        )
    )).scalar_one_or_none()
    if existing is None:
        db.add(UserDemographics(
            user_id=response.user_id,
            source_response_id=response.id,
            **updates,
        ))
        return
    for k, v in updates.items():
        setattr(existing, k, v)


# ============ user endpoints ============

@router.get("/me/pending", response_model=List[PendingSurvey])
async def list_my_pending_surveys(
    course_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    surveys = await list_pending_for_user(db, current_user.id, course_id)
    out: List[PendingSurvey] = []
    for s in surveys:
        # If a pending response with a delivery_token exists, expose the token
        # so the client can resume via the magic-link route.
        token = None
        existing = await get_pending_response(db, current_user.id, s.id)
        if existing is not None:
            token = existing.delivery_token
        out.append(PendingSurvey(
            survey_id=s.id,
            title=s.title,
            placement=s.placement,
            course_id=s.course_id,
            estimated_minutes=s.estimated_minutes,
            consent_copy=s.consent_copy,
            delivery_token=token,
        ))
    return out


@router.get("/surveys/{survey_id}", response_model=SurveyResponse_)
async def get_survey(
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    survey = await _load_survey(db, survey_id)
    if not survey.is_published:
        raise HTTPException(status_code=404, detail="Survey not published")
    return survey


@router.post(
    "/surveys/{survey_id}/responses", response_model=SurveyResponseResult
)
async def submit_response(
    survey_id: int,
    submission: SurveyResponseSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    survey = await _load_survey(db, survey_id)
    if not survey.is_published:
        raise HTTPException(status_code=404, detail="Survey not published")

    # Reuse a pending response if one exists (e.g. longitudinal pre-create);
    # otherwise create a fresh one. The partial unique index on
    # (user_id, survey_id) prevents duplicates.
    response = await get_pending_response(db, current_user.id, survey_id)
    if response is None:
        # Was there already a completed response? Reject (single-shot).
        existing = (await db.execute(
            select(SurveyResponse.id).where(
                SurveyResponse.user_id == current_user.id,
                SurveyResponse.survey_id == survey_id,
            )
        )).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Already submitted a response for this survey",
            )
        response = SurveyResponse(
            user_id=None if survey.is_anonymous else current_user.id,
            survey_id=survey_id,
            course_id=survey.course_id,
            status=SurveyResponseStatus.IN_PROGRESS.value,
        )
        db.add(response)
        await db.flush()

    return await _process_submission(db, survey, response, submission)


@router.post("/me/demographics", response_model=UserDemographicsResponse)
async def upsert_my_demographics(
    payload: UserDemographicsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (await db.execute(
        select(UserDemographics).where(
            UserDemographics.user_id == current_user.id
        )
    )).scalar_one_or_none()
    updates = payload.model_dump(exclude_none=True)
    if existing is None:
        existing = UserDemographics(user_id=current_user.id, **updates)
        db.add(existing)
    else:
        for k, v in updates.items():
            setattr(existing, k, v)
    await db.flush()
    return existing


@router.get("/me/badges", response_model=List[UserBadgeView])
async def list_my_badges(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(UserBadge)
        .options(selectinload(UserBadge.badge))
        .where(UserBadge.user_id == current_user.id)
        .order_by(UserBadge.earned_at.desc())
    )
    return (await db.execute(stmt)).scalars().all()


# ============ magic-link endpoints (no auth) ============

@router.get("/surveys/respond/{token}", response_model=SurveyResponse_)
async def get_survey_via_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Load a survey for a longitudinal magic-link recipient. No auth.

    Token validation: must exist, must not be expired. We don't reveal
    whether the survey is published — the scheduler only mints tokens for
    published surveys.
    """
    response = await _resolve_token(db, token)
    survey = await _load_survey(db, response.survey_id)
    return survey


@router.post(
    "/surveys/respond/{token}", response_model=SurveyResponseResult
)
async def submit_via_token(  # noqa: role-check -- token-gated survey response
    token: str,
    submission: SurveyResponseSubmit,
    db: AsyncSession = Depends(get_db),
):
    response = await _resolve_token(db, token)
    survey = await _load_survey(db, response.survey_id)
    return await _process_submission(db, survey, response, submission)


async def _resolve_token(db: AsyncSession, token: str) -> SurveyResponse:
    if not token or len(token) > 64:
        raise HTTPException(status_code=404, detail="Invalid link")
    response = (await db.execute(
        select(SurveyResponse).where(SurveyResponse.delivery_token == token)
    )).scalar_one_or_none()
    if response is None:
        raise HTTPException(status_code=404, detail="Invalid or used link")
    expires = response.delivery_token_expires_at
    if expires and expires < datetime.now(timezone.utc):
        response.status = SurveyResponseStatus.EXPIRED.value
        response.delivery_token = None
        await db.flush()
        raise HTTPException(status_code=410, detail="Survey link expired")
    if response.status not in (
        SurveyResponseStatus.PENDING.value,
        SurveyResponseStatus.IN_PROGRESS.value,
    ):
        raise HTTPException(status_code=409, detail="Already submitted")
    return response


# ============ staff endpoints ============

@router.get("/surveys", response_model=List[SurveyListItem])
async def list_surveys(
    placement: Optional[SurveyPlacement] = None,
    course_id: Optional[int] = None,
    include_unpublished: bool = False,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
):
    stmt = select(Survey).where(Survey.deleted_at.is_(None))
    if placement is not None:
        stmt = stmt.where(Survey.placement == placement.value)
    if course_id is not None:
        stmt = stmt.where(Survey.course_id == course_id)
    if not include_unpublished:
        stmt = stmt.where(Survey.is_published.is_(True))
    rows = (await db.execute(stmt.order_by(Survey.id.desc()))).scalars().all()
    return rows


@router.post("/surveys", response_model=SurveyResponse_, status_code=201)
async def create_survey(
    payload: SurveyCreate,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(require_staff),
):
    survey = Survey(
        **payload.model_dump(exclude={"questions"}, exclude_unset=False)
    )
    db.add(survey)
    await db.flush()
    for q_payload in payload.questions:
        db.add(SurveyQuestion(survey_id=survey.id, **q_payload.model_dump()))
    await db.flush()
    await db.refresh(survey, attribute_names=["questions"])
    logger.info(
        "engagement: survey created id=%s by user_id=%s", survey.id, staff.id
    )
    return survey


@router.patch("/surveys/{survey_id}", response_model=SurveyResponse_)
async def update_survey(
    survey_id: int,
    payload: SurveyUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
):
    survey = await _load_survey(db, survey_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(survey, k, v)
    await db.flush()
    return survey


@router.post("/surveys/{survey_id}/publish", response_model=SurveyResponse_)
async def publish_survey(
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(require_staff),
):
    survey = await _load_survey(db, survey_id)
    if not survey.questions:
        raise HTTPException(
            status_code=400,
            detail="Cannot publish a survey with no questions",
        )
    survey.is_published = True
    await db.flush()
    logger.info(
        "engagement: survey published id=%s by user_id=%s",
        survey.id, staff.id,
    )
    return survey


@router.post(
    "/surveys/{survey_id}/questions",
    response_model=SurveyQuestionResponse,
    status_code=201,
)
async def add_question(
    survey_id: int,
    payload: SurveyQuestionCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
):
    survey = await _load_survey(db, survey_id)
    question = SurveyQuestion(survey_id=survey.id, **payload.model_dump())
    db.add(question)
    await db.flush()
    return question
