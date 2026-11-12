# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Onboarding API Endpoints

Provides:
- GET  /patrons/me/onboarding-status   - Get current onboarding progress
- PATCH /patrons/me/preferences        - Save reading preferences (Step 2)
- PATCH /patrons/me/home-branch        - Set default branch (Step 3)
- POST /patrons/me/onboarding/step     - Mark a step completed
- POST /patrons/me/onboarding/skip     - Skip onboarding
- POST /patrons/me/onboarding/reset    - Reset onboarding (redo setup)
- POST /patrons/me/onboarding/analytics - Log analytics event
- GET  /admin/onboarding/analytics     - Admin analytics summary
"""
import json
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sql_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.helpers import get_current_user
from .dependencies import require_admin
from ...core.database import get_db
from ...models.patron_onboarding import (
    OnboardingAnalyticsEvent,
    PatronOnboardingProgress,
    ReadingGoal,
)
from ...models.user import User
from ...schemas.patron_onboarding import (
    OnboardingAnalyticsEventCreate,
    OnboardingAnalyticsSummary,
    OnboardingSkipRequest,
    OnboardingStepUpdate,
    PatronHomeBranchUpdate,
    PatronOnboardingStatusResponse,
    PatronPreferencesUpdate,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/patrons/me", tags=["patron-onboarding"])


async def get_or_create_progress(
    patron_id: int, db: AsyncSession
) -> PatronOnboardingProgress:
    result = await db.execute(
        select(PatronOnboardingProgress).where(
            PatronOnboardingProgress.patron_id == patron_id
        )
    )
    progress = result.scalar_one_or_none()
    if progress:
        return progress

    try:
        async with db.begin_nested():
            progress = PatronOnboardingProgress(patron_id=patron_id)
            db.add(progress)
            await db.flush()
        return progress
    except IntegrityError:
        result = await db.execute(
            select(PatronOnboardingProgress).where(
                PatronOnboardingProgress.patron_id == patron_id
            )
        )
        return result.scalar_one()


async def _build_status_response(
    user: User, progress: PatronOnboardingProgress, db: AsyncSession
) -> PatronOnboardingStatusResponse:
    genres = None
    formats = None
    if progress.preferred_genres:
        try:
            genres = json.loads(progress.preferred_genres)
        except (json.JSONDecodeError, TypeError):
            genres = []
    if progress.preferred_formats:
        try:
            formats = json.loads(progress.preferred_formats)
        except (json.JSONDecodeError, TypeError):
            formats = []

    branch_name = None
    if user.home_branch_id:
        from ...models.multi_branch import Branch
        result = await db.execute(
            select(Branch.name).where(Branch.id == user.home_branch_id)
        )
        branch_name = result.scalar_one_or_none()

    return PatronOnboardingStatusResponse(
        patron_id=user.id,
        current_step=progress.current_step,
        step_welcome_completed=progress.step_welcome_completed,
        step_preferences_completed=progress.step_preferences_completed,
        step_branch_completed=progress.step_branch_completed,
        step_tour_completed=progress.step_tour_completed,
        step_complete_completed=progress.step_complete_completed,
        preferred_genres=genres,
        preferred_formats=formats,
        reading_goal=str(progress.reading_goal) if progress.reading_goal else None,
        skipped=progress.skipped,
        completed_at=progress.completed_at,
        started_at=progress.started_at,
        home_branch_id=user.home_branch_id,
        home_branch_name=branch_name,
    )


@router.get("/onboarding-status", response_model=PatronOnboardingStatusResponse)
async def get_onboarding_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current patron's onboarding status and progress."""
    progress = await get_or_create_progress(user.id, db)
    return await _build_status_response(user, progress, db)


@router.patch("/preferences", response_model=PatronOnboardingStatusResponse)
async def update_preferences(
    data: PatronPreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save patron reading preferences (genres, formats, reading goal)."""
    progress = await get_or_create_progress(user.id, db)
    progress.preferred_genres = json.dumps(data.preferred_genres)
    progress.preferred_formats = json.dumps(data.preferred_formats)
    progress.reading_goal = ReadingGoal(data.reading_goal)
    progress.step_preferences_completed = True

    if progress.current_step < 3:
        progress.current_step = 3

    # Log analytics
    db.add(OnboardingAnalyticsEvent(
        patron_id=user.id,
        event_type="step_completed",
        step_number=2,
        step_name="preferences",
        event_metadata=json.dumps({
            "genres_count": len(data.preferred_genres),
            "formats_count": len(data.preferred_formats),
            "reading_goal": data.reading_goal,
        }),
    ))

    await db.flush()
    return await _build_status_response(user, progress, db)


@router.patch("/home-branch")
async def update_home_branch(
    data: PatronHomeBranchUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set patron's default home branch for holds pickup."""
    from ...models.multi_branch import Branch

    # Verify branch exists
    result = await db.execute(
        select(Branch).where(Branch.id == data.branch_id)
    )
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    user.home_branch_id = data.branch_id
    progress = await get_or_create_progress(user.id, db)
    progress.step_branch_completed = True

    if progress.current_step < 4:
        progress.current_step = 4

    db.add(OnboardingAnalyticsEvent(
        patron_id=user.id,
        event_type="step_completed",
        step_number=3,
        step_name="branch",
        event_metadata=json.dumps({"branch_id": data.branch_id, "branch_name": branch.name}),
    ))

    await db.flush()
    return {"status": "ok", "message": f"Home branch set to {branch.name}"}


@router.post("/onboarding/step")
async def complete_step(
    data: OnboardingStepUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an onboarding step as completed."""
    progress = await get_or_create_progress(user.id, db)

    step_map = {
        1: ("step_welcome_completed", "welcome"),
        2: ("step_preferences_completed", "preferences"),
        3: ("step_branch_completed", "branch"),
        4: ("step_tour_completed", "tour"),
        5: ("step_complete_completed", "complete"),
    }

    attr, step_name = step_map[data.step]
    setattr(progress, attr, True)

    if progress.current_step <= data.step:
        progress.current_step = min(data.step + 1, 5)

    # If completing step 5, mark the whole onboarding as done
    if data.step == 5:
        progress.completed_at = datetime.now(timezone.utc)
        user.onboarding_completed_at = datetime.now(timezone.utc)

    db.add(OnboardingAnalyticsEvent(
        patron_id=user.id,
        event_type="step_completed",
        step_number=data.step,
        step_name=step_name,
    ))

    await db.flush()
    return {"status": "ok", "step": data.step, "completed": True}


@router.post("/onboarding/skip", response_model=PatronOnboardingStatusResponse)
async def skip_onboarding(
    data: OnboardingSkipRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Skip onboarding. Progress is saved up to the current step."""
    progress = await get_or_create_progress(user.id, db)
    progress.skipped = True
    progress.skipped_at = datetime.now(timezone.utc)
    if data.current_step:
        progress.current_step = data.current_step

    user.onboarding_completed_at = datetime.now(timezone.utc)
    user.onboarding_skipped = True

    db.add(OnboardingAnalyticsEvent(
        patron_id=user.id,
        event_type="flow_skipped",
        step_number=data.current_step,
        step_name="skip",
    ))

    await db.flush()
    return await _build_status_response(user, progress, db)


@router.post("/onboarding/reset")
async def reset_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset onboarding so patron can redo the setup wizard."""
    progress = await get_or_create_progress(user.id, db)
    progress.step_welcome_completed = False
    progress.step_preferences_completed = False
    progress.step_branch_completed = False
    progress.step_tour_completed = False
    progress.step_complete_completed = False
    progress.current_step = 1
    progress.skipped = False
    progress.skipped_at = None
    progress.completed_at = None

    user.onboarding_completed_at = None
    user.onboarding_skipped = False

    await db.flush()
    return {"status": "ok", "message": "Onboarding reset"}


@router.post("/onboarding/analytics")
async def log_analytics_event(
    data: OnboardingAnalyticsEventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log an analytics event for the onboarding flow."""
    event = OnboardingAnalyticsEvent(
        patron_id=user.id,
        event_type=data.event_type,
        step_number=data.step_number,
        step_name=data.step_name,
        event_metadata=json.dumps(data.metadata) if data.metadata else None,
    )
    db.add(event)
    await db.flush()
    return {"status": "ok"}


# Admin analytics router (separate prefix)
analytics_router = APIRouter(prefix="/admin/onboarding", tags=["admin-onboarding-analytics"])


@analytics_router.get("/analytics", response_model=OnboardingAnalyticsSummary)
async def get_onboarding_analytics(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Total started
    total_started = await db.scalar(
        select(sql_func.count(PatronOnboardingProgress.id))
    ) or 0

    # Total completed
    total_completed = await db.scalar(
        select(sql_func.count(PatronOnboardingProgress.id)).where(
            PatronOnboardingProgress.completed_at.isnot(None)
        )
    ) or 0

    # Total skipped
    total_skipped = await db.scalar(
        select(sql_func.count(PatronOnboardingProgress.id)).where(
            PatronOnboardingProgress.skipped.is_(True)
        )
    ) or 0

    completion_rate = (total_completed / total_started * 100) if total_started > 0 else 0.0

    # Step completion rates
    step_fields = {
        "welcome": PatronOnboardingProgress.step_welcome_completed,
        "preferences": PatronOnboardingProgress.step_preferences_completed,
        "branch": PatronOnboardingProgress.step_branch_completed,
        "tour": PatronOnboardingProgress.step_tour_completed,
        "complete": PatronOnboardingProgress.step_complete_completed,
    }

    step_rates = {}
    drop_off = {}
    prev_count = total_started
    for step_name, field in step_fields.items():
        count = await db.scalar(
            select(sql_func.count(PatronOnboardingProgress.id)).where(field.is_(True))
        ) or 0
        step_rates[step_name] = round((count / total_started * 100) if total_started > 0 else 0, 1)
        drop_off[step_name] = max(0, prev_count - count)
        prev_count = count

    return OnboardingAnalyticsSummary(
        total_started=total_started,
        total_completed=total_completed,
        total_skipped=total_skipped,
        completion_rate=round(completion_rate, 1),
        step_completion_rates=step_rates,
        drop_off_by_step=drop_off,
    )
