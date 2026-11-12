# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public technology assistance booking routes."""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.tech_booking import (
    BookingStatus, TechFollowUpStatus, TechAssistanceBooking, TechTopic,
    TechVolunteerTutor, SkillLevel, TechFollowUpBooking,
    TechResourceHandout, TechSessionNote, TechSkillImpact,
)
from ...models.user import User
from ...schemas.tech_booking import (
    AvailabilityResponse, AvailabilitySlot,
    BookingDetailResponse, CancelBookingRequest,
    ImpactSummaryResponse, PatronBookingHistoryResponse,
    TechAssistanceBookingCreate,
    TechAssistanceBookingListResponse, TechAssistanceBookingResponse,
    TechAssistanceBookingUpdate, TechFollowUpBookingResponse,
    TechResourceHandoutResponse,
    TechSessionNoteResponse, TechSkillImpactResponse,
    TechVolunteerTutorResponse,
)
from ...services import tech_booking_service
from .auth import get_current_user, get_current_user_optional

logger = get_logger(__name__)

router = APIRouter(prefix="/tech-booking", tags=["tech-booking"])


# ============================================================================
# Topic and Availability Browsing
# ============================================================================

@router.get("/topics", response_model=list[dict])
@limiter.limit("60/minute")
async def list_tech_topics(request: Request):
    """Get all available technology topics."""
    topics = [
        {
            "value": TechTopic.email.value,
            "name": "Email",
            "description": "Email setup, sending/receiving, managing contacts",
        },
        {
            "value": TechTopic.smartphone.value,
            "name": "Smartphone",
            "description": "iPhone, Android basics, apps, settings",
        },
        {
            "value": TechTopic.tablet.value,
            "name": "Tablet",
            "description": "iPad, Android tablets, usage tips",
        },
        {
            "value": TechTopic.computer_basics.value,
            "name": "Computer Basics",
            "description": "Windows, Mac, file management, basic operations",
        },
        {
            "value": TechTopic.internet_browsing.value,
            "name": "Internet Browsing",
            "description": "Web browsers, searching, bookmarks, security",
        },
        {
            "value": TechTopic.social_media.value,
            "name": "Social Media",
            "description": "Facebook, Twitter, Instagram, LinkedIn basics",
        },
        {
            "value": TechTopic.password_management.value,
            "name": "Password Management",
            "description": "Creating secure passwords, password managers",
        },
        {
            "value": TechTopic.online_safety.value,
            "name": "Online Safety",
            "description": "Avoiding scams, protecting personal information",
        },
        {
            "value": TechTopic.resume_building.value,
            "name": "Resume Building",
            "description": "Creating and formatting resumes online",
        },
        {
            "value": TechTopic.job_search_online.value,
            "name": "Job Search Online",
            "description": "Job boards, LinkedIn, applications",
        },
        {
            "value": TechTopic.cloud_storage.value,
            "name": "Cloud Storage",
            "description": "Google Drive, OneDrive, Dropbox basics",
        },
        {
            "value": TechTopic.video_conferencing.value,
            "name": "Video Conferencing",
            "description": "Zoom, Google Meet, Teams setup and usage",
        },
        {
            "value": TechTopic.library_website.value,
            "name": "Library Website",
            "description": "Accessing library resources, digital collections",
        },
        {
            "value": TechTopic.digital_resources.value,
            "name": "Digital Resources",
            "description": "E-books, databases, streaming services",
        },
        {
            "value": TechTopic.accessibility_features.value,
            "name": "Accessibility Features",
            "description": "Screen readers, magnification, voice control",
        },
        {
            "value": TechTopic.other.value,
            "name": "Other",
            "description": "Other technology topics",
        },
    ]
    return topics


@router.get("/skill-levels", response_model=list[dict])
@limiter.limit("60/minute")
async def list_skill_levels(request: Request):
    """Get available skill level options."""
    return [
        {
            "value": SkillLevel.beginner.value,
            "name": "Beginner",
            "description": "New to this technology",
        },
        {
            "value": SkillLevel.intermediate.value,
            "name": "Intermediate",
            "description": "Some experience, want to improve",
        },
        {
            "value": SkillLevel.advanced.value,
            "name": "Advanced",
            "description": "Confident, looking to learn advanced features",
        },
    ]


@router.get("/volunteer-tutors", response_model=list[TechVolunteerTutorResponse])
@limiter.limit("60/minute")
async def list_volunteer_tutors(
    request: Request,
    topic: str | None = Query(None, description="Filter by topic"),
    db: AsyncSession = Depends(get_db),
):
    """Get available volunteer tutors."""
    query = select(TechVolunteerTutor).where(
        TechVolunteerTutor.is_active == True,
        TechVolunteerTutor.approval_status == "approved",
    )

    if topic:
        query = query.where(TechVolunteerTutor.expertise_topics.any(topic))

    result = await db.execute(query.order_by(TechVolunteerTutor.average_rating.desc()))
    tutors = result.scalars().all()

    return [TechVolunteerTutorResponse.model_validate(t) for t in tutors]


# ============================================================================
# Booking Management
# ============================================================================

@router.post("", response_model=TechAssistanceBookingResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_booking(  # noqa: role-check -- public tech assistance booking, rate-limited
    request: Request,
    booking_data: TechAssistanceBookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Create a new technology assistance booking.

    Patrons can book one-on-one tech help sessions with customizable topics
    and skill levels. Confirmation email will be sent automatically.
    """
    # Validate booking rules
    errors = await tech_booking_service.validate_booking_rules(
        db, booking_data.start_time, booking_data.end_time, current_user
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )

    # Try to match staff by expertise
    assigned_staff = await tech_booking_service.match_staff_by_expertise(
        db, booking_data.topic, booking_data.preferred_staff_id
    )

    # Create booking
    booking = TechAssistanceBooking(
        patron_id=current_user.id if current_user else None,
        start_time=booking_data.start_time,
        end_time=booking_data.end_time,
        topic=booking_data.topic,
        skill_level=booking_data.skill_level,
        description=booking_data.description,
        contact_name=booking_data.contact_name or (current_user.full_name if current_user else None),
        contact_email=booking_data.contact_email or (current_user.email if current_user else None),
        contact_phone=booking_data.contact_phone,
        preferred_staff_id=booking_data.preferred_staff_id,
        assigned_staff_id=assigned_staff.id if assigned_staff else None,
        status=BookingStatus.confirmed if assigned_staff else BookingStatus.pending,
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    # Send confirmation email
    await tech_booking_service.send_booking_confirmation(db, booking)

    return TechAssistanceBookingResponse.model_validate(booking)


@router.get("", response_model=list[TechAssistanceBookingListResponse])
@limiter.limit("60/minute")
async def list_my_bookings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's tech assistance bookings."""
    result = await db.execute(
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.patron_id == current_user.id)
        .order_by(TechAssistanceBooking.start_time.desc())
    )
    bookings = result.scalars().all()

    return [TechAssistanceBookingListResponse.model_validate(b) for b in bookings]


@router.get("/history", response_model=PatronBookingHistoryResponse)
@limiter.limit("60/minute")
async def get_booking_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get patron's booking history with session notes for continuity.

    Returns all past bookings with their notes, resources, and impact data
    so staff can prepare for future sessions.
    """
    bookings = await tech_booking_service.get_patron_booking_history(
        db, current_user.id, limit=50
    )

    # Load related data for each booking
    detail_responses = []
    topics_covered = set()
    for b in bookings:
        await db.refresh(b, ["session_notes", "resources", "follow_ups", "impact_tracking", "assigned_staff"])
        detail_responses.append(BookingDetailResponse.model_validate(b))
        topics_covered.add(b.topic)

    # Get impact summary
    impact = await tech_booking_service.get_impact_summary(db, current_user.id)

    return PatronBookingHistoryResponse(
        bookings=detail_responses,
        total_sessions=len(bookings),
        topics_covered=list(topics_covered),
        impact_summary=ImpactSummaryResponse(**impact),
    )


# ============================================================================
# Impact Summary
# ============================================================================

@router.get("/impact-summary", response_model=ImpactSummaryResponse)
@limiter.limit("60/minute")
async def get_my_impact_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get patron's skill impact summary across all sessions."""
    impact = await tech_booking_service.get_impact_summary(db, current_user.id)
    return ImpactSummaryResponse(**impact)


# ============================================================================
# Availability
# ============================================================================

@router.get("/availability", response_model=AvailabilityResponse)
@limiter.limit("60/minute")
async def get_availability(
    request: Request,
    topic: str | None = Query(None, description="Filter by topic"),
    date_start: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """Get available time slots for tech assistance booking."""
    from datetime import datetime as dt

    start = None
    end = None
    if date_start:
        start = dt.fromisoformat(date_start + "T00:00:00+00:00")
    if date_end:
        end = dt.fromisoformat(date_end + "T23:59:59+00:00")

    slots = await tech_booking_service.get_available_slots(
        db, topic=topic, date_start=start, date_end=end
    )

    return AvailabilityResponse(
        slots=[AvailabilitySlot(**s) for s in slots],
        topic=topic,
        date_range_start=date_start or "",
        date_range_end=date_end or "",
    )


@router.get("/{booking_id}", response_model=BookingDetailResponse)
@limiter.limit("60/minute")
async def get_booking_details(
    request: Request,
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get details of a specific booking."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Check authorization (patron can view their own bookings)
    if current_user and booking.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this booking",
        )

    # Load related data
    await db.refresh(booking, ["session_notes", "resources", "follow_ups", "impact_tracking", "assigned_staff"])

    return BookingDetailResponse.model_validate(booking)


@router.patch("/{booking_id}", response_model=TechAssistanceBookingResponse)
@limiter.limit("20/minute")
async def update_booking(
    request: Request,
    booking_id: int,
    update_data: TechAssistanceBookingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a booking (reschedule/cancel)."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Authorization check
    if booking.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this booking",
        )

    # Validate status change
    if update_data.status == BookingStatus.cancelled.value:
        if booking.status in [BookingStatus.completed, BookingStatus.no_show]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a completed or no-show booking",
            )
        booking.cancelled_at = datetime.now(timezone.utc)
        booking.cancelled_by = current_user.id
        booking.cancellation_reason = "Cancelled by patron"

    # Update fields
    if update_data.start_time:
        errors = await tech_booking_service.validate_booking_rules(
            db, update_data.start_time, update_data.end_time or booking.end_time
        )
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": errors},
            )
        booking.start_time = update_data.start_time
        booking.status = BookingStatus.rescheduled

    if update_data.end_time:
        booking.end_time = update_data.end_time

    if update_data.description is not None:
        booking.description = update_data.description

    await db.commit()
    await db.refresh(booking)

    return TechAssistanceBookingResponse.model_validate(booking)


@router.post("/{booking_id}/check-in")
@limiter.limit("20/minute")
async def check_in(
    request: Request,
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check in for a tech assistance session."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    if booking.status not in [BookingStatus.confirmed, BookingStatus.pending]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check in for this booking",
        )

    booking.checked_in_at = datetime.now(timezone.utc)
    booking.status = BookingStatus.in_progress
    await db.commit()

    return {"message": "Checked in successfully", "booking_id": booking.id}


@router.post("/{booking_id}/session-notes", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def add_session_notes(
    request: Request,
    booking_id: int,
    notes_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add session notes after a tech help session (staff only)."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Create notes
    note = TechSessionNote(
        booking_id=booking_id,
        content=notes_data.get("content"),
        topics_covered=notes_data.get("topics_covered", []),
        concepts_taught=notes_data.get("concepts_taught", []),
        patron_comprehension_level=notes_data.get("patron_comprehension_level"),
        recommendations=notes_data.get("recommendations"),
        challenges=notes_data.get("challenges"),
        created_by=current_user.id,
    )

    db.add(note)

    # Mark session as completed
    booking.status = BookingStatus.completed
    booking.session_end_actual = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(note)

    return TechSessionNoteResponse.model_validate(note)


@router.post("/{booking_id}/impact-tracking", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def record_impact(
    request: Request,
    booking_id: int,
    impact_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record impact/outcomes for a completed session."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Create impact record
    impact = TechSkillImpact(
        booking_id=booking_id,
        skills_learned=impact_data.get("skills_learned", []),
        confidence_before=impact_data.get("confidence_before"),
        confidence_after=impact_data.get("confidence_after"),
        independence_level=impact_data.get("independence_level"),
        goal_achieved=impact_data.get("goal_achieved", False),
        satisfaction_rating=impact_data.get("satisfaction_rating"),
        patron_feedback=impact_data.get("patron_feedback"),
        interested_in_future_sessions=impact_data.get("interested_in_future_sessions", False),
        staff_recommendation=impact_data.get("staff_recommendation"),
    )

    db.add(impact)
    await db.commit()
    await db.refresh(impact)

    return TechSkillImpactResponse.model_validate(impact)


# ============================================================================
# Cancel Booking
# ============================================================================

@router.post("/{booking_id}/cancel")
@limiter.limit("20/minute")
async def cancel_booking(
    request: Request,
    booking_id: int,
    cancel_data: CancelBookingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a tech assistance booking."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this booking",
        )

    if booking.status in [BookingStatus.completed, BookingStatus.no_show, BookingStatus.cancelled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a booking with status: {booking.status}",
        )

    booking.status = BookingStatus.cancelled
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancelled_by = current_user.id
    booking.cancellation_reason = cancel_data.reason or "Cancelled by patron"

    await db.commit()

    return {"message": "Booking cancelled successfully", "booking_id": booking.id}


# ============================================================================
# Follow-Up Acceptance
# ============================================================================

@router.post("/{booking_id}/follow-up/{follow_up_id}/accept")
@limiter.limit("20/minute")
async def accept_follow_up(
    request: Request,
    booking_id: int,
    follow_up_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a follow-up session recommendation."""
    # Verify booking belongs to patron
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Get follow-up record
    result = await db.execute(
        select(TechFollowUpBooking).where(
            TechFollowUpBooking.id == follow_up_id,
            TechFollowUpBooking.original_booking_id == booking_id,
        )
    )
    follow_up = result.scalar_one_or_none()

    if not follow_up:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )

    follow_up.patron_agreed = True
    follow_up.patron_agreed_at = datetime.now(timezone.utc)
    follow_up.status = TechFollowUpStatus.scheduled

    await db.commit()

    return {
        "message": "Follow-up accepted",
        "follow_up_id": follow_up.id,
        "suggested_timing": follow_up.suggested_timing,
    }


@router.post("/{booking_id}/follow-up/{follow_up_id}/decline")
@limiter.limit("20/minute")
async def decline_follow_up(
    request: Request,
    booking_id: int,
    follow_up_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decline a follow-up session recommendation."""
    result = await db.execute(
        select(TechAssistanceBooking).where(TechAssistanceBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    result = await db.execute(
        select(TechFollowUpBooking).where(
            TechFollowUpBooking.id == follow_up_id,
            TechFollowUpBooking.original_booking_id == booking_id,
        )
    )
    follow_up = result.scalar_one_or_none()

    if not follow_up:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )

    follow_up.patron_agreed = False
    follow_up.status = TechFollowUpStatus.declined

    await db.commit()

    return {"message": "Follow-up declined", "follow_up_id": follow_up.id}
