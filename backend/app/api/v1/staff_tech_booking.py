# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff technology assistance booking management routes."""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.tech_booking import (
    BookingStatus, TechAssistanceBooking, TechAssistanceStaff,
    TechResourceHandout, TechSessionNote, TechVolunteerTutor,
)
from ...models.user import User, UserRole
from ...schemas.tech_booking import (
    BookingDetailResponse, CompleteSessionRequest,
    ImpactSummaryResponse, TechAssistanceBookingResponse,
    TechAssistanceStaffCreate, TechAssistanceStaffResponse,
    TechAssistanceStaffUpdate, TechFollowUpBookingCreate,
    TechFollowUpBookingResponse, TechResourceHandoutCreate,
    TechResourceHandoutResponse, TechVolunteerTutorCreate,
    TechVolunteerTutorResponse, TechVolunteerTutorUpdate,
)
from ...services import tech_booking_service
from .dependencies import get_current_user, require_staff
from app.api.v1.dependencies import is_staff_or_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/tech-booking", tags=["staff-tech-booking"])


# ============================================================================
# Staff Expertise Management
# ============================================================================

@router.post("/staff", response_model=TechAssistanceStaffResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def register_staff_expertise(
    request: Request,
    staff_data: TechAssistanceStaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Register or update staff expertise for tech assistance."""
    # Check if staff expertise already exists
    result = await db.execute(
        select(TechAssistanceStaff).where(TechAssistanceStaff.staff_id == current_user.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        existing.expertise_topics = staff_data.expertise_topics
        existing.max_concurrent_sessions = staff_data.max_concurrent_sessions
        existing.bio = staff_data.bio
        existing.languages = staff_data.languages
        existing.is_volunteer_coordinator = staff_data.is_volunteer_coordinator
        await db.commit()
        await db.refresh(existing)
        return TechAssistanceStaffResponse.model_validate(existing)

    # Create new
    staff_expertise = TechAssistanceStaff(
        staff_id=current_user.id,
        expertise_topics=staff_data.expertise_topics,
        max_concurrent_sessions=staff_data.max_concurrent_sessions,
        bio=staff_data.bio,
        languages=staff_data.languages,
        is_volunteer_coordinator=staff_data.is_volunteer_coordinator,
    )

    db.add(staff_expertise)
    await db.commit()
    await db.refresh(staff_expertise)

    return TechAssistanceStaffResponse.model_validate(staff_expertise)


@router.get("/staff/me", response_model=TechAssistanceStaffResponse)
@limiter.limit("60/minute")
async def get_my_expertise(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get current staff member's tech expertise."""
    result = await db.execute(
        select(TechAssistanceStaff).where(TechAssistanceStaff.staff_id == current_user.id)
    )
    expertise = result.scalar_one_or_none()

    if not expertise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not registered tech expertise yet",
        )

    return TechAssistanceStaffResponse.model_validate(expertise)


@router.patch("/staff/{staff_id}", response_model=TechAssistanceStaffResponse)
@limiter.limit("20/minute")
async def update_staff_expertise(
    request: Request,
    staff_id: int,
    update_data: TechAssistanceStaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update staff expertise."""
    result = await db.execute(
        select(TechAssistanceStaff).where(TechAssistanceStaff.id == staff_id)
    )
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff expertise not found",
        )

    # Only allow staff to update their own, or admins to update anyone
    if staff.staff_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Update fields
    if update_data.expertise_topics:
        staff.expertise_topics = update_data.expertise_topics
    if update_data.max_concurrent_sessions is not None:
        staff.max_concurrent_sessions = update_data.max_concurrent_sessions
    if update_data.bio is not None:
        staff.bio = update_data.bio
    if update_data.languages is not None:
        staff.languages = update_data.languages
    if update_data.is_volunteer_coordinator is not None:
        staff.is_volunteer_coordinator = update_data.is_volunteer_coordinator
    if update_data.is_active is not None:
        staff.is_active = update_data.is_active

    await db.commit()
    await db.refresh(staff)

    return TechAssistanceStaffResponse.model_validate(staff)


# ============================================================================
# Booking Management
# ============================================================================

@router.get("/bookings", response_model=list[BookingDetailResponse])
@limiter.limit("60/minute")
async def list_all_bookings(
    request: Request,
    status_filter: str | None = Query(None, description="Filter by status"),
    topic: str | None = Query(None, description="Filter by topic"),
    staff_id: int | None = Query(None, description="Filter by assigned staff"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all tech assistance bookings (staff only)."""
    query = select(TechAssistanceBooking)

    if status_filter:
        query = query.where(TechAssistanceBooking.status == status_filter)

    if topic:
        query = query.where(TechAssistanceBooking.topic == topic)

    if staff_id:
        query = query.where(TechAssistanceBooking.assigned_staff_id == staff_id)

    if start_date:
        query = query.where(TechAssistanceBooking.start_time >= start_date)

    if end_date:
        query = query.where(TechAssistanceBooking.start_time <= end_date)

    result = await db.execute(query.order_by(TechAssistanceBooking.start_time.desc()))
    bookings = result.scalars().all()

    return [BookingDetailResponse.model_validate(b) for b in bookings]


@router.get("/my-bookings", response_model=list[BookingDetailResponse])
@limiter.limit("60/minute")
async def list_my_assigned_bookings(
    request: Request,
    status_filter: str | None = Query(None, description="Filter by status"),
    date: datetime | None = Query(None, description="Filter by date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List tech bookings assigned to current staff member."""
    # Get staff expertise record
    result = await db.execute(
        select(TechAssistanceStaff).where(TechAssistanceStaff.staff_id == current_user.id)
    )
    staff = result.scalar_one_or_none()

    if not staff:
        return []

    query = select(TechAssistanceBooking).where(
        TechAssistanceBooking.assigned_staff_id == staff.id
    )

    if status_filter:
        query = query.where(TechAssistanceBooking.status == status_filter)

    if date:
        # Filter by date (ignoring time)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        query = query.where(
            and_(
                TechAssistanceBooking.start_time >= date_start,
                TechAssistanceBooking.start_time < date_end,
            )
        )

    result = await db.execute(query.order_by(TechAssistanceBooking.start_time))
    bookings = result.scalars().all()

    return [BookingDetailResponse.model_validate(b) for b in bookings]


@router.patch("/bookings/{booking_id}", response_model=TechAssistanceBookingResponse)
@limiter.limit("20/minute")
async def assign_staff_to_booking(
    request: Request,
    booking_id: int,
    assignment_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Assign a staff member to a booking or update booking status."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    staff_id = assignment_data.get("staff_id")
    new_status = assignment_data.get("status")

    # Assign staff if specified
    if staff_id:
        # Check availability
        is_available = await tech_booking_service.check_staff_availability(
            db, staff_id, booking.start_time, booking.end_time, booking.id
        )

        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff member is not available during this time",
            )

        booking.assigned_staff_id = staff_id
        booking.status = BookingStatus.confirmed

    # Update status if specified
    if new_status:
        try:
            booking.status = BookingStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}",
            ) from None

    await db.commit()
    await db.refresh(booking)

    return TechAssistanceBookingResponse.model_validate(booking)


# ============================================================================
# Resource Handouts
# ============================================================================

@router.post("/bookings/{booking_id}/resources", response_model=TechResourceHandoutResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def add_resource_handout(
    request: Request,
    booking_id: int,
    resource_data: TechResourceHandoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Add a resource handout to a booking."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    resource = TechResourceHandout(
        booking_id=booking_id,
        title=resource_data.title,
        description=resource_data.description,
        resource_url=resource_data.resource_url,
        file_path=resource_data.file_path,
        resource_type=resource_data.resource_type,
        topics=resource_data.topics,
    )

    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return TechResourceHandoutResponse.model_validate(resource)


@router.post("/bookings/{booking_id}/send-resources", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def send_resources_to_patron(
    request: Request,
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Send all resource handouts to patron."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Get all resources
    resources_result = await db.execute(
        select(TechResourceHandout).where(TechResourceHandout.booking_id == booking_id)
    )
    resources = list(resources_result.scalars().all())

    if not resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resources to send",
        )

    # Send resources
    success = await tech_booking_service.send_handout_materials(db, booking, resources)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send resources",
        )

    return {"message": "Resources sent successfully"}


# ============================================================================
# Volunteer Tutor Management
# ============================================================================

@router.post("/volunteer-tutors", response_model=TechVolunteerTutorResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def register_volunteer_tutor(
    request: Request,
    tutor_data: TechVolunteerTutorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Register a new volunteer tutor."""
    tutor = TechVolunteerTutor(
        volunteer_id=tutor_data.expertise_topics[0],  # Should be volunteer_id passed separately
        expertise_topics=tutor_data.expertise_topics,
        phone=tutor_data.phone,
        email=tutor_data.email,
        background=tutor_data.background,
        has_background_check=tutor_data.has_background_check,
        training_completed=tutor_data.training_completed,
        approval_status="pending",
    )

    db.add(tutor)
    await db.commit()
    await db.refresh(tutor)

    return TechVolunteerTutorResponse.model_validate(tutor)


@router.get("/volunteer-tutors", response_model=list[TechVolunteerTutorResponse])
@limiter.limit("60/minute")
async def list_volunteer_tutors(
    request: Request,
    status_filter: str | None = Query(None, description="Filter by approval status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List volunteer tutors (staff only)."""
    query = select(TechVolunteerTutor)

    if status_filter:
        query = query.where(TechVolunteerTutor.approval_status == status_filter)

    result = await db.execute(query)
    tutors = result.scalars().all()

    return [TechVolunteerTutorResponse.model_validate(t) for t in tutors]


@router.patch("/volunteer-tutors/{tutor_id}", response_model=TechVolunteerTutorResponse)
@limiter.limit("20/minute")
async def update_volunteer_tutor(
    request: Request,
    tutor_id: int,
    update_data: TechVolunteerTutorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update volunteer tutor information or approval status."""
    result = await db.execute(
        select(TechVolunteerTutor).where(TechVolunteerTutor.id == tutor_id)
    )
    tutor = result.scalar_one_or_none()

    if not tutor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutor not found",
        )

    # Update fields
    if update_data.expertise_topics:
        tutor.expertise_topics = update_data.expertise_topics
    if update_data.phone is not None:
        tutor.phone = update_data.phone
    if update_data.email is not None:
        tutor.email = update_data.email
    if update_data.background is not None:
        tutor.background = update_data.background
    if update_data.has_background_check is not None:
        tutor.has_background_check = update_data.has_background_check
    if update_data.training_completed is not None:
        tutor.training_completed = update_data.training_completed
    if update_data.is_active is not None:
        tutor.is_active = update_data.is_active

    await db.commit()
    await db.refresh(tutor)

    return TechVolunteerTutorResponse.model_validate(tutor)


@router.post("/volunteer-tutors/{tutor_id}/approve")
@limiter.limit("20/minute")
async def approve_volunteer_tutor(
    request: Request,
    tutor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Approve a volunteer tutor."""
    result = await db.execute(
        select(TechVolunteerTutor).where(TechVolunteerTutor.id == tutor_id)
    )
    tutor = result.scalar_one_or_none()

    if not tutor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutor not found",
        )

    tutor.approval_status = "approved"
    tutor.approved_by = current_user.id
    tutor.approved_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Tutor approved successfully"}


# ============================================================================
# Complete Session (with notes, impact, follow-up, auto-send resources)
# ============================================================================

@router.post("/bookings/{booking_id}/complete", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def complete_session(
    request: Request,
    booking_id: int,
    session_data: CompleteSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Complete a tech assistance session with all wrap-up actions.

    Handles session notes, impact tracking, follow-up scheduling,
    and auto-sending resource handouts in a single request.
    """
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.status == BookingStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already completed",
        )

    completion_result = await tech_booking_service.complete_session(
        db,
        booking,
        notes_data=session_data.notes.model_dump() if session_data.notes else None,
        impact_data=session_data.impact.model_dump() if session_data.impact else None,
        follow_up_needed=session_data.follow_up_needed,
        follow_up_topics=session_data.follow_up_topics,
        follow_up_reason=session_data.follow_up_reason,
        follow_up_timing=session_data.follow_up_timing,
        resource_ids_to_send=session_data.resource_ids_to_send,
        completed_by=current_user.id,
    )

    return {"message": "Session completed successfully", **completion_result}


# ============================================================================
# Follow-Up Scheduling (staff-initiated)
# ============================================================================

@router.post("/bookings/{booking_id}/follow-up", response_model=TechFollowUpBookingResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_follow_up(
    request: Request,
    booking_id: int,
    follow_up_data: TechFollowUpBookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Schedule a follow-up session for a completed booking."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    follow_up = await tech_booking_service.schedule_follow_up(
        db,
        booking_id,
        suggested_topics=follow_up_data.suggested_topics,
        reason=follow_up_data.reason,
        suggested_timing=follow_up_data.suggested_timing,
    )

    return TechFollowUpBookingResponse.model_validate(follow_up)


# ============================================================================
# Patron Impact Summary (staff view)
# ============================================================================

@router.get("/patron/{patron_id}/impact", response_model=ImpactSummaryResponse)
@limiter.limit("60/minute")
async def get_patron_impact(
    request: Request,
    patron_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get a patron's skill impact summary (staff view for continuity)."""
    impact = await tech_booking_service.get_impact_summary(db, patron_id)
    return ImpactSummaryResponse(**impact)


# ============================================================================
# Patron History (staff view for session continuity)
# ============================================================================

@router.get("/patron/{patron_id}/history", response_model=list[BookingDetailResponse])
@limiter.limit("60/minute")
async def get_patron_history(
    request: Request,
    patron_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get a patron's booking history for session continuity."""
    bookings = await tech_booking_service.get_patron_booking_history(
        db, patron_id, limit=20
    )

    detail_responses = []
    for b in bookings:
        await db.refresh(b, ["session_notes", "resources", "follow_ups", "impact_tracking", "assigned_staff"])
        detail_responses.append(BookingDetailResponse.model_validate(b))

    return detail_responses


# ============================================================================
# No-Show Detection
# ============================================================================

@router.post("/admin/mark-no-shows")
@limiter.limit("10/minute")
async def trigger_no_show_detection(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually trigger no-show detection for past bookings."""
    count = await tech_booking_service.mark_no_shows(db)
    return {"message": f"Marked {count} booking(s) as no-show", "count": count}


# ============================================================================
# Appointment Reminders
# ============================================================================

@router.post("/admin/send-reminders")
@limiter.limit("10/minute")
async def trigger_reminders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually trigger appointment reminders for upcoming sessions."""
    upcoming = await tech_booking_service.get_upcoming_appointments_for_reminders(db)
    sent_count = 0
    for booking in upcoming:
        success = await tech_booking_service.send_appointment_reminder(db, booking)
        if success:
            sent_count += 1

    return {"message": f"Sent {sent_count} reminder(s)", "count": sent_count}


# ============================================================================
# Statistics and Reporting
# ============================================================================

@router.get("/stats/staff-workload", response_model=dict)
@limiter.limit("60/minute")
async def get_staff_workload(
    request: Request,
    staff_id: int | None = Query(None, description="Staff ID (current user if not specified)"),
    start_date: datetime | None = Query(None, description="Start date"),
    end_date: datetime | None = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get staff workload statistics."""
    if not staff_id:
        result = await db.execute(
            select(TechAssistanceStaff).where(TechAssistanceStaff.staff_id == current_user.id)
        )
        staff = result.scalar_one_or_none()
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff expertise not found",
            )
        staff_id = staff.id

    # Default to last 30 days
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)

    workload = await tech_booking_service.get_staff_workload(
        db, staff_id, start_date, end_date
    )

    return workload
