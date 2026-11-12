# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
HomeDelivery Delivery Service - Volunteer Management API Endpoints

Provides endpoints for:
- Volunteer registration and profiles
- Volunteer approval workflow
- Volunteer schedules
- Hour logging and verification
- Volunteer statistics and recognition
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.database import get_db
from ...models.home_delivery import (
    DeliveryVolunteer, HomeDeliveryEnrollment, VolunteerHourLog,
    VolunteerSchedule, DeliveryVolunteerStatus
)
from ...models.user import User, name_or_email_clause
from ...schemas.home_delivery import (
    DeliveryVolunteerCreate, DeliveryVolunteerListResponse,
    DeliveryVolunteerResponse, DeliveryVolunteerStatusUpdate,
    DeliveryVolunteerUpdate, VolunteerHourLogCreate,
    VolunteerHourLogListResponse, VolunteerHourLogResponse,
    VolunteerScheduleCreate, VolunteerScheduleResponse
)
from ...services.home_delivery_service import DeliveryVolunteerService
from .auth import get_current_user
from .dependencies import require_authenticated, require_staff

router = APIRouter(prefix="/home-delivery/volunteers", tags=["home-delivery-volunteers"])


# ============================================================================
# Volunteer Registration (Self-service)
# ============================================================================

@router.post("/register", response_model=DeliveryVolunteerResponse, status_code=status.HTTP_201_CREATED)
async def register_as_volunteer(
    data: DeliveryVolunteerCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Register current user as a delivery volunteer."""
    # User can only register themselves
    if data.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only register yourself as a volunteer")

    try:
        volunteer = await DeliveryVolunteerService.create_volunteer(
            db=db,
            user_id=current_user.id,
            data=data.model_dump(exclude={"user_id"})
        )

        return _build_volunteer_response(volunteer, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/my-profile", response_model=Optional[DeliveryVolunteerResponse])
async def get_my_volunteer_profile(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's volunteer profile."""
    result = await db.execute(
        select(DeliveryVolunteer)
        .where(DeliveryVolunteer.user_id == current_user.id)
    )
    volunteer = result.scalar_one_or_none()

    if not volunteer:
        return None

    # Get assigned patrons count
    patron_count = await db.execute(
        select(func.count(HomeDeliveryEnrollment.id))
        .where(HomeDeliveryEnrollment.assigned_volunteer_id == volunteer.id)
    )

    return _build_volunteer_response(volunteer, current_user, patron_count.scalar() or 0)


@router.patch("/my-profile", response_model=DeliveryVolunteerResponse)
async def update_my_volunteer_profile(
    data: DeliveryVolunteerUpdate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's volunteer profile."""
    result = await db.execute(
        select(DeliveryVolunteer)
        .where(DeliveryVolunteer.user_id == current_user.id)
    )
    volunteer = result.scalar_one_or_none()

    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer profile not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(volunteer, key, value)

    await db.commit()
    await db.refresh(volunteer)

    return _build_volunteer_response(volunteer, current_user)


# ============================================================================
# My Hours (Volunteer Self-Service)
# ============================================================================

@router.get("/my-hours", response_model=VolunteerHourLogListResponse)
async def get_my_hours(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's volunteer hours."""
    # Get volunteer profile
    volunteer_result = await db.execute(
        select(DeliveryVolunteer)
        .where(DeliveryVolunteer.user_id == current_user.id)
    )
    volunteer = volunteer_result.scalar_one_or_none()

    if not volunteer:
        return VolunteerHourLogListResponse(logs=[], total=0, total_hours=0, limit=limit, offset=offset)

    query = select(VolunteerHourLog).where(VolunteerHourLog.volunteer_id == volunteer.id)
    count_query = select(func.count(VolunteerHourLog.id)).where(
        VolunteerHourLog.volunteer_id == volunteer.id
    )
    hours_query = select(func.sum(VolunteerHourLog.hours)).where(
        VolunteerHourLog.volunteer_id == volunteer.id
    )

    if start_date:
        query = query.where(VolunteerHourLog.date >= start_date)
        count_query = count_query.where(VolunteerHourLog.date >= start_date)
        hours_query = hours_query.where(VolunteerHourLog.date >= start_date)
    if end_date:
        query = query.where(VolunteerHourLog.date <= end_date)
        count_query = count_query.where(VolunteerHourLog.date <= end_date)
        hours_query = hours_query.where(VolunteerHourLog.date <= end_date)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_hours_result = await db.execute(hours_query)
    total_hours = total_hours_result.scalar() or 0

    query = query.order_by(VolunteerHourLog.date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    logs = result.scalars().all()

    return VolunteerHourLogListResponse(
        logs=[
            VolunteerHourLogResponse(
                **{k: v for k, v in log.__dict__.items() if not k.startswith("_")},
                volunteer_name=current_user.full_name
            )
            for log in logs
        ],
        total=total,
        total_hours=round(total_hours, 2),
        limit=limit,
        offset=offset
    )


# ============================================================================
# Staff Volunteer Management
# ============================================================================

@router.get("", response_model=DeliveryVolunteerListResponse)
async def list_volunteers(
    status: Optional[DeliveryVolunteerStatus] = Query(None),
    search: Optional[str] = Query(None, description="Search by name or email"),
    available_on: Optional[date] = Query(None, description="Filter by availability on date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all delivery volunteers."""
    query = (
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
    )
    count_query = select(func.count(DeliveryVolunteer.id))

    if status:
        query = query.where(DeliveryVolunteer.status == status)
        count_query = count_query.where(DeliveryVolunteer.status == status)

    _search_clause = name_or_email_clause(search) if search else None
    if _search_clause is not None:
        # Names + email encrypted: exact email + name blind index, not substring.
        query = query.join(User, DeliveryVolunteer.user_id == User.id).where(_search_clause)
        count_query = count_query.join(User, DeliveryVolunteer.user_id == User.id).where(_search_clause)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DeliveryVolunteer.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    volunteers = result.unique().scalars().all()

    # Get assigned patron counts
    volunteer_responses = []
    for volunteer in volunteers:
        patron_count = await db.execute(
            select(func.count(HomeDeliveryEnrollment.id))
            .where(HomeDeliveryEnrollment.assigned_volunteer_id == volunteer.id)
        )
        volunteer_responses.append(
            _build_volunteer_response(volunteer, volunteer.user, patron_count.scalar() or 0)
        )

    # Filter by availability if specified
    if available_on:
        day_name = available_on.strftime("%A")
        filtered_volunteers = []
        for v_response, volunteer in zip(volunteer_responses, volunteers):
            # Check if day is in available days
            if day_name in (volunteer.available_days or []):
                # Check for specific schedule override
                schedule_result = await db.execute(
                    select(VolunteerSchedule)
                    .where(
                        VolunteerSchedule.volunteer_id == volunteer.id,
                        VolunteerSchedule.date == available_on
                    )
                )
                schedule = schedule_result.scalar_one_or_none()
                if not schedule or schedule.is_available:
                    filtered_volunteers.append(v_response)

        return DeliveryVolunteerListResponse(
            volunteers=filtered_volunteers,
            total=len(filtered_volunteers),
            limit=limit,
            offset=offset
        )

    return DeliveryVolunteerListResponse(
        volunteers=volunteer_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{volunteer_id}", response_model=DeliveryVolunteerResponse)
async def get_volunteer(
    volunteer_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific volunteer."""
    result = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.id == volunteer_id)
    )
    volunteer = result.scalar_one_or_none()

    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    patron_count = await db.execute(
        select(func.count(HomeDeliveryEnrollment.id))
        .where(HomeDeliveryEnrollment.assigned_volunteer_id == volunteer.id)
    )

    return _build_volunteer_response(volunteer, volunteer.user, patron_count.scalar() or 0)


@router.patch("/{volunteer_id}", response_model=DeliveryVolunteerResponse)
async def update_volunteer(
    volunteer_id: int,
    data: DeliveryVolunteerUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a volunteer's profile (staff)."""
    result = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.id == volunteer_id)
    )
    volunteer = result.scalar_one_or_none()

    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(volunteer, key, value)

    await db.commit()
    await db.refresh(volunteer)

    return _build_volunteer_response(volunteer, volunteer.user)


@router.post("/{volunteer_id}/status", response_model=DeliveryVolunteerResponse)
async def update_volunteer_status(
    volunteer_id: int,
    data: DeliveryVolunteerStatusUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update volunteer status (approve, deactivate, etc.)."""
    result = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.id == volunteer_id)
    )
    volunteer = result.scalar_one_or_none()

    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    # Handle approval
    if data.status == DeliveryVolunteerStatus.active and volunteer.status == DeliveryVolunteerStatus.pending_approval:
        try:
            # Update background check and training first if provided
            if data.background_check_completed is not None:
                volunteer.background_check_completed = data.background_check_completed
            if data.background_check_date:
                volunteer.background_check_date = data.background_check_date
            if data.background_check_expiry:
                volunteer.background_check_expiry = data.background_check_expiry
            if data.training_completed is not None:
                volunteer.training_completed = data.training_completed
            if data.training_date:
                volunteer.training_date = data.training_date

            await db.commit()

            volunteer = await DeliveryVolunteerService.approve_volunteer(
                db=db,
                volunteer_id=volunteer_id,
                approved_by_id=staff_user.id
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    else:
        # Direct status update
        volunteer.status = data.status

        # Update optional fields
        if data.background_check_completed is not None:
            volunteer.background_check_completed = data.background_check_completed
        if data.background_check_date:
            volunteer.background_check_date = data.background_check_date
        if data.background_check_expiry:
            volunteer.background_check_expiry = data.background_check_expiry
        if data.training_completed is not None:
            volunteer.training_completed = data.training_completed
        if data.training_date:
            volunteer.training_date = data.training_date

        await db.commit()

    # Reload
    result = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.id == volunteer_id)
    )
    volunteer = result.scalar_one()

    return _build_volunteer_response(volunteer, volunteer.user)


# ============================================================================
# Volunteer Schedule Management
# ============================================================================

@router.get("/{volunteer_id}/schedule", response_model=list[VolunteerScheduleResponse])
async def get_volunteer_schedule(
    volunteer_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get volunteer's schedule entries."""
    query = (
        select(VolunteerSchedule)
        .where(VolunteerSchedule.volunteer_id == volunteer_id)
    )

    if start_date:
        query = query.where(VolunteerSchedule.date >= start_date)
    if end_date:
        query = query.where(VolunteerSchedule.date <= end_date)

    query = query.order_by(VolunteerSchedule.date).limit(500)
    result = await db.execute(query)
    schedules = result.scalars().all()

    return [VolunteerScheduleResponse.model_validate(s) for s in schedules]


@router.post("/{volunteer_id}/schedule", response_model=VolunteerScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule_entry(
    volunteer_id: int,
    data: VolunteerScheduleCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a schedule entry for a volunteer."""
    # Check if volunteer exists
    volunteer_result = await db.execute(
        select(DeliveryVolunteer).where(DeliveryVolunteer.id == volunteer_id)
    )
    if not volunteer_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    # Check for existing entry on this date
    existing = await db.execute(
        select(VolunteerSchedule)
        .where(
            VolunteerSchedule.volunteer_id == volunteer_id,
            VolunteerSchedule.date == data.date
        )
    )
    schedule = existing.scalar_one_or_none()

    if schedule:
        # Update existing
        for key, value in data.model_dump().items():
            setattr(schedule, key, value)
    else:
        # Create new
        schedule = VolunteerSchedule(
            volunteer_id=volunteer_id,
            **data.model_dump()
        )
        db.add(schedule)

    await db.commit()
    await db.refresh(schedule)

    return VolunteerScheduleResponse.model_validate(schedule)


@router.delete("/{volunteer_id}/schedule/{schedule_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_entry(
    volunteer_id: int,
    schedule_date: date,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule entry."""
    result = await db.execute(
        select(VolunteerSchedule)
        .where(
            VolunteerSchedule.volunteer_id == volunteer_id,
            VolunteerSchedule.date == schedule_date
        )
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule entry not found")

    await db.delete(schedule)
    await db.commit()

    return None


# ============================================================================
# Volunteer Hour Logging
# ============================================================================

@router.get("/{volunteer_id}/hours", response_model=VolunteerHourLogListResponse)
async def get_volunteer_hours(
    volunteer_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    verified_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get volunteer's hour logs."""
    query = (
        select(VolunteerHourLog)
        .options(joinedload(VolunteerHourLog.verified_by))
        .where(VolunteerHourLog.volunteer_id == volunteer_id)
    )
    count_query = select(func.count(VolunteerHourLog.id)).where(
        VolunteerHourLog.volunteer_id == volunteer_id
    )
    hours_query = select(func.sum(VolunteerHourLog.hours)).where(
        VolunteerHourLog.volunteer_id == volunteer_id
    )

    if start_date:
        query = query.where(VolunteerHourLog.date >= start_date)
        count_query = count_query.where(VolunteerHourLog.date >= start_date)
        hours_query = hours_query.where(VolunteerHourLog.date >= start_date)
    if end_date:
        query = query.where(VolunteerHourLog.date <= end_date)
        count_query = count_query.where(VolunteerHourLog.date <= end_date)
        hours_query = hours_query.where(VolunteerHourLog.date <= end_date)
    if verified_only:
        query = query.where(VolunteerHourLog.verified == True)
        count_query = count_query.where(VolunteerHourLog.verified == True)
        hours_query = hours_query.where(VolunteerHourLog.verified == True)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_hours_result = await db.execute(hours_query)
    total_hours = total_hours_result.scalar() or 0

    query = query.order_by(VolunteerHourLog.date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    logs = result.unique().scalars().all()

    # Get volunteer for name
    volunteer_result = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.id == volunteer_id)
    )
    volunteer = volunteer_result.scalar_one_or_none()
    volunteer_name = volunteer.user.full_name if volunteer and volunteer.user else None

    return VolunteerHourLogListResponse(
        logs=[
            VolunteerHourLogResponse(
                **{k: v for k, v in log.__dict__.items() if not k.startswith("_")},
                volunteer_name=volunteer_name,
                verified_by_name=log.verified_by.full_name if log.verified_by else None
            )
            for log in logs
        ],
        total=total,
        total_hours=round(total_hours, 2),
        limit=limit,
        offset=offset
    )


@router.post("/{volunteer_id}/hours", response_model=VolunteerHourLogResponse, status_code=status.HTTP_201_CREATED)
async def log_volunteer_hours(
    volunteer_id: int,
    data: VolunteerHourLogCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Log hours for a volunteer."""
    try:
        hour_log = await DeliveryVolunteerService.log_volunteer_hours(
            db=db,
            volunteer_id=volunteer_id,
            date=data.date,
            hours=data.hours,
            activity_type=data.activity_type,
            delivery_route_id=data.delivery_route_id,
            notes=data.notes
        )

        # Get volunteer for name
        volunteer_result = await db.execute(
            select(DeliveryVolunteer)
            .options(joinedload(DeliveryVolunteer.user))
            .where(DeliveryVolunteer.id == volunteer_id)
        )
        volunteer = volunteer_result.scalar_one_or_none()

        return VolunteerHourLogResponse(
            **{k: v for k, v in hour_log.__dict__.items() if not k.startswith("_")},
            volunteer_name=volunteer.user.full_name if volunteer and volunteer.user else None
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/hours/{log_id}/verify", response_model=VolunteerHourLogResponse)
async def verify_volunteer_hours(
    log_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Verify a volunteer hour log entry."""
    result = await db.execute(
        select(VolunteerHourLog)
        .options(
            joinedload(VolunteerHourLog.volunteer).joinedload(DeliveryVolunteer.user),
            joinedload(VolunteerHourLog.verified_by)
        )
        .where(VolunteerHourLog.id == log_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hour log not found")

    log.verified = True
    log.verified_by_id = staff_user.id
    log.verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(log)

    return VolunteerHourLogResponse(
        **{k: v for k, v in log.__dict__.items() if not k.startswith("_")},
        volunteer_name=log.volunteer.user.full_name if log.volunteer and log.volunteer.user else None,
        verified_by_name=staff_user.full_name
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _build_volunteer_response(
    volunteer: DeliveryVolunteer,
    user: Optional[User] = None,
    assigned_patrons_count: int = 0
) -> DeliveryVolunteerResponse:
    user = user or volunteer.user

    return DeliveryVolunteerResponse(
        id=volunteer.id,
        user_id=volunteer.user_id,
        user_name=user.full_name if user else None,
        user_email=user.email if user else None,
        status=volunteer.status,
        phone=volunteer.phone,
        emergency_contact_name=volunteer.emergency_contact_name,
        emergency_contact_phone=volunteer.emergency_contact_phone,
        has_vehicle=volunteer.has_vehicle,
        vehicle_type=volunteer.vehicle_type,
        can_transport_large_items=volunteer.can_transport_large_items,
        background_check_completed=volunteer.background_check_completed,
        background_check_date=volunteer.background_check_date,
        background_check_expiry=volunteer.background_check_expiry,
        training_completed=volunteer.training_completed,
        training_date=volunteer.training_date,
        available_days=volunteer.available_days or [],
        available_time_start=volunteer.available_time_start,
        available_time_end=volunteer.available_time_end,
        max_deliveries_per_day=volunteer.max_deliveries_per_day,
        max_deliveries_per_week=volunteer.max_deliveries_per_week,
        preferred_areas=volunteer.preferred_areas or [],
        max_driving_distance=volunteer.max_driving_distance,
        total_deliveries=volunteer.total_deliveries,
        total_volunteer_hours=volunteer.total_volunteer_hours,
        recognition_level=volunteer.recognition_level,
        achievements=volunteer.achievements or [],
        approved_at=volunteer.approved_at,
        last_active_at=volunteer.last_active_at,
        assigned_patrons_count=assigned_patrons_count
    )



