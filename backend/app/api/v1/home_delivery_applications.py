# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
HomeDelivery Delivery Service - Applications and Enrollment API Endpoints

Provides endpoints for:
- Patron applications for home delivery service
- Staff review of applications
- Enrollment management
- Reading preference profiles
- Patron item requests
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ...core.database import get_db
from ...models.home_delivery import (
    DeliveryVolunteer, HomeDeliveryApplication, HomeDeliveryApplicationStatus,
    HomeDeliveryEnrollment, HomeDeliveryEnrollmentStatus, HomeDeliveryItemRequest,
    ReadingPreferenceProfile
)
from ...models.user import User, name_search_clause
from ...schemas.home_delivery import (
    HomeDeliveryApplicationCreate, HomeDeliveryApplicationListResponse,
    HomeDeliveryApplicationResponse, HomeDeliveryApplicationReview,
    HomeDeliveryEnrollmentCreate, HomeDeliveryEnrollmentListResponse,
    HomeDeliveryEnrollmentResponse, HomeDeliveryEnrollmentStatusUpdate,
    HomeDeliveryEnrollmentUpdate, HomeDeliveryItemRequestCreate,
    HomeDeliveryItemRequestListResponse, HomeDeliveryItemRequestResponse,
    ReadingPreferenceProfileResponse, ReadingPreferenceProfileUpdate
)
from ...services.home_delivery_service import (
    HomeDeliveryApplicationService, HomeDeliveryEnrollmentService
)
from .auth import get_current_user
from .dependencies import require_authenticated, require_staff

router = APIRouter(prefix="/home-delivery", tags=["home-delivery"])


# ============================================================================
# Patron Application Endpoints
# ============================================================================

@router.get("/applications", response_model=list[HomeDeliveryApplicationResponse])
async def list_applications(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List applications (returns current user's applications)."""
    result = await db.execute(
        select(HomeDeliveryApplication)
        .options(joinedload(HomeDeliveryApplication.patron))
        .where(HomeDeliveryApplication.patron_id == current_user.id)
        .order_by(HomeDeliveryApplication.submitted_at.desc())
    )
    applications = result.unique().scalars().all()

    return [
        HomeDeliveryApplicationResponse(
            **{k: v for k, v in app.__dict__.items() if not k.startswith("_")},
            patron_name=app.patron.full_name if app.patron else None,
            patron_library_card=app.patron.library_card if app.patron else None
        )
        for app in applications
    ]


@router.post("/applications", response_model=HomeDeliveryApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: HomeDeliveryApplicationCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Submit an application for home delivery service (patron-facing)."""
    try:
        application = await HomeDeliveryApplicationService.create_application(
            db=db,
            patron_id=current_user.id,
            data=data.model_dump()
        )

        # Reload with relationships
        result = await db.execute(
            select(HomeDeliveryApplication)
            .options(joinedload(HomeDeliveryApplication.patron))
            .where(HomeDeliveryApplication.id == application.id)
        )
        application = result.scalar_one()

        return HomeDeliveryApplicationResponse(
            **{k: v for k, v in application.__dict__.items() if not k.startswith("_")},
            patron_name=application.patron.full_name if application.patron else None,
            patron_library_card=application.patron.library_card if application.patron else None
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/applications/my", response_model=list[HomeDeliveryApplicationResponse])
async def get_my_applications(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's home delivery applications."""
    result = await db.execute(
        select(HomeDeliveryApplication)
        .where(HomeDeliveryApplication.patron_id == current_user.id)
        .order_by(HomeDeliveryApplication.submitted_at.desc())
    )
    applications = result.scalars().all()

    return [
        HomeDeliveryApplicationResponse(
            **{k: v for k, v in app.__dict__.items() if not k.startswith("_")},
            patron_name=current_user.full_name,
            patron_library_card=current_user.library_card
        )
        for app in applications
    ]


@router.get("/enrollment/my", response_model=Optional[HomeDeliveryEnrollmentResponse])
async def get_my_enrollment(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's home delivery enrollment status."""
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .options(
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        return None

    return _build_enrollment_response(enrollment, current_user)


# ============================================================================
# Staff Application Management Endpoints
# ============================================================================

@router.get("/staff/applications", response_model=HomeDeliveryApplicationListResponse)
async def list_applications(
    status: Optional[HomeDeliveryApplicationStatus] = Query(None),
    search: Optional[str] = Query(None, description="Search by patron name or card"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all home delivery applications (staff-facing)."""
    query = (
        select(HomeDeliveryApplication)
        .options(
            joinedload(HomeDeliveryApplication.patron),
            joinedload(HomeDeliveryApplication.reviewer)
        )
    )
    count_query = select(func.count(HomeDeliveryApplication.id))

    if status:
        query = query.where(HomeDeliveryApplication.status == status)
        count_query = count_query.where(HomeDeliveryApplication.status == status)

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        # Names encrypted: exact/last-prefix blind index, not substring.
        _name_clause = name_search_clause(search)
        search_filter = or_(
            User.library_card.ilike(f"%{safe_search}%"),
            *([_name_clause] if _name_clause is not None else []),
        )
        query = query.join(User, HomeDeliveryApplication.patron_id == User.id).where(search_filter)
        count_query = count_query.join(User, HomeDeliveryApplication.patron_id == User.id).where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(HomeDeliveryApplication.submitted_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    applications = result.unique().scalars().all()

    return HomeDeliveryApplicationListResponse(
        applications=[
            HomeDeliveryApplicationResponse(
                **{k: v for k, v in app.__dict__.items() if not k.startswith("_")},
                patron_name=app.patron.full_name if app.patron else None,
                patron_library_card=app.patron.library_card if app.patron else None,
                reviewed_by_name=app.reviewer.full_name if app.reviewer else None
            )
            for app in applications
        ],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/staff/applications/{application_id}", response_model=HomeDeliveryApplicationResponse)
async def get_application(
    application_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific application."""
    result = await db.execute(
        select(HomeDeliveryApplication)
        .options(
            joinedload(HomeDeliveryApplication.patron),
            joinedload(HomeDeliveryApplication.reviewer)
        )
        .where(HomeDeliveryApplication.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return HomeDeliveryApplicationResponse(
        **{k: v for k, v in application.__dict__.items() if not k.startswith("_")},
        patron_name=application.patron.full_name if application.patron else None,
        patron_library_card=application.patron.library_card if application.patron else None,
        reviewed_by_name=application.reviewer.full_name if application.reviewer else None
    )


@router.post("/staff/applications/{application_id}/review", response_model=HomeDeliveryApplicationResponse)
async def review_application(
    application_id: int,
    data: HomeDeliveryApplicationReview,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Review and update application status."""
    try:
        application = await HomeDeliveryApplicationService.review_application(
            db=db,
            application_id=application_id,
            reviewer_id=staff_user.id,
            status=data.status,
            review_notes=data.review_notes,
            denial_reason=data.denial_reason
        )

        # Reload with relationships
        result = await db.execute(
            select(HomeDeliveryApplication)
            .options(
                joinedload(HomeDeliveryApplication.patron),
                joinedload(HomeDeliveryApplication.reviewer)
            )
            .where(HomeDeliveryApplication.id == application.id)
        )
        application = result.scalar_one()

        return HomeDeliveryApplicationResponse(
            **{k: v for k, v in application.__dict__.items() if not k.startswith("_")},
            patron_name=application.patron.full_name if application.patron else None,
            patron_library_card=application.patron.library_card if application.patron else None,
            reviewed_by_name=application.reviewer.full_name if application.reviewer else None
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Staff Enrollment Management Endpoints
# ============================================================================

@router.post("/staff/enrollments", response_model=HomeDeliveryEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    data: HomeDeliveryEnrollmentCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create enrollment from approved application."""
    try:
        overrides = {
            "delivery_address": data.delivery_address,
            "delivery_instructions": data.delivery_instructions,
            "contact_phone": data.contact_phone,
            "delivery_frequency": data.delivery_frequency,
            "preferred_day": data.preferred_day,
            "preferred_time_start": data.preferred_time_start,
            "preferred_time_end": data.preferred_time_end,
            "assigned_volunteer_id": data.assigned_volunteer_id,
            "next_scheduled_delivery": data.next_scheduled_delivery
        }

        enrollment = await HomeDeliveryEnrollmentService.create_enrollment(
            db=db,
            application_id=data.application_id,
            enrolled_by_id=staff_user.id,
            overrides=overrides
        )

        # Reload with relationships
        result = await db.execute(
            select(HomeDeliveryEnrollment)
            .options(
                joinedload(HomeDeliveryEnrollment.patron),
                selectinload(HomeDeliveryEnrollment.reading_preferences),
                selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
            )
            .where(HomeDeliveryEnrollment.id == enrollment.id)
        )
        enrollment = result.scalar_one()

        return _build_enrollment_response(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/staff/enrollments", response_model=HomeDeliveryEnrollmentListResponse)
async def list_enrollments(
    status: Optional[HomeDeliveryEnrollmentStatus] = Query(None),
    search: Optional[str] = Query(None),
    volunteer_id: Optional[int] = Query(None),
    upcoming_delivery: bool = Query(False, description="Filter by upcoming delivery date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all home delivery enrollments."""
    query = (
        select(HomeDeliveryEnrollment)
        .options(
            joinedload(HomeDeliveryEnrollment.patron),
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
    )
    count_query = select(func.count(HomeDeliveryEnrollment.id))

    if status:
        query = query.where(HomeDeliveryEnrollment.status == status)
        count_query = count_query.where(HomeDeliveryEnrollment.status == status)

    if volunteer_id:
        query = query.where(HomeDeliveryEnrollment.assigned_volunteer_id == volunteer_id)
        count_query = count_query.where(HomeDeliveryEnrollment.assigned_volunteer_id == volunteer_id)

    if upcoming_delivery:
        today = date.today()
        next_week = today + timedelta(days=7)
        query = query.where(
            HomeDeliveryEnrollment.next_scheduled_delivery.between(today, next_week)
        )
        count_query = count_query.where(
            HomeDeliveryEnrollment.next_scheduled_delivery.between(today, next_week)
        )

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        # Names encrypted: exact/last-prefix blind index, not substring.
        _name_clause = name_search_clause(search)
        search_filter = or_(
            User.library_card.ilike(f"%{safe_search}%"),
            *([_name_clause] if _name_clause is not None else []),
        )
        query = query.join(User, HomeDeliveryEnrollment.patron_id == User.id).where(search_filter)
        count_query = count_query.join(User, HomeDeliveryEnrollment.patron_id == User.id).where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(HomeDeliveryEnrollment.next_scheduled_delivery.asc().nulls_last()).limit(limit).offset(offset)
    result = await db.execute(query)
    enrollments = result.unique().scalars().all()

    return HomeDeliveryEnrollmentListResponse(
        enrollments=[_build_enrollment_response(e) for e in enrollments],
        total=total,
        limit=limit,
        offset=offset
    )


from datetime import timedelta


@router.get("/staff/enrollments/{enrollment_id}", response_model=HomeDeliveryEnrollmentResponse)
async def get_enrollment(
    enrollment_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific enrollment."""
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .options(
            joinedload(HomeDeliveryEnrollment.patron),
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
        .where(HomeDeliveryEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    return _build_enrollment_response(enrollment)


@router.patch("/staff/enrollments/{enrollment_id}", response_model=HomeDeliveryEnrollmentResponse)
async def update_enrollment(
    enrollment_id: int,
    data: HomeDeliveryEnrollmentUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update enrollment details."""
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(enrollment, key, value)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .options(
            joinedload(HomeDeliveryEnrollment.patron),
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
        .where(HomeDeliveryEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one()

    return _build_enrollment_response(enrollment)


@router.post("/staff/enrollments/{enrollment_id}/status", response_model=HomeDeliveryEnrollmentResponse)
async def update_enrollment_status(
    enrollment_id: int,
    data: HomeDeliveryEnrollmentStatusUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update enrollment status (pause, resume, terminate)."""
    try:
        enrollment = await HomeDeliveryEnrollmentService.update_enrollment_status(
            db=db,
            enrollment_id=enrollment_id,
            status=data.status,
            pause_reason=data.pause_reason,
            pause_until=data.pause_until,
            termination_reason=data.termination_reason
        )

        # Reload with relationships
        result = await db.execute(
            select(HomeDeliveryEnrollment)
            .options(
                joinedload(HomeDeliveryEnrollment.patron),
                selectinload(HomeDeliveryEnrollment.reading_preferences),
                selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
            )
            .where(HomeDeliveryEnrollment.id == enrollment.id)
        )
        enrollment = result.scalar_one()

        return _build_enrollment_response(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Reading Preferences Endpoints
# ============================================================================

@router.get("/staff/enrollments/{enrollment_id}/preferences", response_model=ReadingPreferenceProfileResponse)
async def get_reading_preferences(
    enrollment_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get reading preferences for an enrollment."""
    result = await db.execute(
        select(ReadingPreferenceProfile)
        .where(ReadingPreferenceProfile.enrollment_id == enrollment_id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading preferences not found")

    return ReadingPreferenceProfileResponse.model_validate(prefs)


@router.patch("/staff/enrollments/{enrollment_id}/preferences", response_model=ReadingPreferenceProfileResponse)
async def update_reading_preferences(
    enrollment_id: int,
    data: ReadingPreferenceProfileUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update reading preferences for an enrollment."""
    result = await db.execute(
        select(ReadingPreferenceProfile)
        .where(ReadingPreferenceProfile.enrollment_id == enrollment_id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading preferences not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prefs, key, value)

    await db.commit()
    await db.refresh(prefs)

    return ReadingPreferenceProfileResponse.model_validate(prefs)


# ============================================================================
# Patron Item Requests
# ============================================================================

@router.post("/item-requests", response_model=HomeDeliveryItemRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_item_request(
    data: HomeDeliveryItemRequestCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create an item request for next delivery (patron-facing)."""
    # Get patron's enrollment
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(
            HomeDeliveryEnrollment.patron_id == current_user.id,
            HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.active
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active home delivery enrollment found")

    request = HomeDeliveryItemRequest(
        enrollment_id=enrollment.id,
        **data.model_dump()
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)

    return HomeDeliveryItemRequestResponse(
        **{k: v for k, v in request.__dict__.items() if not k.startswith("_")}
    )


@router.get("/item-requests/my", response_model=HomeDeliveryItemRequestListResponse)
async def get_my_item_requests(
    fulfilled: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's item requests."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        return HomeDeliveryItemRequestListResponse(requests=[], total=0, limit=limit, offset=offset)

    query = select(HomeDeliveryItemRequest).where(HomeDeliveryItemRequest.enrollment_id == enrollment.id)
    count_query = select(func.count(HomeDeliveryItemRequest.id)).where(
        HomeDeliveryItemRequest.enrollment_id == enrollment.id
    )

    if fulfilled is not None:
        query = query.where(HomeDeliveryItemRequest.fulfilled == fulfilled)
        count_query = count_query.where(HomeDeliveryItemRequest.fulfilled == fulfilled)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(HomeDeliveryItemRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    requests = result.scalars().all()

    return HomeDeliveryItemRequestListResponse(
        requests=[
            HomeDeliveryItemRequestResponse(
                **{k: v for k, v in req.__dict__.items() if not k.startswith("_")}
            )
            for req in requests
        ],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/staff/enrollments/{enrollment_id}/item-requests", response_model=HomeDeliveryItemRequestListResponse)
async def get_enrollment_item_requests(
    enrollment_id: int,
    fulfilled: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get item requests for an enrollment (staff-facing)."""
    query = (
        select(HomeDeliveryItemRequest)
        .options(joinedload(HomeDeliveryItemRequest.item))
        .where(HomeDeliveryItemRequest.enrollment_id == enrollment_id)
    )
    count_query = select(func.count(HomeDeliveryItemRequest.id)).where(
        HomeDeliveryItemRequest.enrollment_id == enrollment_id
    )

    if fulfilled is not None:
        query = query.where(HomeDeliveryItemRequest.fulfilled == fulfilled)
        count_query = count_query.where(HomeDeliveryItemRequest.fulfilled == fulfilled)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(HomeDeliveryItemRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    requests = result.unique().scalars().all()

    return HomeDeliveryItemRequestListResponse(
        requests=[
            HomeDeliveryItemRequestResponse(
                **{k: v for k, v in req.__dict__.items() if not k.startswith("_")},
                item_title=req.item.title if req.item else None
            )
            for req in requests
        ],
        total=total,
        limit=limit,
        offset=offset
    )


# ============================================================================
# Patron Self-Service Endpoints
# ============================================================================

@router.patch("/enrollment/my/preferences", response_model=ReadingPreferenceProfileResponse)
async def update_my_reading_preferences(
    data: ReadingPreferenceProfileUpdate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update reading preferences (patron-facing)."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrollment found")

    result = await db.execute(
        select(ReadingPreferenceProfile)
        .where(ReadingPreferenceProfile.enrollment_id == enrollment.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading preferences not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prefs, key, value)

    await db.commit()
    await db.refresh(prefs)

    return ReadingPreferenceProfileResponse.model_validate(prefs)


@router.post("/enrollment/my/pause", response_model=HomeDeliveryEnrollmentResponse)
async def pause_my_enrollment(
    pause_until: Optional[date] = Query(None, description="Date to automatically resume"),
    reason: Optional[str] = Query(None, max_length=500),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Pause home delivery enrollment (patron-facing)."""
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .options(
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
        .where(
            HomeDeliveryEnrollment.patron_id == current_user.id,
            HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.active
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active enrollment found"
        )

    try:
        from datetime import timezone as tz
        enrollment.status = HomeDeliveryEnrollmentStatus.paused
        enrollment.paused_at = datetime.now(tz.utc)
        enrollment.pause_reason = reason or "Paused by patron"
        enrollment.pause_until = pause_until

        await db.commit()
        await db.refresh(enrollment)

        return _build_enrollment_response(enrollment, current_user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/enrollment/my/resume", response_model=HomeDeliveryEnrollmentResponse)
async def resume_my_enrollment(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Resume paused home delivery enrollment (patron-facing)."""
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .options(
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
        .where(
            HomeDeliveryEnrollment.patron_id == current_user.id,
            HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.paused
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No paused enrollment found"
        )

    enrollment.status = HomeDeliveryEnrollmentStatus.active
    enrollment.paused_at = None
    enrollment.pause_reason = None
    enrollment.pause_until = None

    # Calculate next delivery date
    next_delivery = await HomeDeliveryEnrollmentService.calculate_next_delivery_date(
        enrollment.delivery_frequency,
        enrollment.preferred_day
    )
    enrollment.next_scheduled_delivery = next_delivery

    await db.commit()
    await db.refresh(enrollment)

    return _build_enrollment_response(enrollment, current_user)


@router.patch("/enrollment/my", response_model=HomeDeliveryEnrollmentResponse)
async def update_my_enrollment(
    delivery_instructions: Optional[str] = Query(None, max_length=1000),
    contact_phone: Optional[str] = Query(None, max_length=20),
    alternate_contact_name: Optional[str] = Query(None, max_length=200),
    alternate_contact_phone: Optional[str] = Query(None, max_length=20),
    preferred_day: Optional[str] = Query(None, max_length=20),
    preferred_time_start: Optional[str] = Query(None, pattern=r"^\d{2}:\d{2}$"),
    preferred_time_end: Optional[str] = Query(None, pattern=r"^\d{2}:\d{2}$"),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update enrollment details (patron-facing, limited fields)."""
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .options(
            selectinload(HomeDeliveryEnrollment.reading_preferences),
            selectinload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
        )
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrollment found")

    # Update only allowed fields
    if delivery_instructions is not None:
        enrollment.delivery_instructions = delivery_instructions
    if contact_phone is not None:
        enrollment.contact_phone = contact_phone
    if alternate_contact_name is not None:
        enrollment.alternate_contact_name = alternate_contact_name
    if alternate_contact_phone is not None:
        enrollment.alternate_contact_phone = alternate_contact_phone
    if preferred_day is not None:
        enrollment.preferred_day = preferred_day
    if preferred_time_start is not None:
        enrollment.preferred_time_start = preferred_time_start
    if preferred_time_end is not None:
        enrollment.preferred_time_end = preferred_time_end

    await db.commit()
    await db.refresh(enrollment)

    return _build_enrollment_response(enrollment, current_user)


# ============================================================================
# Helper Functions
# ============================================================================

def _build_enrollment_response(
    enrollment: HomeDeliveryEnrollment,
    patron: Optional[User] = None
) -> HomeDeliveryEnrollmentResponse:
    patron = patron or enrollment.patron

    reading_prefs = None
    if enrollment.reading_preferences:
        reading_prefs = ReadingPreferenceProfileResponse.model_validate(enrollment.reading_preferences)

    volunteer_name = None
    if enrollment.assigned_volunteer and enrollment.assigned_volunteer.user:
        volunteer_name = enrollment.assigned_volunteer.user.full_name

    return HomeDeliveryEnrollmentResponse(
        id=enrollment.id,
        patron_id=enrollment.patron_id,
        patron_name=patron.full_name if patron else None,
        patron_library_card=patron.library_card if patron else None,
        application_id=enrollment.application_id,
        status=enrollment.status,
        delivery_address=enrollment.delivery_address,
        delivery_instructions=enrollment.delivery_instructions,
        contact_phone=enrollment.contact_phone,
        alternate_contact_name=enrollment.alternate_contact_name,
        alternate_contact_phone=enrollment.alternate_contact_phone,
        delivery_frequency=enrollment.delivery_frequency,
        preferred_day=enrollment.preferred_day,
        preferred_time_start=enrollment.preferred_time_start,
        preferred_time_end=enrollment.preferred_time_end,
        next_scheduled_delivery=enrollment.next_scheduled_delivery,
        assigned_volunteer_id=enrollment.assigned_volunteer_id,
        assigned_volunteer_name=volunteer_name,
        enrolled_at=enrollment.enrolled_at,
        paused_at=enrollment.paused_at,
        pause_reason=enrollment.pause_reason,
        pause_until=enrollment.pause_until,
        total_deliveries=enrollment.total_deliveries,
        last_delivery_date=enrollment.last_delivery_date,
        reading_preferences=reading_prefs
    )


@router.get("/enrollment/my/pause")
async def get_enrollment_my_pause(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Get information about pausing home delivery enrollment.

    Returns current enrollment status and pause capabilities.
    """
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        return {
            "endpoint": "POST /home-delivery/enrollment/my/pause",
            "description": "Pause your home delivery enrollment",
            "enrolled": False,
            "message": "No active enrollment found",
        }

    return {
        "endpoint": "POST /home-delivery/enrollment/my/pause",
        "description": "Pause your home delivery enrollment",
        "enrolled": True,
        "current_status": str(enrollment.status),
        "can_pause": enrollment.status == HomeDeliveryEnrollmentStatus.active,
        "optional_parameters": {
            "pause_until": "Date to automatically resume (YYYY-MM-DD)",
            "reason": "Reason for pausing (optional)",
        },
        "notes": "Your deliveries will be temporarily stopped. You can resume at any time.",
    }



@router.get("/enrollment/my/preferences")
async def get_enrollment_my_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Get current reading preferences for user's home delivery enrollment.

    Returns the patron's reading preference profile if enrolled.
    """
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        return {
            "endpoint": "PATCH /home-delivery/enrollment/my/preferences",
            "description": "Update your reading preferences",
            "enrolled": False,
            "message": "No enrollment found",
        }

    # Get reading preferences
    result = await db.execute(
        select(ReadingPreferenceProfile)
        .where(ReadingPreferenceProfile.enrollment_id == enrollment.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        return {
            "endpoint": "PATCH /home-delivery/enrollment/my/preferences",
            "description": "Update your reading preferences",
            "enrolled": True,
            "preferences": None,
            "message": "No preferences profile found",
        }

    return {
        "endpoint": "PATCH /home-delivery/enrollment/my/preferences",
        "description": "Update your reading preferences",
        "enrolled": True,
        "current_preferences": ReadingPreferenceProfileResponse.model_validate(prefs).model_dump(),
        "updatable_fields": [
            "preferred_genres",
            "preferred_formats",
            "preferred_authors",
            "reading_level",
            "interests",
            "exclusions",
            "items_per_delivery",
            "prefer_fiction",
            "prefer_nonfiction",
            "prefer_large_print",
            "prefer_audiobooks",
        ],
    }



@router.get("/enrollment/my/resume")
async def get_enrollment_my_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Get information about resuming paused home delivery enrollment.

    Returns current pause status and resume capabilities.
    """
    result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        return {
            "endpoint": "POST /home-delivery/enrollment/my/resume",
            "description": "Resume your paused home delivery enrollment",
            "enrolled": False,
            "message": "No enrollment found",
        }

    return {
        "endpoint": "POST /home-delivery/enrollment/my/resume",
        "description": "Resume your paused home delivery enrollment",
        "enrolled": True,
        "current_status": str(enrollment.status),
        "can_resume": enrollment.status == HomeDeliveryEnrollmentStatus.paused,
        "paused_at": enrollment.paused_at.isoformat() if enrollment.paused_at else None,
        "pause_reason": enrollment.pause_reason,
        "pause_until": enrollment.pause_until.isoformat() if enrollment.pause_until else None,
        "notes": "Resuming will reactivate your deliveries and calculate your next delivery date.",
    }



@router.get("/item-requests")
async def get_item_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Get information about creating item requests.

    Returns guidance on how to request items for next delivery.
    """
    # Check if user has active enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(
            HomeDeliveryEnrollment.patron_id == current_user.id,
            HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.active
        )
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        return {
            "endpoint": "POST /home-delivery/item-requests",
            "description": "Request specific items for your next delivery",
            "enrolled": False,
            "can_request": False,
            "message": "You must have an active home delivery enrollment to request items",
        }

    # Get count of pending requests
    pending_count_result = await db.execute(
        select(func.count(HomeDeliveryItemRequest.id)).where(
            HomeDeliveryItemRequest.enrollment_id == enrollment.id,
            HomeDeliveryItemRequest.fulfilled == False
        )
    )
    pending_count = pending_count_result.scalar() or 0

    return {
        "endpoint": "POST /home-delivery/item-requests",
        "description": "Request specific items for your next delivery",
        "enrolled": True,
        "can_request": True,
        "enrollment_id": enrollment.id,
        "next_delivery": enrollment.next_scheduled_delivery.isoformat() if enrollment.next_scheduled_delivery else None,
        "pending_requests": pending_count,
        "required_fields": ["request_type", "title"],
        "optional_fields": ["author", "isbn", "catalog_item_id", "notes", "priority"],
        "request_types": ["specific_item", "subject_area", "author_works", "similar_to"],
        "notes": "Requests will be fulfilled for your next scheduled delivery.",
    }

