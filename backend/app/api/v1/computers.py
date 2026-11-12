# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for public computer management."""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc

from ...core.database import get_db
from .dependencies import get_current_user
from ...models.computer import (
    Computer,
    ComputerReservation,
    ComputerSession,
    ComputerWaitlist,
    GuestPass,
    SessionExtensionRequest,
    ComputerUsageStats,
    ComputerType,
    ComputerStatus,
    ComputerReservationStatus,
    ComputerWaitlistStatus,
    ExtensionStatus,
)
from ...models.user import User, UserRole

_STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN)
from ...services import computer_service
from ...services import session_manager
from ...services import floor_view_bus
from ...schemas.computer import (
    ComputerResponse,
    ComputerListResponse,
    ReservationCreateRequest,
    ReservationResponse,
    SessionResponse,
    GuestPassResponse,
    ExtensionRequestResponse,
    UsageStatsResponse,
    StaffEndSessionRequest,
    StaffBulkActionRequest,
    StaffBulkActionResponse,
    StaffBulkActionResultItem,
    LabMapStation,
    LabMapResponse,
)
from ...schemas.computer_booking import (
    StationResponse,
    StationListResponse,
    AvailabilitySlot,
    AvailabilityResponse,
    ComputerAvailability,
    RangeAvailabilityResponse,
    ReservationCreateRequest as BookingReservationCreateRequest,
    ReservationResponse as BookingReservationResponse,
    ReservationListResponse,
    SessionStartRequest,
    SessionExtendRequest,
    StaffReservationUpdateRequest,
    StaffExtendRequest,
    SessionResponse as BookingSessionResponse,
)
from .computer_guest_routes import router as computer_guest_router
from .computer_waitlist_routes import router as computer_waitlist_router

logger = get_logger(__name__)
router = APIRouter(prefix="/computers", tags=["computers"])


# Computer Management Endpoints


@router.get("/lab-map", response_model=LabMapResponse)
async def get_lab_map(db: AsyncSession = Depends(get_db)) -> LabMapResponse:
    """Public lab-map: mapped stations with status and est. availability."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Computer)
        .where(Computer.is_active.is_(True))
        .order_by(Computer.computer_number.asc())
    )
    computers = result.scalars().all()

    CANONICAL_STATUSES = {"available", "in_use", "maintenance", "offline", "reserved"}
    end_expr = sqlfunc.coalesce(
        ComputerReservation.extended_until,
        ComputerReservation.reserved_end_time,
    )

    stations: list[LabMapStation] = []
    for c in computers:
        available_at = None
        if c.status in (ComputerStatus.in_use, ComputerStatus.reserved):
            res_q = (
                select(end_expr.label("effective_end"))
                .where(ComputerReservation.computer_id == c.id)
                .where(
                    ComputerReservation.status.in_(
                        [
                            ComputerReservationStatus.in_session,
                            ComputerReservationStatus.confirmed,
                            ComputerReservationStatus.pending,
                        ]
                    )
                )
                .where(end_expr > now)
                .order_by(end_expr.asc())
                .limit(1)
            )
            row = (await db.execute(res_q)).first()
            if row is not None:
                available_at = row.effective_end
        raw_status = c.status.value if hasattr(c.status, "value") else c.status
        safe_status = raw_status if raw_status in CANONICAL_STATUSES else "offline"
        stations.append(
            LabMapStation(
                id=c.id,
                name=c.name,
                computer_number=c.computer_number,
                location=c.location,
                computer_type=c.computer_type.value
                if hasattr(c.computer_type, "value")
                else c.computer_type,
                status=safe_status,
                map_x=c.map_x,
                map_y=c.map_y,
                map_floor=c.map_floor,
                available_at=available_at,
            )
        )
    return LabMapResponse(stations=stations, generated_at=now)


@router.get("", response_model=ComputerListResponse)
async def list_computers(
    db: AsyncSession = Depends(get_db),
    computer_type: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> ComputerListResponse:
    """List available public computers with optional filtering."""
    from sqlalchemy import select

    query = select(Computer)

    if is_active is not None:
        query = query.where(Computer.is_active == is_active)

    if computer_type:
        query = query.where(Computer.computer_type == computer_type)

    if branch_id:
        query = query.where(Computer.branch_id == branch_id)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    computers = list(result.scalars())

    total_count_result = await db.execute(select(sqlfunc.count(Computer.id)))
    total_count = total_count_result.scalar() or 0

    return ComputerListResponse(
        total=total_count,
        skip=skip,
        limit=limit,
        items=[ComputerResponse.model_validate(c) for c in computers],
    )


@router.get("/available")
async def get_available_computers(
    start_time: datetime = Query(...),
    duration_minutes: int = Query(..., gt=0),
    computer_type: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get list of available computers for a given time slot."""
    computers = await computer_service.get_available_computers(
        db, start_time, duration_minutes, computer_type, branch_id
    )

    return {
        "available_count": len(computers),
        "computers": [ComputerResponse.model_validate(c) for c in computers],
    }


# Reservation Endpoints


@router.post("/reservations", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    request: ReservationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ReservationResponse:
    """Create a new computer reservation."""
    # Determine patron ID based on authentication
    patron_id = current_user.id if current_user else None

    # For guest passes, need at least a name
    if request.is_guest_pass and not request.guest_name:
        raise HTTPException(
            status_code=400, detail="Guest name required for guest pass reservations"
        )

    reservation = await computer_service.create_reservation(
        db,
        computer_id=request.computer_id,
        patron_id=patron_id,
        start_time=request.start_time,
        duration_minutes=request.duration_minutes,
        is_guest_pass=request.is_guest_pass,
        guest_name=request.guest_name,
        guest_email=request.guest_email,
        guest_phone=request.guest_phone,
    )

    if not reservation:
        raise HTTPException(status_code=409, detail="Computer not available for requested time")

    await db.commit()
    return ReservationResponse.model_validate(reservation)


@router.post("/reservations/book", response_model=BookingReservationResponse, status_code=201)
async def book_reservation(
    request: BookingReservationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingReservationResponse:
    """Book a computer reservation ahead of time."""
    reservation = await computer_service.create_reservation(
        db,
        computer_id=request.computer_id,
        patron_id=current_user.id,
        start_time=request.start_time,
        duration_minutes=request.duration_minutes,
    )

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Computer not available for requested time"
        )

    await db.commit()
    return BookingReservationResponse.model_validate(reservation)


@router.get("/reservations/mine", response_model=ReservationListResponse)
async def list_my_reservations(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationListResponse:
    """Get the current patron's computer reservations."""
    from sqlalchemy import select, func as sqlfunc

    query = select(ComputerReservation).where(ComputerReservation.patron_id == current_user.id)

    if status_filter:
        query = query.where(ComputerReservation.status == status_filter)

    count_query = select(sqlfunc.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ComputerReservation.reserved_start_time.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    reservations = list(result.scalars())

    return ReservationListResponse(
        items=[BookingReservationResponse.model_validate(r) for r in reservations],
        total=total,
    )


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationResponse:
    """Get details for a specific reservation."""
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Check access
    if reservation.patron_id != current_user.id and not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    return ReservationResponse.model_validate(reservation)


@router.post(
    "/reservations/{reservation_id}/check-in", response_model=SessionResponse, status_code=201
)
async def check_in(  # noqa: role-check -- public computer reservation check-in via guest-pass-code
    reservation_id: int,
    guest_pass_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Check in for a reservation and start a session."""
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    session = await computer_service.check_in_reservation(db, reservation_id, guest_pass_code)

    if not session:
        raise HTTPException(status_code=400, detail="Invalid guest pass code or reservation status")

    await db.commit()
    await floor_view_bus.publish(
        "session_started",
        computer_id=reservation.computer_id,
        reservation_id=reservation_id,
    )
    return SessionResponse.model_validate(session)


@router.post("/reservations/{reservation_id}/cancel", response_model=dict)
async def cancel_reservation(
    reservation_id: int,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel a reservation."""
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Check access
    if reservation.patron_id != current_user.id and not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    reservation.status = ComputerReservationStatus.cancelled
    reservation.cancelled_by = current_user.id
    reservation.cancellation_reason = reason or "User cancelled"

    await db.commit()

    return {"message": "Reservation cancelled successfully"}


# Session Endpoints (literal routes before parameterized)


@router.post("/sessions/start", response_model=BookingSessionResponse, status_code=201)
async def start_walk_in_session(
    request: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingSessionResponse:
    """Start a walk-in computer session (no prior reservation needed)."""
    reservation = await session_manager.start_session(
        db,
        patron_id=current_user.id,
        computer_id=request.computer_id,
        duration_minutes=request.duration_minutes,
    )

    now = datetime.now(timezone.utc)
    remaining = int((reservation.reserved_end_time - now).total_seconds() / 60)

    await floor_view_bus.publish(
        "session_started",
        computer_id=request.computer_id,
        reservation_id=reservation.id,
    )

    resp = BookingSessionResponse.model_validate(reservation)
    resp.minutes_remaining = max(remaining, 0)
    return resp


@router.get("/sessions/current", response_model=BookingSessionResponse)
async def get_current_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingSessionResponse:
    """Get the current patron's active computer session."""
    reservation = await session_manager.get_current_session(db, current_user.id)
    if not reservation:
        raise HTTPException(status_code=404, detail="No active session found")

    now = datetime.now(timezone.utc)
    remaining = int((reservation.reserved_end_time - now).total_seconds() / 60)

    resp = BookingSessionResponse.model_validate(reservation)
    resp.minutes_remaining = max(remaining, 0)
    return resp


@router.post("/sessions/extend", response_model=BookingSessionResponse)
async def extend_current_session(
    request: SessionExtendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingSessionResponse:
    """Extend the current patron's active session."""
    reservation = await session_manager.extend_session(
        db,
        patron_id=current_user.id,
        extra_minutes=request.extra_minutes,
    )

    now = datetime.now(timezone.utc)
    remaining = int((reservation.reserved_end_time - now).total_seconds() / 60)

    await floor_view_bus.publish(
        "session_extended",
        computer_id=reservation.computer_id,
        reservation_id=reservation.id,
        extra_minutes=request.extra_minutes,
    )

    resp = BookingSessionResponse.model_validate(reservation)
    resp.minutes_remaining = max(remaining, 0)
    return resp


@router.post("/sessions/end", response_model=BookingSessionResponse)
async def end_current_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingSessionResponse:
    """End the current patron's active session (logout)."""
    reservation = await session_manager.end_session(db, current_user.id)

    await floor_view_bus.publish(
        "session_ended",
        computer_id=reservation.computer_id,
        reservation_id=reservation.id,
        by_staff=False,
    )

    resp = BookingSessionResponse.model_validate(reservation)
    resp.minutes_remaining = 0
    return resp


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Get details for an active session."""
    session = await db.get(ComputerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: int,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """End an active session (logout)."""
    session = await db.get(ComputerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check access (patron or staff)
    if session.patron_id != current_user.id and not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    ended_session = await computer_service.end_session(db, session_id, reason or "user_logout")

    await db.commit()
    await floor_view_bus.publish(
        "session_ended",
        computer_id=ended_session.computer_id if ended_session else session.computer_id,
        reservation_id=session.reservation_id,
        by_staff=current_user.id != session.patron_id,
    )
    return SessionResponse.model_validate(ended_session)


# Session Extension Endpoints


@router.post(
    "/sessions/{session_id}/extend", response_model=ExtensionRequestResponse, status_code=201
)
async def request_extension(
    session_id: int,
    extension_minutes: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ExtensionRequestResponse:
    """Request to extend a computer session."""
    session = await db.get(ComputerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_active:
        raise HTTPException(status_code=400, detail="Cannot extend inactive session")

    extension_request = await computer_service.request_session_extension(
        db, session_id, extension_minutes
    )

    if not extension_request:
        raise HTTPException(status_code=400, detail="Extension not allowed or limit reached")

    await db.commit()
    await floor_view_bus.publish(
        "extension_requested",
        computer_id=session.computer_id,
        reservation_id=session.reservation_id,
        extension_id=extension_request.id,
    )
    return ExtensionRequestResponse.model_validate(extension_request)


@router.post("/extensions/{extension_id}/approve", response_model=ExtensionRequestResponse)
async def approve_extension(
    extension_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExtensionRequestResponse:
    """Approve a session extension request (staff only)."""
    if not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    extension_request = await db.get(SessionExtensionRequest, extension_id)
    if not extension_request:
        raise HTTPException(status_code=404, detail="Extension request not found")

    approved = await computer_service.approve_extension(db, extension_id, current_user.id)

    await db.commit()
    await floor_view_bus.publish(
        "extension_approved",
        reservation_id=extension_request.reservation_id,
        extension_id=extension_id,
    )
    return ExtensionRequestResponse.model_validate(approved)


# Guest Pass Endpoints

router.include_router(computer_guest_router)

# Usage Statistics Endpoints


@router.get("/computers/{computer_id}/stats", response_model=dict)
async def get_computer_stats(
    computer_id: int,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get usage statistics for a computer (staff only)."""
    if not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    from sqlalchemy import select
    from datetime import timedelta

    computer = await db.get(Computer, computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    # Get stats for the requested period
    date_from = datetime.now() - timedelta(days=days)

    query = (
        select(ComputerUsageStats)
        .where(ComputerUsageStats.computer_id == computer_id)
        .where(ComputerUsageStats.date >= date_from)
        .order_by(ComputerUsageStats.date.desc())
    )

    result = await db.execute(query)
    stats = list(result.scalars())

    return {
        "computer_id": computer_id,
        "computer_name": computer.name,
        "period_days": days,
        "stats": [UsageStatsResponse.model_validate(s) for s in stats],
    }


@router.get("/stats/system")
async def get_system_stats(
    days: int = Query(7, ge=1, le=90),
    branch_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get system-wide computer usage statistics (staff only)."""
    if not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    from sqlalchemy import select, func
    from datetime import timedelta

    date_from = datetime.now() - timedelta(days=days)

    # Get stats for all computers or filtered by branch
    query = select(ComputerUsageStats).where(ComputerUsageStats.date >= date_from)

    if branch_id:
        query = query.join(Computer).where(Computer.branch_id == branch_id)

    result = await db.execute(query)
    all_stats = list(result.scalars())

    # Aggregate statistics
    total_reservations = sum(s.total_reservations for s in all_stats)
    total_sessions = sum(s.completed_sessions for s in all_stats)
    total_minutes = sum(s.total_minutes_used for s in all_stats)
    guest_sessions = sum(s.guest_sessions for s in all_stats)
    cancellations = sum(s.cancelled_reservations for s in all_stats)
    no_shows = sum(s.no_show_count for s in all_stats)

    # Auto-event counts come from the system log so they're independent
    # of the daily-aggregate rollup cadence.
    from ...models.computer import ComputerSystemLog

    auto_q = (
        select(ComputerSystemLog.event_type, sqlfunc.count(ComputerSystemLog.id))
        .where(ComputerSystemLog.created_at >= date_from)
        .where(ComputerSystemLog.event_type.in_(["auto_no_show", "auto_logout"]))
        .group_by(ComputerSystemLog.event_type)
    )
    auto_result = await db.execute(auto_q)
    auto_counts = {row[0]: row[1] for row in auto_result}
    auto_no_shows = auto_counts.get("auto_no_show", 0)
    auto_logouts = auto_counts.get("auto_logout", 0)

    return {
        "period_days": days,
        "total_reservations": total_reservations,
        "total_completed_sessions": total_sessions,
        "total_minutes_used": total_minutes,
        "guest_sessions": guest_sessions,
        "cardholders_sessions": total_sessions - guest_sessions,
        "cancelled_reservations": cancellations,
        "no_show_count": no_shows,
        "auto_no_shows": auto_no_shows,
        "auto_logouts": auto_logouts,
        "average_session_minutes": total_minutes // total_sessions if total_sessions > 0 else 0,
    }


# =========================================================================
# Enhanced Booking Endpoints
# =========================================================================


@router.get("/stations", response_model=StationListResponse)
async def list_stations(
    computer_type: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> StationListResponse:
    """List computer stations with real-time availability status."""
    from sqlalchemy import select

    query = select(Computer).where(Computer.is_active == True)

    if computer_type:
        query = query.where(Computer.computer_type == computer_type)

    if branch_id:
        query = query.where(Computer.branch_id == branch_id)

    if status_filter:
        query = query.where(Computer.status == status_filter)

    result = await db.execute(query.order_by(Computer.name))
    computers = list(result.scalars())

    return StationListResponse(
        items=[StationResponse.model_validate(c) for c in computers],
        total=len(computers),
    )


async def _resolve_hours_for_date(db: AsyncSession, target_date, tz):
    """Resolve open/close for a date as tz-aware datetimes.

    LibraryHoursOverride wins for the specific date, otherwise the weekly
    LibraryHours schedule. Returns (is_closed, open_dt_local, close_dt_local);
    open/close are None when the library is closed that day.
    """
    from ...models.homepage_content import LibraryHours, LibraryHoursOverride

    open_time = None
    close_time = None
    is_closed = False

    override_q = await db.execute(
        select(LibraryHoursOverride).where(LibraryHoursOverride.date == target_date)
    )
    override = override_q.scalar_one_or_none()
    if override is not None:
        is_closed = override.is_closed
        open_time = override.open_time
        close_time = override.close_time
    else:
        # LibraryHours uses JS day-of-week: 0=Sun, 1=Mon, ..., 6=Sat.
        js_dow = (target_date.weekday() + 1) % 7
        hours_q = await db.execute(select(LibraryHours).where(LibraryHours.day_of_week == js_dow))
        hours = hours_q.scalar_one_or_none()
        if hours is None or hours.is_closed:
            is_closed = True
        else:
            open_time = hours.open_time
            close_time = hours.close_time

    if is_closed or open_time is None or close_time is None:
        return True, None, None

    open_dt_local = datetime.combine(target_date, open_time, tzinfo=tz)
    close_dt_local = datetime.combine(target_date, close_time, tzinfo=tz)
    return False, open_dt_local, close_dt_local


def _build_hourly_slots(open_dt_local, close_dt_local, reservations) -> List[AvailabilitySlot]:
    """Hourly free/busy slots between open and close; last slot ends at close."""
    slots: List[AvailabilitySlot] = []
    slot_start_local = open_dt_local
    while slot_start_local + timedelta(hours=1) <= close_dt_local:
        slot_end_local = slot_start_local + timedelta(hours=1)
        slot_start_utc = slot_start_local.astimezone(timezone.utc)
        slot_end_utc = slot_end_local.astimezone(timezone.utc)
        is_available = not any(
            r.reserved_start_time < slot_end_utc and r.reserved_end_time > slot_start_utc
            for r in reservations
        )
        slots.append(
            AvailabilitySlot(
                start_time=slot_start_utc,
                end_time=slot_end_utc,
                is_available=is_available,
            )
        )
        slot_start_local = slot_end_local
    return slots


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability_slots(
    computer_id: int = Query(...),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    """Get availability time slots for a computer on a given date.

    Slots are built from the library's hours of operation (LibraryHoursOverride
    for the specific date, otherwise the weekly LibraryHours schedule) and
    rendered in the configured library timezone (settings.library_timezone).
    """
    from zoneinfo import ZoneInfo
    from datetime import date as date_cls
    from ...core.config import get_settings

    computer = await db.get(Computer, computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    try:
        target_date = date_cls.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD") from None

    tz = ZoneInfo(get_settings().library_timezone)
    is_closed, open_dt_local, close_dt_local = await _resolve_hours_for_date(db, target_date, tz)
    if is_closed:
        return AvailabilityResponse(computer_id=computer_id, date=date, slots=[])

    day_start_local = datetime.combine(target_date, datetime.min.time(), tzinfo=tz)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = (day_start_local + timedelta(days=1)).astimezone(timezone.utc)

    result = await db.execute(
        select(ComputerReservation).where(
            ComputerReservation.computer_id == computer_id,
            ComputerReservation.status.in_(
                [
                    ComputerReservationStatus.confirmed,
                    ComputerReservationStatus.in_session,
                ]
            ),
            ComputerReservation.reserved_start_time < day_end_utc,
            ComputerReservation.reserved_end_time > day_start_utc,
        )
    )
    reservations = list(result.scalars())

    return AvailabilityResponse(
        computer_id=computer_id,
        date=date,
        slots=_build_hourly_slots(open_dt_local, close_dt_local, reservations),
    )


@router.get("/availability/range", response_model=RangeAvailabilityResponse)
async def get_availability_range(
    date: Optional[str] = Query(None, description="Start date YYYY-MM-DD, default today"),
    days: int = Query(1, ge=1, le=7, description="Number of days from the start date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RangeAvailabilityResponse:
    """Identity-free free/busy slots for every bookable computer over a date range.

    Powers the all-computers availability grid on the booking page. Carries no
    patron identity, only per-slot free/busy (same shape as /availability).
    Maintenance/offline computers are excluded since they cannot be booked.
    """
    from zoneinfo import ZoneInfo
    from datetime import date as date_cls
    from ...core.config import get_settings

    tz = ZoneInfo(get_settings().library_timezone)
    if date:
        try:
            start_date = date_cls.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format, use YYYY-MM-DD"
            ) from None
    else:
        start_date = datetime.now(tz).date()

    dates = [start_date + timedelta(days=i) for i in range(days)]
    window_start_utc = datetime.combine(dates[0], datetime.min.time(), tzinfo=tz).astimezone(
        timezone.utc
    )
    window_end_utc = (
        datetime.combine(dates[-1], datetime.min.time(), tzinfo=tz) + timedelta(days=1)
    ).astimezone(timezone.utc)

    comp_result = await db.execute(
        select(Computer)
        .where(Computer.is_active.is_(True))
        .where(Computer.status.notin_([ComputerStatus.maintenance, ComputerStatus.offline]))
        .order_by(Computer.computer_number.asc())
    )
    computers = list(comp_result.scalars())
    if not computers:
        return RangeAvailabilityResponse(start_date=start_date.isoformat(), days=days, computers=[])

    comp_ids = [c.id for c in computers]
    # One reservation query across the whole window; bucket per computer in
    # Python so this stays O(1) queries regardless of computer/day count.
    res_result = await db.execute(
        select(ComputerReservation).where(
            ComputerReservation.computer_id.in_(comp_ids),
            ComputerReservation.status.in_(
                [
                    ComputerReservationStatus.confirmed,
                    ComputerReservationStatus.in_session,
                ]
            ),
            ComputerReservation.reserved_start_time < window_end_utc,
            ComputerReservation.reserved_end_time > window_start_utc,
        )
    )
    by_computer: dict[int, list] = {cid: [] for cid in comp_ids}
    for r in res_result.scalars():
        by_computer[r.computer_id].append(r)

    # Resolve library hours once per date (shared across all computers).
    hours_by_date = {d: await _resolve_hours_for_date(db, d, tz) for d in dates}

    out: List[ComputerAvailability] = []
    for c in computers:
        slots: List[AvailabilitySlot] = []
        for d in dates:
            is_closed, open_dt_local, close_dt_local = hours_by_date[d]
            if is_closed:
                continue
            slots.extend(_build_hourly_slots(open_dt_local, close_dt_local, by_computer[c.id]))
        out.append(
            ComputerAvailability(
                computer_id=c.id,
                name=c.name,
                computer_number=c.computer_number,
                computer_type=c.computer_type.value
                if hasattr(c.computer_type, "value")
                else str(c.computer_type),
                max_session_minutes=c.max_session_minutes,
                slots=slots,
            )
        )

    return RangeAvailabilityResponse(start_date=start_date.isoformat(), days=days, computers=out)


@router.delete("/reservations/{reservation_id}", status_code=200)
async def delete_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel a reservation via DELETE."""
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.patron_id != current_user.id and not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    if reservation.status in (
        ComputerReservationStatus.completed,
        ComputerReservationStatus.cancelled,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation is already completed or cancelled",
        )

    reservation.status = ComputerReservationStatus.cancelled
    reservation.cancelled_by = current_user.id
    reservation.cancellation_reason = "Cancelled by patron"
    reservation.cancelled_at = datetime.now(timezone.utc)

    # Free up computer if it was reserved
    computer = await db.get(Computer, reservation.computer_id)
    if computer and computer.status == ComputerStatus.reserved:
        computer.status = ComputerStatus.available

    await db.commit()
    return {"message": "Reservation cancelled successfully", "reservation_id": reservation_id}


@router.post(
    "/reservations/{reservation_id}/check-in/walk-in", response_model=BookingReservationResponse
)
async def check_in_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingReservationResponse:
    """Check in for an existing reservation."""
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.patron_id != current_user.id and not current_user.role in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    if reservation.status != ComputerReservationStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in: reservation status is {reservation.status}",
        )

    now = datetime.now(timezone.utc)
    reservation.status = ComputerReservationStatus.in_session
    reservation.checked_in_at = now
    reservation.actual_start_time = now

    computer = await db.get(Computer, reservation.computer_id)
    if computer:
        computer.status = ComputerStatus.in_use

    await db.commit()
    await db.refresh(reservation)
    await floor_view_bus.publish(
        "session_started",
        computer_id=reservation.computer_id,
        reservation_id=reservation.id,
    )
    return BookingReservationResponse.model_validate(reservation)


# Enhanced Waitlist Endpoints (using waitlist_service)

router.include_router(computer_waitlist_router)

# ── Staff dashboard endpoints ────────────────────────────────────────


@router.get("/staff/floor-view")
async def staff_floor_view(
    branch_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get all computers with their current session info for staff floor view."""
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    from sqlalchemy.orm import selectinload

    query = select(Computer).where(Computer.is_active == True)
    if branch_id:
        query = query.where(Computer.branch_id == branch_id)
    query = query.order_by(Computer.name)

    result = await db.execute(query)
    computers = list(result.scalars())

    # Get all active reservations (in_session status)
    now = datetime.now(timezone.utc)
    active_q = select(ComputerReservation).where(
        ComputerReservation.status == ComputerReservationStatus.in_session
    )
    active_result = await db.execute(active_q)
    active_reservations = {r.computer_id: r for r in active_result.scalars()}

    # Get patron names for active sessions
    patron_ids = [r.patron_id for r in active_reservations.values() if r.patron_id]
    patron_names = {}
    if patron_ids:
        from ...models.user import User as UserModel

        patron_q = select(UserModel).where(UserModel.id.in_(patron_ids))
        patron_result = await db.execute(patron_q)
        patron_names = {u.id: u.full_name for u in patron_result.scalars()}

    # Get pending extension requests
    pending_ext_q = select(SessionExtensionRequest).where(
        SessionExtensionRequest.status == ExtensionStatus.pending
    )
    pending_ext_result = await db.execute(pending_ext_q)
    # Map by reservation_id for lookup
    pending_extensions = {}
    for ext in pending_ext_result.scalars():
        if ext.reservation_id:
            pending_extensions[ext.reservation_id] = {
                "id": ext.id,
                "extension_minutes": ext.extension_minutes,
                "requested_at": ext.requested_at.isoformat() if ext.requested_at else None,
            }

    floor = []
    for comp in computers:
        entry = {
            "id": comp.id,
            "name": comp.name,
            "computer_number": comp.computer_number,
            "location": comp.location,
            "computer_type": comp.computer_type.value
            if hasattr(comp.computer_type, "value")
            else comp.computer_type,
            "status": comp.status.value if hasattr(comp.status, "value") else comp.status,
            "has_internet": comp.has_internet,
            "has_print_release": comp.has_print_release,
            "max_session_minutes": comp.max_session_minutes,
            "active_session": None,
            "pending_extension": None,
        }

        reservation = active_reservations.get(comp.id)
        if reservation:
            end_time = reservation.extended_until or reservation.reserved_end_time
            remaining = int((end_time - now).total_seconds() / 60) if end_time else 0
            is_overtime = remaining < 0
            patron_name = None
            if reservation.patron_id:
                patron_name = patron_names.get(reservation.patron_id)
            elif reservation.guest_name:
                patron_name = f"{reservation.guest_name} (Guest)"

            entry["active_session"] = {
                "reservation_id": reservation.id,
                "patron_name": patron_name,
                "started_at": reservation.actual_start_time.isoformat()
                if reservation.actual_start_time
                else None,
                "ends_at": end_time.isoformat() if end_time else None,
                "minutes_remaining": max(remaining, 0),
                "is_overtime": is_overtime,
                "minutes_overtime": -remaining if is_overtime else 0,
                "extensions_used": reservation.extensions_used,
                "is_guest": reservation.is_guest_pass,
                "print_jobs_count": reservation.print_jobs_count,
            }

            ext = pending_extensions.get(reservation.id)
            if ext:
                entry["pending_extension"] = ext

        floor.append(entry)

    return {
        "computers": floor,
        "summary": {
            "total": len(floor),
            "available": sum(1 for c in floor if c["status"] == "available"),
            "in_use": sum(1 for c in floor if c["active_session"]),
            "maintenance": sum(1 for c in floor if c["status"] in ("maintenance", "offline")),
            "pending_extensions": len(pending_extensions),
        },
    }


_END_REASON_CATEGORIES = {
    "time_up",
    "patron_left",
    "policy_violation",
    "technical_issue",
    "other",
}

# Window during which staff can undo a force-end via /reopen.
_REOPEN_WINDOW_SECONDS = 60


@router.post("/staff/reservations/{reservation_id}/end-session")
async def staff_end_session_by_reservation(
    reservation_id: int,
    request: StaffEndSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Staff force-ends a patron's active computer session.

    Resolves the active ComputerSession for the reservation, records the
    terminating staff member + reason on the session for CIPA audit, frees
    the workstation, and marks the reservation completed.

    Falls back to completing the reservation directly if no session row
    exists (data-recovery path for legacy walk-ins).
    """
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    if request.reason_category not in _END_REASON_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"reason_category must be one of {sorted(_END_REASON_CATEGORIES)}",
        )

    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    session_q = (
        select(ComputerSession)
        .where(ComputerSession.reservation_id == reservation_id)
        .where(ComputerSession.is_active == True)  # noqa: E712
    )
    session = (await db.execute(session_q)).scalars().first()

    full_reason = (
        f"{request.reason_category}: {request.notes}" if request.notes else request.reason_category
    )

    if session:
        await computer_service.end_session(
            db,
            session.id,
            logoff_reason=f"staff_terminated:{request.reason_category}",
            terminated_by_id=current_user.id,
            termination_reason=full_reason,
        )
    else:
        # No session row exists — reservation got into in_session without
        # a paired ComputerSession. Recover state directly.
        now = datetime.now(timezone.utc)
        reservation.status = ComputerReservationStatus.completed
        reservation.actual_end_time = now
        reservation.cancelled_by = current_user.id
        reservation.cancellation_reason = f"staff_ended:{full_reason}"[:500]
        computer = await db.get(Computer, reservation.computer_id)
        if computer and computer.status in (
            ComputerStatus.in_use,
            ComputerStatus.reserved,
        ):
            computer.status = ComputerStatus.available
        logger.warning(
            "staff_end_session no_active_session reservation_id=%s staff_id=%s reason=%s",
            reservation_id,
            current_user.id,
            full_reason,
        )

    await db.commit()
    await floor_view_bus.publish(
        "session_ended",
        computer_id=reservation.computer_id,
        reservation_id=reservation_id,
        by_staff=True,
    )
    return {
        "ok": True,
        "reservation_id": reservation_id,
        "session_id": session.id if session else None,
        "reason_category": request.reason_category,
    }


@router.post("/staff/sessions/{session_id}/reopen")
async def staff_reopen_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Undo a recent staff-initiated session end.

    Only valid within `_REOPEN_WINDOW_SECONDS` of the original end and only
    when the session was staff-terminated (`terminated_by_id` set). Restores
    the session, reservation, and computer state, and writes an audit row.
    """
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    session = await db.get(ComputerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_active:
        raise HTTPException(status_code=400, detail="Session is already active")

    if session.terminated_by_id is None:
        # Patron self-logout or auto timeout — undo isn't appropriate.
        raise HTTPException(
            status_code=400,
            detail="Only staff-terminated sessions can be reopened",
        )

    end_time = session.ended_at or session.actual_end_time
    if end_time is None:
        raise HTTPException(status_code=400, detail="Session has no end timestamp")

    now = datetime.now(timezone.utc)
    seconds_since_end = int((now - end_time).total_seconds())
    if seconds_since_end > _REOPEN_WINDOW_SECONDS:
        raise HTTPException(
            status_code=410,
            detail=f"Undo window expired ({seconds_since_end}s ago)",
        )

    # Restore session
    from ...models.cipa_compliance import ComputerSessionStatus

    session.is_active = True
    session.status = ComputerSessionStatus.ACTIVE
    session.ended_at = None
    session.actual_end_time = None
    session.terminated_by_id = None
    session.termination_reason = None
    session.logoff_reason = None
    session.user_initiated_logout = False

    # Restore reservation
    if session.reservation_id:
        reservation = await db.get(ComputerReservation, session.reservation_id)
        if reservation:
            reservation.status = ComputerReservationStatus.in_session
            reservation.actual_end_time = None

    # Restore computer
    if session.computer_id:
        computer = await db.get(Computer, session.computer_id)
        if computer:
            computer.status = ComputerStatus.in_use

    from ...services import operations_audit_service as ops_audit

    await ops_audit.log_computer_session_reopened(
        db,
        session_id=session.id,
        computer_id=session.computer_id,
        patron_id=session.patron_id,
        reopened_by_id=current_user.id,
        seconds_since_end=seconds_since_end,
    )

    logger.info(
        "computer_session_reopened session_id=%s staff_id=%s seconds_since_end=%s",
        session.id,
        current_user.id,
        seconds_since_end,
    )

    await db.commit()
    await floor_view_bus.publish(
        "session_reopened",
        computer_id=session.computer_id,
        reservation_id=session.reservation_id,
    )
    return {
        "ok": True,
        "session_id": session.id,
        "reservation_id": session.reservation_id,
    }


@router.patch("/staff/reservations/{reservation_id}", response_model=BookingReservationResponse)
async def staff_update_reservation(
    reservation_id: int,
    request: StaffReservationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingReservationResponse:
    """Staff reschedule of a reservation's time (move start/end, or set a new end).

    A confirmed reservation can move both ends; an in-session one can only move
    its end (the active session's end + auto-logout follow). Rejects overlaps
    with other reservations on the same computer (409).
    """
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    for dt in (request.reserved_start_time, request.reserved_end_time):
        if dt is not None and dt.tzinfo is None:
            raise HTTPException(
                status_code=400,
                detail="Timestamps must include a timezone offset (e.g. ...Z)",
            )
    if request.reserved_start_time is None and request.reserved_end_time is None:
        raise HTTPException(status_code=400, detail="Provide a new start and/or end time")

    reservation, error = await computer_service.staff_update_reservation(
        db, reservation_id, request.reserved_start_time, request.reserved_end_time
    )
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Reservation not found")
    if error == "closed":
        raise HTTPException(
            status_code=400, detail="Cannot reschedule a completed or cancelled reservation"
        )
    if error == "bad_times":
        raise HTTPException(
            status_code=400, detail="End must be after start; a started session's start cannot move"
        )
    if error == "no_change":
        raise HTTPException(status_code=400, detail="New time is the same as the current time")
    if error == "conflict":
        raise HTTPException(
            status_code=409,
            detail="Requested time conflicts with another reservation on this computer",
        )

    await db.commit()
    if reservation is not None and reservation.status == ComputerReservationStatus.in_session:
        await floor_view_bus.publish(
            "session_extended",
            computer_id=reservation.computer_id,
            reservation_id=reservation.id,
            extra_minutes=0,
        )
    return BookingReservationResponse.model_validate(reservation)


@router.post("/staff/reservations/{reservation_id}/extend", response_model=BookingSessionResponse)
async def staff_extend_session(
    reservation_id: int,
    request: StaffExtendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingSessionResponse:
    """Staff-granted extension on a reservation's active session (no patron request)."""
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    session_q = (
        select(ComputerSession)
        .where(ComputerSession.reservation_id == reservation_id)
        .where(ComputerSession.is_active == True)  # noqa: E712
    )
    session = (await db.execute(session_q)).scalars().first()
    if session is None:
        raise HTTPException(status_code=404, detail="No active session for this reservation")

    reservation, error = await computer_service.staff_extend_session(
        db, session.id, request.extra_minutes, current_user.id
    )
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Active session not found")
    if error == "no_reservation":
        raise HTTPException(status_code=400, detail="Session is not linked to a reservation")
    if error == "no_end":
        raise HTTPException(status_code=400, detail="Session has no end time to extend")

    await db.commit()
    now = datetime.now(timezone.utc)
    await floor_view_bus.publish(
        "session_extended",
        computer_id=reservation.computer_id,
        reservation_id=reservation.id,
        extra_minutes=request.extra_minutes,
    )
    resp = BookingSessionResponse.model_validate(reservation)
    resp.minutes_remaining = max(int((reservation.reserved_end_time - now).total_seconds() / 60), 0)
    return resp


_BULK_ACTIONS = {"end_sessions", "mark_available", "mark_maintenance", "mark_offline"}

_BULK_STATUS_MAP = {
    "mark_available": ComputerStatus.available,
    "mark_maintenance": ComputerStatus.maintenance,
    "mark_offline": ComputerStatus.offline,
}


@router.post("/staff/bulk", response_model=StaffBulkActionResponse)
async def staff_bulk_action(
    request: StaffBulkActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffBulkActionResponse:
    """Apply a single staff action across many computers in one request.

    Per-computer outcomes are returned independently so a partial failure
    (e.g. one row has no active session) doesn't sink the whole batch.
    """
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    if request.action not in _BULK_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"action must be one of {sorted(_BULK_ACTIONS)}",
        )

    if request.action == "end_sessions":
        if request.reason_category not in _END_REASON_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail="end_sessions requires reason_category",
            )

    ids = list(dict.fromkeys(request.computer_ids))  # dedupe, preserve order

    # Fetch all targeted computers in one query.
    comp_q = select(Computer).where(Computer.id.in_(ids))
    comp_result = await db.execute(comp_q)
    computers_by_id = {c.id: c for c in comp_result.scalars()}

    results: list[StaffBulkActionResultItem] = []
    affected_computer_ids: list[int] = []
    ended_reservation_ids: list[int] = []

    full_reason = (
        f"{request.reason_category}: {request.notes}"
        if request.notes
        else (request.reason_category or "")
    )

    if request.action == "end_sessions":
        # Look up active sessions for the targeted computers once.
        sess_q = (
            select(ComputerSession)
            .where(ComputerSession.computer_id.in_(ids))
            .where(ComputerSession.is_active == True)  # noqa: E712
        )
        sess_result = await db.execute(sess_q)
        sessions_by_computer = {s.computer_id: s for s in sess_result.scalars()}

        for cid in ids:
            if cid not in computers_by_id:
                results.append(
                    StaffBulkActionResultItem(
                        computer_id=cid,
                        success=False,
                        detail="not_found",
                    )
                )
                continue
            session = sessions_by_computer.get(cid)
            if session is None:
                results.append(
                    StaffBulkActionResultItem(
                        computer_id=cid,
                        success=False,
                        detail="no_active_session",
                    )
                )
                continue
            await computer_service.end_session(
                db,
                session.id,
                logoff_reason=f"staff_terminated:{request.reason_category}",
                terminated_by_id=current_user.id,
                termination_reason=full_reason,
            )
            affected_computer_ids.append(cid)
            if session.reservation_id:
                ended_reservation_ids.append(session.reservation_id)
            results.append(
                StaffBulkActionResultItem(
                    computer_id=cid,
                    success=True,
                )
            )
    else:
        target_status = _BULK_STATUS_MAP[request.action]
        for cid in ids:
            computer = computers_by_id.get(cid)
            if computer is None:
                results.append(
                    StaffBulkActionResultItem(
                        computer_id=cid,
                        success=False,
                        detail="not_found",
                    )
                )
                continue
            # Refuse to overwrite an in_use station unless explicitly ending it.
            if (
                computer.status == ComputerStatus.in_use
                and target_status != ComputerStatus.available
            ):
                results.append(
                    StaffBulkActionResultItem(
                        computer_id=cid,
                        success=False,
                        detail="active_session_present",
                    )
                )
                continue
            computer.status = target_status
            affected_computer_ids.append(cid)
            results.append(
                StaffBulkActionResultItem(
                    computer_id=cid,
                    success=True,
                )
            )

    await db.commit()

    # Best-effort live fan-out per affected entity.
    for cid in affected_computer_ids:
        try:
            if request.action == "end_sessions":
                await floor_view_bus.publish(
                    "session_ended",
                    computer_id=cid,
                    by_staff=True,
                    bulk=True,
                )
            else:
                computer = computers_by_id.get(cid)
                await floor_view_bus.publish(
                    "computer_status_changed",
                    computer_id=cid,
                    status=computer.status.value
                    if computer and hasattr(computer.status, "value")
                    else None,
                )
        except Exception:  # noqa: BLE001
            pass

    succeeded = sum(1 for r in results if r.success)
    return StaffBulkActionResponse(
        action=request.action,
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )


@router.get("/staff/reservations")
async def staff_list_reservations(
    status_filter: Optional[str] = Query(None, alias="status"),
    date_filter: Optional[str] = Query(None, alias="date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List all reservations for staff (not just current user's)."""
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    query = select(ComputerReservation)

    if status_filter:
        query = query.where(ComputerReservation.status == status_filter)

    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            day_end = target_date + timedelta(days=1)
            query = query.where(
                ComputerReservation.reserved_start_time >= target_date,
                ComputerReservation.reserved_start_time < day_end,
            )
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format, use YYYY-MM-DD"
            ) from None
    else:
        # Default to today
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        query = query.where(
            ComputerReservation.reserved_start_time >= today,
            ComputerReservation.reserved_start_time < tomorrow,
        )

    count_q = select(sqlfunc.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(ComputerReservation.reserved_start_time).offset(skip).limit(limit)
    result = await db.execute(query)
    reservations = list(result.scalars())

    # Get patron names and computer names
    patron_ids = [r.patron_id for r in reservations if r.patron_id]
    computer_ids = list({r.computer_id for r in reservations})

    patron_names = {}
    if patron_ids:
        from ...models.user import User as UserModel

        p_result = await db.execute(select(UserModel).where(UserModel.id.in_(patron_ids)))
        patron_names = {u.id: u.full_name for u in p_result.scalars()}

    computer_names = {}
    if computer_ids:
        c_result = await db.execute(select(Computer).where(Computer.id.in_(computer_ids)))
        computer_names = {c.id: c.name for c in c_result.scalars()}

    items = []
    for r in reservations:
        patron_name = None
        if r.patron_id:
            patron_name = patron_names.get(r.patron_id)
        elif r.guest_name:
            patron_name = f"{r.guest_name} (Guest)"

        items.append(
            {
                "id": r.id,
                "computer_id": r.computer_id,
                "computer_name": computer_names.get(r.computer_id, "Unknown"),
                "patron_id": r.patron_id,
                "patron_name": patron_name,
                "reserved_start_time": r.reserved_start_time.isoformat()
                if r.reserved_start_time
                else None,
                "reserved_end_time": r.reserved_end_time.isoformat()
                if r.reserved_end_time
                else None,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "session_duration_minutes": r.session_duration_minutes,
                "is_guest_pass": r.is_guest_pass,
                "guest_name": r.guest_name,
                "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
                "extensions_used": r.extensions_used,
                "print_jobs_count": r.print_jobs_count,
            }
        )

    return {"items": items, "total": total}


@router.get("/staff/guest-passes")
async def staff_list_guest_passes(
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List all guest passes for staff."""
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    query = select(GuestPass)
    if active_only:
        query = query.where(GuestPass.is_active == True)

    count_q = select(sqlfunc.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(GuestPass.issued_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    passes = list(result.scalars())

    return {
        "items": [GuestPassResponse.model_validate(p) for p in passes],
        "total": total,
    }


# ── Single-computer lookup (must be after all /specific routes) ──────


@router.get("/{computer_id}", response_model=ComputerResponse)
async def get_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db),
) -> Computer:
    """Get details for a specific computer."""
    computer = await db.get(Computer, computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    return computer


@router.get("/{computer_id}/availability")
async def check_computer_availability(
    computer_id: int,
    start_time: datetime = Query(...),
    duration_minutes: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a computer is available for a given time slot."""
    computer = await db.get(Computer, computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    is_available = await computer_service.check_computer_availability(
        db, computer_id, start_time, duration_minutes
    )

    return {"computer_id": computer_id, "is_available": is_available}


# ── Floor View live updates (WebSocket) ───────────────────────────────


def _floor_ws_credentials(
    websocket: WebSocket, query_token: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Extract the staff JWT, preferring the ``bearer`` Sec-WebSocket-Protocol
    subprotocol so the token stays out of URL-logging nginx access logs.

    Returns ``(token, subprotocol_to_accept)``.
    """
    offered = websocket.headers.get("sec-websocket-protocol")
    if offered:
        parts = [p.strip() for p in offered.split(",")]
        if len(parts) >= 2 and parts[0] == "bearer" and parts[1]:
            return parts[1], "bearer"
    if query_token:
        # Legacy clients; remove after one deploy cycle.
        logger.warning(
            "staff_floor_ws token in query string is deprecated; "
            "send it via the bearer Sec-WebSocket-Protocol subprotocol"
        )
        return query_token, None
    return None, None


@router.websocket("/staff/floor/ws")
async def staff_floor_ws(websocket: WebSocket, token: Optional[str] = Query(None)) -> None:
    from ...core.security import verify_token
    from ...core.database import async_session_maker
    from ...models.user import User as UserModel, UserRole

    token, accept_subprotocol = _floor_ws_credentials(websocket, token)
    if not token:
        await websocket.close(code=1008, reason="invalid_token")
        return

    # Authenticate before accepting so we can close cleanly on bad creds.
    try:
        payload = verify_token(token, check_revocation=True)
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            await websocket.close(code=1008, reason="invalid_token")
            return
        user_id = int(user_id_raw)
    except Exception:  # noqa: BLE001  # WebSocket auth — close with invalid_token on any decode failure
        await websocket.close(code=1008, reason="invalid_token")
        return

    async with async_session_maker() as db:
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()

    if user is None or not user.is_active or user.role not in _STAFF_ROLES:
        await websocket.close(code=1008, reason="forbidden")
        return

    # When the client offered the bearer subprotocol we must select it back,
    # or browsers fail the handshake.
    await websocket.accept(subprotocol=accept_subprotocol)
    await floor_view_bus.connect(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            # We don't expect inbound messages, but receive_text drains any
            # client-sent keepalives and surfaces disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("staff_floor_ws unexpected error user_id=%s err=%s", user_id, exc)
    finally:
        await floor_view_bus.disconnect(websocket)
