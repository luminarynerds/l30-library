# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Teacher Application API

Self-serve teacher signup, librarian approval. Patron submits a
TeacherApplication; librarian reviews and either approves (sets
users.role=TEACHER + users.school_id) or denies.

Mirrors backend/app/api/v1/card_applications.py.
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.database import get_db
from ...core.email import (
    send_teacher_application_approved,
    send_teacher_application_denied,
    send_teacher_application_received,
)
from ...core.logging import get_logger
from ...models.outreach import OutreachPartner, OutreachPartnerStatus, PartnerType
from ...models.teacher_application import (
    TeacherApplication,
    TeacherApplicationStatus,
)
from ...models.user import User, UserRole, name_or_email_clause
from ...schemas.teacher_application import (
    TeacherApplicationCreate,
    TeacherApplicationListResponse,
    TeacherApplicationResponse,
    TeacherApplicationReview,
    TeacherSchoolOption,
)
from .dependencies import require_authenticated, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/teacher-applications", tags=["teacher-applications"])


def _build_response(
    app: TeacherApplication,
    reviewer: Optional[User] = None,
) -> TeacherApplicationResponse:
    user_email = app.user.email if app.user else None
    user_name = None
    if app.user:
        if app.user.first_name or app.user.last_name:
            user_name = f"{app.user.first_name or ''} {app.user.last_name or ''}".strip()
        else:
            user_name = app.user.email

    school_name = app.school.name if app.school else None

    reviewer_name = None
    if reviewer:
        reviewer_name = reviewer.full_name if hasattr(reviewer, "full_name") else reviewer.email
    elif app.reviewer:
        reviewer_name = (
            app.reviewer.full_name if hasattr(app.reviewer, "full_name") else app.reviewer.email
        )

    return TeacherApplicationResponse(
        id=app.id,
        user_id=app.user_id,
        user_email=user_email,
        user_name=user_name,
        school_id=app.school_id,
        school_name=school_name,
        school_name_freetext=app.school_name_freetext,
        grade_level=app.grade_level,
        subject=app.subject,
        classroom_size=app.classroom_size,
        notes=app.notes,
        status=app.status,
        created_at=app.created_at,
        reviewed_at=app.reviewed_at,
        reviewed_by_id=app.reviewed_by_id,
        reviewed_by_name=reviewer_name,
        review_notes=app.review_notes,
        denial_reason=app.denial_reason,
    )


# ============================================================================
# Patron-facing endpoints
# ============================================================================

@router.get("/schools", response_model=list[TeacherSchoolOption])
async def list_schools(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List active school outreach partners for the application dropdown.

    Authenticated-only. Returns id + name only. No PII, no contacts.
    """
    result = await db.execute(
        select(OutreachPartner.id, OutreachPartner.name)
        .where(
            OutreachPartner.partner_type == PartnerType.SCHOOL.value,
            OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value,
        )
        .order_by(OutreachPartner.name.asc())
    )
    rows = result.all()
    return [TeacherSchoolOption(id=r[0], name=r[1]) for r in rows]


@router.post(
    "",
    response_model=TeacherApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_teacher_application(
    data: TeacherApplicationCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Submit a teacher application.

    - Already-TEACHER users get 409.
    - Users with an existing PENDING application get 409.
    - Users with an APPROVED application get 409 (already teacher pathway).
    - DENIED is fine; user may re-apply.
    """
    if current_user.role == UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a teacher. Contact staff to update your school.",
        )

    # Check for an active (PENDING or APPROVED) application
    existing_result = await db.execute(
        select(TeacherApplication)
        .where(TeacherApplication.user_id == current_user.id)
        .where(
            TeacherApplication.status.in_(
                [TeacherApplicationStatus.pending, TeacherApplicationStatus.approved]
            )
        )
    )
    existing = existing_result.scalars().first()
    if existing is not None:
        if existing.status == TeacherApplicationStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a pending teacher application.",
            )
        # APPROVED case
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an approved teacher application on file.",
        )

    # Validate school_id if provided (must be an active school partner)
    if data.school_id is not None:
        school = await db.get(OutreachPartner, data.school_id)
        if school is None or school.partner_type != PartnerType.SCHOOL.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School not found.",
            )

    application = TeacherApplication(
        user_id=current_user.id,
        school_id=data.school_id,
        school_name_freetext=data.school_name_freetext,
        grade_level=data.grade_level,
        subject=data.subject,
        classroom_size=data.classroom_size,
        notes=data.notes,
        status=TeacherApplicationStatus.pending,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Confirmation email -- failures are non-fatal; row already persisted.
    try:
        await send_teacher_application_received(
            to_email=current_user.email,
            first_name=current_user.first_name or "",
        )
    except Exception as exc:  # noqa: BLE001  # best-effort confirmation email — application already saved
        logger.warning(
            "Failed to send teacher application received email",
            extra={"application_id": application.id, "error": str(exc)},
        )

    # Re-load with relationships for response
    result = await db.execute(
        select(TeacherApplication)
        .options(joinedload(TeacherApplication.user), joinedload(TeacherApplication.school))
        .where(TeacherApplication.id == application.id)
    )
    application = result.scalar_one()
    return _build_response(application)


@router.get("/me", response_model=Optional[TeacherApplicationResponse])
async def get_my_teacher_application(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's most recent teacher application, or null."""
    result = await db.execute(
        select(TeacherApplication)
        .options(
            joinedload(TeacherApplication.user),
            joinedload(TeacherApplication.school),
            joinedload(TeacherApplication.reviewer),
        )
        .where(TeacherApplication.user_id == current_user.id)
        .order_by(TeacherApplication.created_at.desc())
        .limit(1)
    )
    app = result.scalars().first()
    if app is None:
        return None
    return _build_response(app)


# ============================================================================
# Staff endpoints
# ============================================================================

@router.get("/staff", response_model=TeacherApplicationListResponse)
async def staff_list_teacher_applications(
    status_filter: Optional[TeacherApplicationStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None, description="Search by applicant email or name"),
    sort: Optional[Literal["oldest_first", "newest_first"]] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff queue of teacher applications."""
    query = (
        select(TeacherApplication)
        .options(
            joinedload(TeacherApplication.user),
            joinedload(TeacherApplication.school),
            joinedload(TeacherApplication.reviewer),
        )
    )
    count_query = select(func.count(TeacherApplication.id))

    if status_filter:
        query = query.where(TeacherApplication.status == status_filter)
        count_query = count_query.where(TeacherApplication.status == status_filter)

    _search_clause = name_or_email_clause(search) if search else None
    if _search_clause is not None:
        # Names + email encrypted: exact email + name blind index, not substring.
        query = query.join(User, TeacherApplication.user_id == User.id).where(_search_clause)
        count_query = count_query.join(User, TeacherApplication.user_id == User.id).where(_search_clause)

    total = (await db.execute(count_query)).scalar() or 0

    if sort is None:
        effective_sort = "oldest_first" if status_filter == TeacherApplicationStatus.pending else "newest_first"
    else:
        effective_sort = sort
    order_clause = (
        TeacherApplication.created_at.asc()
        if effective_sort == "oldest_first"
        else TeacherApplication.created_at.desc()
    )
    query = query.order_by(order_clause).limit(limit).offset(offset)
    result = await db.execute(query)
    apps = result.unique().scalars().all()

    return TeacherApplicationListResponse(
        applications=[_build_response(a) for a in apps],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/staff/{application_id}", response_model=TeacherApplicationResponse)
async def staff_get_teacher_application(
    application_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeacherApplication)
        .options(
            joinedload(TeacherApplication.user),
            joinedload(TeacherApplication.school),
            joinedload(TeacherApplication.reviewer),
        )
        .where(TeacherApplication.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return _build_response(app)


async def _review(
    application_id: int,
    data: TeacherApplicationReview,
    staff_user: User,
    db: AsyncSession,
) -> TeacherApplicationResponse:
    result = await db.execute(
        select(TeacherApplication)
        .options(joinedload(TeacherApplication.user))
        .where(TeacherApplication.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if app.status in (TeacherApplicationStatus.approved, TeacherApplicationStatus.denied):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application has already been {app.status.value}",
        )

    # Resolve the school_id to assign on approval: prefer the reviewer-supplied
    # value (allows overriding the patron-declared school), else the application's
    # current school_id.
    if data.status == TeacherApplicationStatus.approved:
        effective_school_id = data.school_id if data.school_id is not None else app.school_id
        if effective_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approval requires a school_id (either on the application or in the request body).",
            )
        school = await db.get(OutreachPartner, effective_school_id)
        if school is None or school.partner_type != PartnerType.SCHOOL.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School not found.",
            )
        app.school_id = effective_school_id

        # Flip user's role + school
        user_result = await db.execute(select(User).where(User.id == app.user_id))
        target_user = user_result.scalar_one_or_none()
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Applicant user no longer exists.",
            )
        target_user.role = UserRole.TEACHER
        target_user.school_id = effective_school_id

    app.status = data.status
    app.review_notes = data.review_notes
    app.reviewed_by_id = staff_user.id
    app.reviewed_at = datetime.now(timezone.utc)
    if data.status == TeacherApplicationStatus.denied:
        app.denial_reason = data.denial_reason

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(TeacherApplication)
        .options(
            joinedload(TeacherApplication.user),
            joinedload(TeacherApplication.school),
            joinedload(TeacherApplication.reviewer),
        )
        .where(TeacherApplication.id == application_id)
    )
    app = result.scalar_one()

    # Send user-facing email -- non-fatal.
    try:
        if app.status == TeacherApplicationStatus.approved:
            await send_teacher_application_approved(
                to_email=app.user.email,
                first_name=app.user.first_name or "",
                school_name=app.school.name if app.school else "your school",
            )
        else:
            await send_teacher_application_denied(
                to_email=app.user.email,
                first_name=app.user.first_name or "",
                denial_reason=app.denial_reason or "",
            )
    except Exception as exc:  # noqa: BLE001  # best-effort review email — review already saved
        logger.warning(
            "Failed to send teacher application review email",
            extra={
                "application_id": app.id,
                "decision": app.status.value,
                "error": str(exc),
            },
        )

    return _build_response(app, staff_user)


@router.post("/staff/{application_id}/approve", response_model=TeacherApplicationResponse)
async def approve_teacher_application(
    application_id: int,
    data: TeacherApplicationReview,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    if data.status != TeacherApplicationStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="approve endpoint requires status=approved",
        )
    return await _review(application_id, data, staff_user, db)


@router.post("/staff/{application_id}/deny", response_model=TeacherApplicationResponse)
async def deny_teacher_application(
    application_id: int,
    data: TeacherApplicationReview,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    if data.status != TeacherApplicationStatus.denied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deny endpoint requires status=denied",
        )
    if not data.denial_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="denial_reason is required when denying",
        )
    return await _review(application_id, data, staff_user, db)
