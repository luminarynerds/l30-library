# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Learning Path cohort endpoints (V1).

Endpoints:
  - POST /learning-paths/{id}/cohort/join       — opt in
  - GET  /learning-paths/{id}/cohort/members    — status + (if joined) member list
  - POST /learning-paths/{id}/cohort/leave      — soft delete own membership
  - GET  /learning-paths/{id}/cohort/discussion — list posts (cohort members only)
  - POST /learning-paths/{id}/cohort/discussion — post to shared wall (cohort members only)

Authorization:
  - join/leave: any authenticated user
  - members (status + count + listing): authenticated user; non-members
    receive count only with an empty members list (no membership-state
    disclosure required, but listing is cohort-only per privacy framing)
  - discussion read/write: cohort members only (403 otherwise) — opt-in
    is the gate; non-members cannot see or post

V1 boundaries respected: no facilitator UI, no moderation workflows
beyond soft-delete, no matchmaking, no email notifications.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.learning_path import LearningPath
from ...models.learning_path_cohort import (
    LearningPathCohortMember,
    LearningPathDiscussionPost,
)
from ...models.user import User
from ...schemas.learning_path_cohort import (
    CohortDiscussionPostCreate,
    CohortDiscussionPostResponse,
    CohortMemberPublic,
    CohortStatusResponse,
)
from .auth import get_current_user

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


async def _get_path_or_404(db: AsyncSession, path_id: int) -> LearningPath:
    result = await db.execute(
        select(LearningPath).where(LearningPath.id == path_id)
    )
    path = result.scalars().first()
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found",
        )
    return path


async def _active_membership(
    db: AsyncSession, path_id: int, user_id: int
) -> LearningPathCohortMember | None:
    result = await db.execute(
        select(LearningPathCohortMember).where(
            LearningPathCohortMember.learning_path_id == path_id,
            LearningPathCohortMember.user_id == user_id,
            LearningPathCohortMember.deleted_at.is_(None),
        )
    )
    return result.scalars().first()


async def _active_member_count(db: AsyncSession, path_id: int) -> int:
    result = await db.execute(
        select(func.count(LearningPathCohortMember.id)).where(
            LearningPathCohortMember.learning_path_id == path_id,
            LearningPathCohortMember.deleted_at.is_(None),
        )
    )
    return int(result.scalar_one() or 0)


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


@router.post(
    "/{path_id}/cohort/join",
    response_model=CohortStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def join_cohort(
    path_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohortStatusResponse:
    """Opt the current user into the path's cohort.

    Idempotent: joining when already an active member is a no-op and
    returns the current status.
    """
    await _get_path_or_404(db, path_id)

    existing = await _active_membership(db, path_id, current_user.id)
    if existing is None:
        # Was there a previous (soft-deleted) membership we can revive?
        result = await db.execute(
            select(LearningPathCohortMember).where(
                LearningPathCohortMember.learning_path_id == path_id,
                LearningPathCohortMember.user_id == current_user.id,
                LearningPathCohortMember.deleted_at.is_not(None),
            )
        )
        prior = result.scalars().first()
        if prior is not None:
            prior.deleted_at = None
            prior.opted_in_at = func.now()
            db.add(prior)
        else:
            db.add(
                LearningPathCohortMember(
                    learning_path_id=path_id,
                    user_id=current_user.id,
                )
            )
        await db.commit()

    return await _build_status_response(db, path_id, current_user.id)


@router.post(
    "/{path_id}/cohort/leave",
    response_model=CohortStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def leave_cohort(
    path_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohortStatusResponse:
    """Soft-delete the current user's cohort membership.

    Idempotent: leaving when not an active member is a no-op.
    """
    await _get_path_or_404(db, path_id)
    membership = await _active_membership(db, path_id, current_user.id)
    if membership is not None:
        membership.deleted_at = func.now()
        db.add(membership)
        await db.commit()

    return await _build_status_response(db, path_id, current_user.id)


@router.get(
    "/{path_id}/cohort/members",
    response_model=CohortStatusResponse,
)
async def list_cohort_members(
    path_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohortStatusResponse:
    """Return cohort status for the caller.

    - ``member_count`` is always returned (helps the "join" CTA).
    - ``members`` (first name + opted-in date) is populated only when
      the caller is an active cohort member — privacy-by-default.
    """
    await _get_path_or_404(db, path_id)
    return await _build_status_response(db, path_id, current_user.id)


async def _build_status_response(
    db: AsyncSession, path_id: int, user_id: int
) -> CohortStatusResponse:
    is_member = (await _active_membership(db, path_id, user_id)) is not None
    member_count = await _active_member_count(db, path_id)
    members: List[CohortMemberPublic] = []
    if is_member:
        result = await db.execute(
            select(
                LearningPathCohortMember.user_id,
                User.first_name,
                LearningPathCohortMember.opted_in_at,
            )
            .join(User, User.id == LearningPathCohortMember.user_id)
            .where(
                LearningPathCohortMember.learning_path_id == path_id,
                LearningPathCohortMember.deleted_at.is_(None),
            )
            .order_by(LearningPathCohortMember.opted_in_at.asc())
        )
        members = [
            CohortMemberPublic(
                user_id=row.user_id,
                first_name=row.first_name or "",
                opted_in_at=row.opted_in_at,
            )
            for row in result.all()
        ]
    return CohortStatusResponse(
        is_member=is_member,
        member_count=member_count,
        members=members,
    )


# ---------------------------------------------------------------------------
# Shared discussion thread (one flat wall per path)
# ---------------------------------------------------------------------------


@router.get(
    "/{path_id}/cohort/discussion",
    response_model=List[CohortDiscussionPostResponse],
)
async def list_discussion_posts(
    path_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CohortDiscussionPostResponse]:
    """List posts on the path's shared cohort wall.

    Cohort-members-only: non-members receive 403. This matches the
    "opt-in to participate" framing in the feature spec.
    """
    await _get_path_or_404(db, path_id)
    if (await _active_membership(db, path_id, current_user.id)) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Join the cohort to view the discussion",
        )

    result = await db.execute(
        select(LearningPathDiscussionPost)
        .where(
            LearningPathDiscussionPost.learning_path_id == path_id,
            LearningPathDiscussionPost.deleted_at.is_(None),
        )
        .order_by(LearningPathDiscussionPost.created_at.asc())
    )
    return [
        CohortDiscussionPostResponse.model_validate(p)
        for p in result.scalars().all()
    ]


@router.post(
    "/{path_id}/cohort/discussion",
    response_model=CohortDiscussionPostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_discussion_post(
    body: CohortDiscussionPostCreate,
    path_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohortDiscussionPostResponse:
    """Post to the path's shared cohort wall.

    Cohort-members-only.
    """
    await _get_path_or_404(db, path_id)
    if (await _active_membership(db, path_id, current_user.id)) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Join the cohort to post to the discussion",
        )

    display = (current_user.first_name or "").strip() or "Member"
    post = LearningPathDiscussionPost(
        learning_path_id=path_id,
        user_id=current_user.id,
        author_display_name=display,
        body=body.body,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return CohortDiscussionPostResponse.model_validate(post)
