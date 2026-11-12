# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Family challenge and take-home bundle routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ....core.database import get_db
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.outreach import OutreachPartner
from ....models.reading import (
    BundleDistribution,
    FamilyChallengeRegistration,
    FamilyReadingChallenge,
    ReadingProgram,
    TakeHomeReadingBundle,
)
from ....models.user import User
from ....schemas.reading import (
    FamilyChallengeRegistrationCreate,
    FamilyChallengeRegistrationResponse,
    FamilyReadingChallengeCreate,
    FamilyReadingChallengeResponse,
    TakeHomeReadingBundleCreate,
    TakeHomeReadingBundleResponse,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access
from ..feature_guards import require_for_teachers_enabled
from ._notifications import _notify_librarian_of_teacher_action
from ._shared import (
    _strip_patron_identifiers,
    assert_teacher_access_to_school,
    require_teacher_of_school,
)

challenges_router = APIRouter()


@challenges_router.post(
    "/family-challenges",
    response_model=FamilyReadingChallengeResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_family_reading_challenge(
    request: Request,
    challenge_data: FamilyReadingChallengeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a family reading challenge. Staff only."""
    check_staff_access(current_user)

    # Verify program exists
    program_result = await db.execute(
        select(ReadingProgram).where(ReadingProgram.id == challenge_data.program_id)
    )
    if not program_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading program not found"
        )

    challenge = FamilyReadingChallenge(
        program_id=challenge_data.program_id,
        name=challenge_data.name,
        description=challenge_data.description,
        challenge_type=challenge_data.challenge_type,
        goal_type=challenge_data.goal_type,
        goal_value=challenge_data.goal_value,
        start_date=challenge_data.start_date,
        end_date=challenge_data.end_date,
        parent_reward_description=challenge_data.parent_reward_description,
        child_reward_description=challenge_data.child_reward_description,
    )

    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)

    return challenge


@challenges_router.get(
    "/family-challenges/by-id/{challenge_id}", response_model=FamilyReadingChallengeResponse
)
@limiter.limit("120/minute")
async def get_family_challenge(
    request: Request,
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get family reading challenge details by challenge id.

    Note: previously mounted at ``/family-challenges/{challenge_id}``. Renamed
    to ``/family-challenges/by-id/{challenge_id}`` to disambiguate from
    ``/family-challenges/{school_id}`` (list challenges for a school). No
    frontend caller used the old path at the time of the rename.
    """
    result = await db.execute(
        select(FamilyReadingChallenge)
        .options(selectinload(FamilyReadingChallenge.program))
        .where(FamilyReadingChallenge.id == challenge_id)
    )
    challenge = result.scalar_one_or_none()
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    school_id = getattr(challenge.program, "partner_id", None) if challenge.program else None
    if school_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge has no associated school",
        )
    assert_teacher_access_to_school(current_user, school_id)

    return challenge


def _serialize_challenge_for_school(
    c: FamilyReadingChallenge, participant_count: int, school_id: int
) -> dict:
    goal_type = (c.goal_type or "").lower()
    goal_minutes = c.goal_value if goal_type == "minutes" else 0
    goal_books = c.goal_value if goal_type == "books" else 0
    prizes = c.parent_reward_description or c.child_reward_description or None
    return {
        "id": str(c.id),
        "title": c.name,
        "description": c.description or "",
        "startDate": c.start_date.isoformat() if c.start_date else "",
        "endDate": c.end_date.isoformat() if c.end_date else "",
        "goalMinutes": goal_minutes,
        "goalBooks": goal_books,
        "targetAgeGroup": c.challenge_type or "",
        "theme": c.challenge_type or "",
        "prizes": prizes,
        "participantCount": participant_count,
        "schoolId": str(school_id),
    }


@challenges_router.get("/family-challenges/{school_id}/registrations", response_model=dict)
@limiter.limit("120/minute")
async def list_family_challenge_registrations_for_school(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's family-challenge registrations for a given school.

    Scoped to challenges whose underlying ReadingProgram belongs to this school
    (partner_id == school_id) and to rows where the current user is the parent.
    """
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    query = (
        select(FamilyChallengeRegistration)
        .options(selectinload(FamilyChallengeRegistration.challenge))
        .join(
            FamilyReadingChallenge,
            FamilyChallengeRegistration.challenge_id == FamilyReadingChallenge.id,
        )
        .join(ReadingProgram, FamilyReadingChallenge.program_id == ReadingProgram.id)
        .where(
            and_(
                ReadingProgram.partner_id == school_id,
                FamilyChallengeRegistration.parent_user_id == current_user.id,
            )
        )
        .order_by(FamilyChallengeRegistration.registered_at.desc())
    )
    result = await db.execute(query)
    regs = result.scalars().all()

    today = datetime.now(timezone.utc).date()
    registrations = []
    for r in regs:
        c = r.challenge
        goal_type = (c.goal_type or "").lower() if c else ""
        goal_value = c.goal_value if c else 0
        goal_minutes = goal_value if goal_type == "minutes" else 0
        goal_books = goal_value if goal_type == "books" else 0
        combined = r.combined_progress or ((r.parent_progress or 0) + (r.child_progress or 0))
        minutes_read = combined if goal_type == "minutes" else 0
        books_read = combined if goal_type == "books" else 0
        progress_pct = 0.0
        if goal_value > 0:
            progress_pct = min(100.0, (combined / goal_value) * 100.0)
        if progress_pct >= 100.0:
            reg_status = "completed"
        elif c and c.end_date and today > c.end_date:
            reg_status = "abandoned"
        else:
            reg_status = "active"
        registrations.append(
            {
                "id": str(r.id),
                "challengeId": str(r.challenge_id),
                "challengeTitle": c.name if c else "",
                "familyName": "",
                "studentAge": 0,
                "registrationDate": r.registered_at.isoformat() if r.registered_at else "",
                "minutesRead": minutes_read,
                "booksRead": books_read,
                "goalMinutes": goal_minutes,
                "goalBooks": goal_books,
                "progressPercentage": progress_pct,
                "status": reg_status,
            }
        )

    return {"registrations": registrations}


@challenges_router.get("/family-challenges/{school_id}", response_model=dict)
@limiter.limit("120/minute")
async def list_family_challenges_for_school(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List family reading challenges for a school.

    A FamilyReadingChallenge is linked to a school via its ReadingProgram
    (program.partner_id == school_id), mirroring the take-home-bundles and
    training-modules patterns.
    """
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    query = (
        select(FamilyReadingChallenge)
        .join(ReadingProgram, FamilyReadingChallenge.program_id == ReadingProgram.id)
        .where(
            and_(
                ReadingProgram.partner_id == school_id,
                FamilyReadingChallenge.is_active == True,
            )
        )
        .order_by(FamilyReadingChallenge.start_date.desc())
    )
    result = await db.execute(query)
    challenges = result.scalars().all()

    if not challenges:
        return {"challenges": []}

    challenge_ids = [c.id for c in challenges]
    count_query = (
        select(
            FamilyChallengeRegistration.challenge_id,
            func.count(FamilyChallengeRegistration.id),
        )
        .where(FamilyChallengeRegistration.challenge_id.in_(challenge_ids))
        .group_by(FamilyChallengeRegistration.challenge_id)
    )
    count_result = await db.execute(count_query)
    counts = {cid: cnt for cid, cnt in count_result.all()}

    return {
        "challenges": [
            _serialize_challenge_for_school(c, counts.get(c.id, 0), school_id) for c in challenges
        ]
    }


@challenges_router.post(
    "/family-challenges/{challenge_id}/register",
    response_model=FamilyChallengeRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def register_family_in_challenge(
    request: Request,
    challenge_id: int,
    registration_data: FamilyChallengeRegistrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a family in a reading challenge.

    Accepts two shapes (see FamilyChallengeRegistrationCreate):

    - Page shape: ``{schoolId, familyName, studentAge}`` -- the registering
      user (teacher/staff) is recorded as ``parent_user_id``.  ``schoolId``
      must match the challenge's program partner_id so a teacher cannot
      register a family against another school's challenge.
    - Linked-account shape: ``{parent_user_id, child_user_id, parent_goal?,
      child_goal?}`` -- used when both parent and child have user accounts.
    """
    # Fetch challenge with its program so we can scope-check schoolId.
    challenge_result = await db.execute(
        select(FamilyReadingChallenge)
        .options(selectinload(FamilyReadingChallenge.program))
        .where(FamilyReadingChallenge.id == challenge_id)
    )
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    page_shape = (
        registration_data.schoolId is not None
        or registration_data.familyName is not None
        or registration_data.studentAge is not None
    )

    if page_shape:
        # Page-shape registration.  schoolId must match the challenge's
        # program partner_id; otherwise teachers could register families
        # against challenges that don't belong to their school.
        program_partner_id = (
            getattr(challenge.program, "partner_id", None) if challenge.program else None
        )
        if registration_data.schoolId is not None and program_partner_id is not None:
            if registration_data.schoolId != program_partner_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Challenge does not belong to the specified school",
                )

        registration = FamilyChallengeRegistration(
            challenge_id=challenge_id,
            parent_user_id=current_user.id,
            child_user_id=None,
            family_name=registration_data.familyName,
            student_age=registration_data.studentAge,
            parent_goal=registration_data.parent_goal,
            child_goal=registration_data.child_goal,
        )
    else:
        # Linked-account shape (legacy).
        if registration_data.parent_user_id is None or registration_data.child_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either page shape (schoolId/familyName/studentAge) or linked-account shape (parent_user_id/child_user_id) is required",
            )
        registration = FamilyChallengeRegistration(
            challenge_id=challenge_id,
            parent_user_id=registration_data.parent_user_id,
            child_user_id=registration_data.child_user_id,
            parent_goal=registration_data.parent_goal,
            child_goal=registration_data.child_goal,
        )

    db.add(registration)
    await db.commit()
    await db.refresh(registration)

    # Librarian notification (best-effort; never 500s the caller).
    program_partner_id = (
        getattr(challenge.program, "partner_id", None) if challenge.program else None
    )
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=program_partner_id,
        action_type="family_challenge_join",
        payload={
            "challenge_id": challenge_id,
            "family_name": registration.family_name,
        },
    )

    return registration


@challenges_router.post(
    "/take-home-bundles",
    response_model=TakeHomeReadingBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_take_home_bundle(
    request: Request,
    bundle_data: TakeHomeReadingBundleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a take-home reading bundle for family engagement. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    school_result = await db.execute(
        select(OutreachPartner).where(OutreachPartner.id == bundle_data.partner_id)
    )
    if not school_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    bundle = TakeHomeReadingBundle(
        partner_id=bundle_data.partner_id,
        name=bundle_data.name,
        description=bundle_data.description,
        bundle_theme=bundle_data.bundle_theme,
        book_count=bundle_data.book_count,
        grade_levels=bundle_data.grade_levels,
        reading_levels=bundle_data.reading_levels,
        copies_available=bundle_data.copies_available,
    )

    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)

    return bundle


@challenges_router.get("/take-home-bundles/{school_id}", response_model=dict)
@limiter.limit("120/minute")
async def list_take_home_bundles(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List take-home reading bundles for a school. Staff only."""

    await get_or_404(db, OutreachPartner, school_id, "School not found")

    query = (
        select(TakeHomeReadingBundle)
        .where(
            and_(
                TakeHomeReadingBundle.partner_id == school_id,
                TakeHomeReadingBundle.is_active == True,
            )
        )
        .order_by(TakeHomeReadingBundle.created_at.desc())
    )

    result = await db.execute(query)
    bundles = result.scalars().all()

    return {
        "bundles": [
            {
                "id": str(b.id),
                "title": b.name,
                "description": b.description or "",
                "themeOrGradeLevel": b.bundle_theme or "",
                "numberOfBooks": b.book_count,
                "readingLevels": b.reading_levels or [],
                "totalCopiesAvailable": max(0, b.copies_available - b.copies_distributed),
                "copiesTomorrow": max(0, b.copies_available - b.copies_distributed),
                "bundles": [],
            }
            for b in bundles
        ]
    }


@challenges_router.get("/take-home-bundles/{school_id}/distributions", response_model=dict)
@limiter.limit("120/minute")
async def list_bundle_distributions(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List bundle distributions for a school. Staff only."""

    await get_or_404(db, OutreachPartner, school_id, "School not found")

    query = (
        select(BundleDistribution)
        .join(TakeHomeReadingBundle)
        .where(TakeHomeReadingBundle.partner_id == school_id)
        .options(selectinload(BundleDistribution.bundle))
        .order_by(BundleDistribution.distributed_at.desc())
    )

    result = await db.execute(query)
    distributions = result.scalars().all()

    # Explicit isolation: strip patron identifiers from distribution records
    return _strip_patron_identifiers(
        {
            "distributions": [
                {
                    "id": str(d.id),
                    "bundleId": str(d.bundle_id),
                    "bundleTitle": d.bundle.name if d.bundle else "",
                    "studentName": d.student_name or "",
                    "className": d.class_name or "",
                    "distributedDate": d.distributed_at.isoformat() if d.distributed_at else "",
                    "returnedDate": d.returned_at.isoformat() if d.returned_at else None,
                    "status": d.status or "distributed",
                    "feedback": d.family_feedback,
                }
                for d in distributions
            ]
        }
    )


class DistributeBundleRequest(BaseModel):
    # Free-text roster labels for the child receiving the bundle. `user_id` is
    # optional: take-home recipients are usually schoolchildren without a
    # patron account. See BundleDistribution model for the child-PII note.
    student_name: str
    class_name: Optional[str] = None
    user_id: Optional[int] = None


@challenges_router.post(
    "/take-home-bundles/{bundle_id}/distribute", status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute")
async def distribute_take_home_bundle(
    request: Request,
    bundle_id: int,
    payload: DistributeBundleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Distribute a take-home bundle to a family. Staff only."""
    check_staff_access(current_user)

    # Verify bundle exists
    bundle = await get_or_404(db, TakeHomeReadingBundle, bundle_id, "Bundle not found")

    if bundle.copies_distributed >= bundle.copies_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No copies available for distribution"
        )

    # Create distribution
    distribution = BundleDistribution(
        bundle_id=bundle_id,
        user_id=payload.user_id,
        student_name=payload.student_name,
        class_name=payload.class_name,
    )

    bundle.copies_distributed += 1
    bundle.last_distributed_date = datetime.now(timezone.utc).date()

    db.add(distribution)
    await db.commit()
    await db.refresh(distribution)

    return {"message": "Bundle distributed successfully", "distribution_id": distribution.id}
