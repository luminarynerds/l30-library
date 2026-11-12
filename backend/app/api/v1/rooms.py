# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public room browser and reservation routes."""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.content_i18n import translated
from ...core.database import get_db
from ...core.pagination_config import PaginationDefaults
from ...core.rate_limit import limiter
from ...models.room import (ReservationStatus, Room, RoomEquipment,
                            RoomReservation, RoomType, RoomWaitlist)
from ...models.user import User, UserRole
from ...schemas.room import (EquipmentResponse, ReservationBriefResponse,
                             ReservationCreate, ReservationListResponse,
                             ReservationResponse, RoomAvailabilityResponse,
                             RoomAvailabilitySlot, RoomListResponse,
                             RoomResponse, WaitlistCreate, WaitlistResponse,
                             WaitlistListResponse)
from ...services import room_service
from .auth import get_current_user, get_current_user_optional

logger = get_logger(__name__)

router = APIRouter(prefix="/rooms", tags=["rooms"])


# ============================================================================
# Public Room Browsing
# ============================================================================

def _room_response(room: Room, lang: str | None = None) -> RoomResponse:
    resp = RoomResponse.model_validate(room)
    if lang:
        resp.name = translated(room, "name", lang)
        resp.description = translated(room, "description", lang)
    return resp


@router.get("", response_model=RoomListResponse)
@limiter.limit("60/minute")
async def list_rooms(
    request: Request,
    room_type: str | None = Query(None, description="Filter by room type"),
    branch_id: int | None = Query(None, description="Filter by branch"),
    min_capacity: int | None = Query(None, ge=1, description="Minimum capacity"),
    amenity: str | None = Query(None, description="Required amenity"),
    lang: str | None = Query(None, max_length=10),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """
    List all available rooms with optional filtering.

    This is the public room browser showing all active rooms.
    """
    query = select(Room).where(Room.is_active == True)
    count_query = select(func.count(Room.id)).where(Room.is_active == True)

    if room_type:
        try:
            rt = RoomType(room_type)
            query = query.where(Room.room_type == rt)
            count_query = count_query.where(Room.room_type == rt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid room_type. Valid values: {[t.value for t in RoomType]}"
            ) from None

    if branch_id:
        query = query.where(Room.branch_id == branch_id)
        count_query = count_query.where(Room.branch_id == branch_id)

    if min_capacity:
        query = query.where(Room.capacity >= min_capacity)
        count_query = count_query.where(Room.capacity >= min_capacity)

    if amenity:
        query = query.where(Room.amenities.any(amenity))
        count_query = count_query.where(Room.amenities.any(amenity))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Room.name)

    result = await db.execute(query)
    rooms = result.scalars().all()

    return {
        "items": [_room_response(r, lang) for r in rooms],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/room-types", response_model=list[dict])
@limiter.limit("60/minute")
async def list_room_types(request: Request):
    """Get all available room types with descriptions."""
    return [
        {
            "value": RoomType.study_room.value,
            "name": "Study Room",
            "description": "Individual or small group study rooms. Auto-approved.",
            "requires_approval": False,
        },
        {
            "value": RoomType.meeting_room.value,
            "name": "Meeting Room",
            "description": "Larger rooms for meetings and presentations. Requires staff approval.",
            "requires_approval": True,
        },
        {
            "value": RoomType.computer_lab.value,
            "name": "Computer Lab",
            "description": "Rooms with computers for digital work. Auto-approved.",
            "requires_approval": False,
        },
        {
            "value": RoomType.event_space.value,
            "name": "Event Space",
            "description": "Large spaces for events and programs. Requires staff approval.",
            "requires_approval": True,
        },
    ]


@router.get("/equipment", response_model=list[EquipmentResponse])
@limiter.limit("60/minute")
async def list_equipment(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all available equipment add-ons."""
    result = await db.execute(
        select(RoomEquipment)
        .where(RoomEquipment.is_active == True)
        .order_by(RoomEquipment.name)
    )
    equipment = result.scalars().all()
    return [EquipmentResponse.model_validate(e) for e in equipment]


@router.get("/amenities", response_model=list[str])
@limiter.limit("60/minute")
async def list_amenities(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all unique amenities across active rooms."""
    result = await db.execute(
        select(func.unnest(Room.amenities))
        .where(Room.is_active == True)
        .where(Room.amenities.isnot(None))
        .distinct()
    )
    amenities = [row[0] for row in result.all() if row[0]]
    return sorted(amenities)


@router.get("/availability/multi", response_model=dict[str, list[RoomAvailabilityResponse]])
@limiter.limit("30/minute")
async def get_multi_room_availability(
    request: Request,
    room_ids: str = Query(..., description="Comma-separated list of room IDs"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Check availability across multiple rooms simultaneously.

    Returns availability for all specified rooms across the date range.
    Useful for group bookings or comparing room availability.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    if end <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")

    # Parse room IDs
    try:
        room_id_list = [int(rid.strip()) for rid in room_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid room IDs format") from None

    # Validate limit on number of rooms
    if len(room_id_list) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check availability for more than 20 rooms at once"
        )

    # Validate date range (max 30 days for multi-room queries)
    date_diff = (end - start).days
    if date_diff > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 30 days for multi-room queries"
        )

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Validate dates
    if start < today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot check availability for past dates")

    # Get all rooms
    rooms_result = await db.execute(
        select(Room)
        .where(Room.id.in_(room_id_list))
        .where(Room.is_active == True)
    )
    rooms = {r.id: r for r in rooms_result.scalars().all()}

    # Check which requested room IDs were found
    missing_rooms = set(room_id_list) - set(rooms.keys())
    if missing_rooms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooms not found: {', '.join(map(str, missing_rooms))}"
        )

    result_data = {}

    # For each room, get availability for the date range
    for room_id in room_id_list:
        room = rooms[room_id]
        availability_list = []
        current_date = start

        # Check advance booking limit
        max_date = today + timedelta(days=room.advance_booking_days)
        if start > max_date:
            # Room not available for this date range
            result_data[str(room_id)] = []
            continue

        while current_date < end:
            # Skip dates beyond advance booking limit
            max_date = today + timedelta(days=room.advance_booking_days)
            if current_date > max_date:
                break

            # Get available slots
            slots = await room_service.get_room_availability_slots(db, room, current_date)

            # Get reservations for this date
            day_start = current_date
            day_end = current_date + timedelta(days=1)

            reservations_result = await db.execute(
                select(RoomReservation)
                .where(RoomReservation.room_id == room_id)
                .where(
                    RoomReservation.status.in_([
                        ReservationStatus.pending,
                        ReservationStatus.confirmed,
                        ReservationStatus.checked_in,
                    ])
                )
                .where(RoomReservation.start_time >= day_start)
                .where(RoomReservation.start_time < day_end)
                .order_by(RoomReservation.start_time)
            )
            reservations = reservations_result.scalars().all()

            availability_list.append(
                RoomAvailabilityResponse(
                    room_id=room.id,
                    room_name=room.name,
                    date=current_date.strftime("%Y-%m-%d"),
                    available_slots=[
                        RoomAvailabilitySlot(
                            start_time=s["start_time"],
                            end_time=s["end_time"],
                            duration_minutes=s["duration_minutes"],
                            max_available_minutes=s.get("max_available_minutes"),
                        )
                        for s in slots
                    ],
                    reservations=[
                        ReservationBriefResponse(
                            id=r.id,
                            start_time=r.start_time,
                            end_time=r.end_time,
                            status=str(r.status),
                        )
                        for r in reservations
                    ],
                )
            )

            current_date += timedelta(days=1)

        result_data[str(room_id)] = availability_list

    return result_data


# ============================================================================
# Patron Reservation Management
# ============================================================================

@router.get("/my/reservations", response_model=ReservationListResponse)
@limiter.limit("60/minute")
async def get_my_reservations(
    request: Request,
    status_filter: str | None = Query(None, description="Filter by status"),
    upcoming_only: bool = Query(True, description="Only show upcoming reservations"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's room reservations."""
    query = (
        select(RoomReservation)
        .where(RoomReservation.patron_id == current_user.id)
    )
    count_query = (
        select(func.count(RoomReservation.id))
        .where(RoomReservation.patron_id == current_user.id)
    )

    if status_filter:
        try:
            status_enum = ReservationStatus(status_filter)
            query = query.where(RoomReservation.status == status_enum)
            count_query = count_query.where(RoomReservation.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Valid values: {[s.value for s in ReservationStatus]}"
            ) from None

    if upcoming_only:
        now = datetime.now(timezone.utc)
        query = query.where(RoomReservation.start_time >= now)
        count_query = count_query.where(RoomReservation.start_time >= now)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(RoomReservation.start_time)

    result = await db.execute(query)
    reservations = result.scalars().all()

    # Get room names
    room_ids = {r.room_id for r in reservations}
    rooms_result = await db.execute(
        select(Room).where(Room.id.in_(room_ids))
    )
    rooms_map = {r.id: r for r in rooms_result.scalars().all()}

    items = []
    for r in reservations:
        room = rooms_map.get(r.room_id)
        items.append(ReservationResponse(
            **{k: v for k, v in r.__dict__.items() if not k.startswith("_")},
            room_name=room.name if room else None,
            patron_name=f"{current_user.first_name} {current_user.last_name}",
        ))

    return ReservationListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/my/reservations/{reservation_id}", response_model=ReservationResponse)
@limiter.limit("60/minute")
async def get_my_reservation(
    request: Request,
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific reservation owned by the current user."""
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .where(RoomReservation.patron_id == current_user.id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    # Get room
    room_result = await db.execute(
        select(Room).where(Room.id == reservation.room_id)
    )
    room = room_result.scalar_one_or_none()

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{current_user.first_name} {current_user.last_name}",
    )


@router.put("/my/reservations/{reservation_id}", response_model=ReservationResponse)
@limiter.limit("10/minute")
async def update_my_reservation(
    request: Request,
    reservation_id: int,
    update_data: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a reservation owned by the current user.

    Only pending or confirmed reservations can be modified.
    Modifying a confirmed meeting room reservation will set it back to pending.
    """
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .where(RoomReservation.patron_id == current_user.id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status not in [ReservationStatus.pending, ReservationStatus.confirmed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or confirmed reservations can be modified"
        )

    # Get room
    room_result = await db.execute(
        select(Room).where(Room.id == reservation.room_id).with_for_update()
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Validate new times if changed
    new_start = update_data.start_time or reservation.start_time
    new_end = update_data.end_time or reservation.end_time

    if new_start != reservation.start_time or new_end != reservation.end_time:
        validation_errors = await room_service.validate_reservation_rules(
            db, room, new_start, new_end, current_user
        )
        if validation_errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(validation_errors))

        # Check availability (excluding current reservation)
        is_available = await room_service.check_room_availability(
            db, room.id, new_start, new_end, exclude_reservation_id=reservation_id
        )
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room is not available for the requested time"
            )

        reservation.start_time = new_start
        reservation.end_time = new_end

        # If room requires approval, set back to pending
        if room.requires_approval and reservation.status == ReservationStatus.confirmed:
            reservation.status = ReservationStatus.pending
            reservation.approved_by = None
            reservation.approved_at = None

    # Update other fields
    if update_data.purpose is not None:
        reservation.purpose = update_data.purpose
    if update_data.attendee_count is not None:
        if update_data.attendee_count > room.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attendee count exceeds room capacity ({room.capacity})"
            )
        reservation.attendee_count = update_data.attendee_count
    if update_data.equipment_requested is not None:
        reservation.equipment_requested = update_data.equipment_requested
    if update_data.contact_name is not None:
        reservation.contact_name = update_data.contact_name
    if update_data.contact_email is not None:
        reservation.contact_email = update_data.contact_email
    if update_data.contact_phone is not None:
        reservation.contact_phone = update_data.contact_phone

    await db.commit()
    await db.refresh(reservation)

    logger.info(
        "Reservation updated by patron",
        extra={"reservation_id": reservation_id, "patron_id": current_user.id}
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name,
        patron_name=f"{current_user.first_name} {current_user.last_name}",
    )


@router.delete("/my/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def cancel_my_reservation(
    request: Request,
    reservation_id: int,
    reason: str | None = Query(None, max_length=500),
    cancel_future: bool = Query(False, description="Cancel future occurrences of recurring reservation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a reservation owned by the current user.

    For recurring reservations, optionally cancel all future occurrences.
    """
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .where(RoomReservation.patron_id == current_user.id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status not in (ReservationStatus.pending, ReservationStatus.confirmed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending or confirmed reservations can be cancelled (current status: '{reservation.status}')"
        )

    # Get room for email
    room_result = await db.execute(
        select(Room).where(Room.id == reservation.room_id)
    )
    room = room_result.scalar_one_or_none()

    # Cancel the reservation
    await room_service.cancel_reservation(
        db, reservation, current_user, reason, cancel_future_occurrences=cancel_future
    )

    await db.commit()

    # Send cancellation email
    if room:
        try:
            await room_service.send_cancellation_notification(
                reservation, room, cancelled_by_staff=False, reason=reason, patron=current_user
            )
        except Exception as e:  # noqa: BLE001  # best-effort cancellation email — reservation already cancelled
            logger.error(f"Failed to send cancellation email: {e}")

    logger.info(
        "Reservation cancelled by patron",
        extra={"reservation_id": reservation_id, "patron_id": current_user.id}
    )

    return None


@router.post("/my/reservations/{reservation_id}/check-in", response_model=ReservationResponse)
@limiter.limit("10/minute")
async def check_in_to_reservation(
    request: Request,
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check in to a confirmed reservation.

    Check-in is available starting 15 minutes before the reservation start time.
    Reservations not checked in within 15 minutes of start time will be marked as no-show.
    """
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .where(RoomReservation.patron_id == current_user.id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    try:
        await room_service.check_in_reservation(db, reservation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await db.commit()
    await db.refresh(reservation)

    # Get room
    room_result = await db.execute(
        select(Room).where(Room.id == reservation.room_id)
    )
    room = room_result.scalar_one_or_none()

    logger.info(
        "Patron checked in to reservation",
        extra={"reservation_id": reservation_id, "patron_id": current_user.id}
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{current_user.first_name} {current_user.last_name}",
    )


# ============================================================================
# Waitlist Management
# ============================================================================

@router.post("/waitlist", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def join_waitlist(
    request: Request,
    waitlist_data: WaitlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join the waitlist for a room at a specific time."""
    # Verify room exists and is active
    room_result = await db.execute(
        select(Room).where(Room.id == waitlist_data.room_id).where(Room.is_active == True)
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found or inactive")

    # Validate time range
    if waitlist_data.desired_end_time <= waitlist_data.desired_start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time range")

    # Check if patron already has a confirmed reservation at that time
    conflict_result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.room_id == waitlist_data.room_id)
        .where(RoomReservation.patron_id == current_user.id)
        .where(RoomReservation.status.in_([ReservationStatus.confirmed, ReservationStatus.checked_in]))
        .where(
            RoomReservation.start_time < waitlist_data.desired_end_time,
            RoomReservation.end_time > waitlist_data.desired_start_time,
        )
    )
    if conflict_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already have a confirmed reservation at this time")

    # Create waitlist entry
    waitlist_entry = await room_service.add_to_waitlist(
        db,
        room,
        current_user,
        waitlist_data.desired_start_time,
        waitlist_data.desired_end_time,
    )

    await db.commit()
    await db.refresh(waitlist_entry)

    # Calculate position in queue
    position = await room_service.get_waitlist_position(db, waitlist_entry)

    logger.info(
        "Patron added to waitlist",
        extra={"room_id": room.id, "patron_id": current_user.id, "position": position}
    )

    response_data = WaitlistResponse.model_validate(waitlist_entry)
    response_data.position = position
    return response_data


@router.get("/my/waitlist", response_model=WaitlistListResponse)
@limiter.limit("60/minute")
async def get_my_waitlist(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's waitlist entries."""
    query = select(RoomWaitlist).where(RoomWaitlist.patron_id == current_user.id)

    # Count total
    count_result = await db.execute(
        select(func.count(RoomWaitlist.id)).where(RoomWaitlist.patron_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # Get paginated results (only pending and notified)
    query = (query
        .where(RoomWaitlist.status.in_(["pending", "notified"]))
        .order_by(RoomWaitlist.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    result = await db.execute(query)
    waitlist_entries = list(result.scalars().all())

    # Build response items with positions
    items = []
    for entry in waitlist_entries:
        response_data = WaitlistResponse.model_validate(entry)
        # Only calculate position for pending entries
        if entry.status == "pending":
            position = await room_service.get_waitlist_position(db, entry)
            response_data.position = position
        items.append(response_data)

    return WaitlistListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.delete("/my/waitlist/{waitlist_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def remove_from_waitlist(
    request: Request,
    waitlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove self from waitlist."""
    result = await db.execute(
        select(RoomWaitlist)
        .where(RoomWaitlist.id == waitlist_id)
        .where(RoomWaitlist.patron_id == current_user.id)
    )
    waitlist_entry = result.scalar_one_or_none()
    if not waitlist_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found")

    await db.delete(waitlist_entry)
    await db.commit()

    logger.info(
        "Patron removed from waitlist",
        extra={"room_id": waitlist_entry.room_id, "patron_id": current_user.id}
    )


# ============================================================================
# Room-specific routes (/{room_id} must come after all literal paths)
# ============================================================================

@router.get("/{room_id}", response_model=RoomResponse)
@limiter.limit("120/minute")
async def get_room(
    request: Request,
    room_id: int,
    lang: str | None = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Get details for a specific room."""
    result = await db.execute(
        select(Room).where(Room.id == room_id).where(Room.is_active == True)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    return _room_response(room, lang)


@router.get("/{room_id}/availability", response_model=RoomAvailabilityResponse)
@limiter.limit("60/minute")
async def get_room_availability(
    request: Request,
    room_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get availability calendar for a room on a specific date.

    Returns available time slots and existing reservations.
    """
    # Validate date format
    try:
        check_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    # Check date is not in the past
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if check_date < today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot check availability for past dates")

    # Get room
    result = await db.execute(
        select(Room).where(Room.id == room_id).where(Room.is_active == True)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Check advance booking limit
    max_date = today + timedelta(days=room.advance_booking_days)
    if check_date > max_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check availability more than {room.advance_booking_days} days in advance"
        )

    # Get available slots
    slots = await room_service.get_room_availability_slots(db, room, check_date)

    # Get reservations for this date (for display)
    day_start = check_date
    day_end = check_date + timedelta(days=1)

    reservations_result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.room_id == room_id)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ])
        )
        .where(RoomReservation.start_time >= day_start)
        .where(RoomReservation.start_time < day_end)
        .order_by(RoomReservation.start_time)
    )
    reservations = reservations_result.scalars().all()

    return RoomAvailabilityResponse(
        room_id=room.id,
        room_name=room.name,
        date=date,
        available_slots=[
            RoomAvailabilitySlot(
                start_time=s["start_time"],
                end_time=s["end_time"],
                duration_minutes=s["duration_minutes"],
                max_available_minutes=s.get("max_available_minutes"),
            )
            for s in slots
        ],
        reservations=[
            ReservationBriefResponse(
                id=r.id,
                start_time=r.start_time,
                end_time=r.end_time,
                status=str(r.status),
            )
            for r in reservations
        ],
    )


@router.get("/{room_id}/availability/week", response_model=list[RoomAvailabilityResponse])
@limiter.limit("30/minute")
async def get_room_availability_week(
    request: Request,
    room_id: int,
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get availability calendar for a room for a week starting from the given date.
    """
    try:
        check_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if check_date < today:
        check_date = today

    result = await db.execute(
        select(Room).where(Room.id == room_id).where(Room.is_active == True)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    availability_list = []
    for i in range(7):
        current_date = check_date + timedelta(days=i)

        # Skip dates beyond advance booking limit
        max_date = today + timedelta(days=room.advance_booking_days)
        if current_date > max_date:
            break

        slots = await room_service.get_room_availability_slots(db, room, current_date)

        day_start = current_date
        day_end = current_date + timedelta(days=1)

        reservations_result = await db.execute(
            select(RoomReservation)
            .where(RoomReservation.room_id == room_id)
            .where(
                RoomReservation.status.in_([
                    ReservationStatus.pending,
                    ReservationStatus.confirmed,
                    ReservationStatus.checked_in,
                ])
            )
            .where(RoomReservation.start_time >= day_start)
            .where(RoomReservation.start_time < day_end)
            .order_by(RoomReservation.start_time)
        )
        reservations = reservations_result.scalars().all()

        availability_list.append(
            RoomAvailabilityResponse(
                room_id=room.id,
                room_name=room.name,
                date=current_date.strftime("%Y-%m-%d"),
                available_slots=[
                    RoomAvailabilitySlot(
                        start_time=s["start_time"],
                        end_time=s["end_time"],
                        duration_minutes=s["duration_minutes"],
                    )
                    for s in slots
                ],
                reservations=[
                    ReservationBriefResponse(
                        id=r.id,
                        start_time=r.start_time,
                        end_time=r.end_time,
                        status=str(r.status),
                    )
                    for r in reservations
                ],
            )
        )

    return availability_list



# ============================================================================
# Reservation Booking (Authenticated)
# ============================================================================

@router.post("/{room_id}/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_reservation(
    request: Request,
    room_id: int,
    reservation_in: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new room reservation.

    Study rooms and computer labs are auto-approved.
    Meeting rooms and event spaces require staff approval.
    Recurring reservations always require staff approval.
    """
    # Override room_id from path
    if reservation_in.room_id != room_id:
        reservation_in.room_id = room_id

    # Get room with lock to prevent race conditions
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .where(Room.is_active == True)
        .with_for_update()
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Validate reservation rules
    validation_errors = await room_service.validate_reservation_rules(
        db, room, reservation_in.start_time, reservation_in.end_time, current_user
    )
    if validation_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(validation_errors))

    # Check attendee count
    if reservation_in.attendee_count > room.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Attendee count ({reservation_in.attendee_count}) exceeds room capacity ({room.capacity})"
        )

    # Require meeting-room policy acknowledgement when room is approval-gated
    if room.requires_approval and not getattr(reservation_in, "policy_acknowledged", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting room policy must be acknowledged",
        )

    # Per-patron rolling 30-day cap (opt-in; NULL = unlimited)
    cap = getattr(room, "max_bookings_per_patron_per_month", None)
    if cap is not None and current_user is not None:
        existing_count = await room_service.count_patron_room_bookings_last_30_days(
            db, current_user.id, room_id
        )
        if existing_count >= cap:
            reset_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%m/%d/%Y")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Patron has reached the booking limit for this room "
                    f"({cap} per 30 days). Limit resets {reset_date}."
                ),
            )

    # Check availability
    is_available = await room_service.check_room_availability(
        db, room_id, reservation_in.start_time, reservation_in.end_time
    )
    if not is_available:
        conflicts = await room_service.get_conflicting_reservations(
            db, room_id, reservation_in.start_time, reservation_in.end_time
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room is not available for the requested time. {len(conflicts)} conflicting reservation(s) found."
        )

    # Create reservation
    reservation = await room_service.create_reservation(
        db=db,
        room=room,
        patron=current_user,
        start_time=reservation_in.start_time,
        end_time=reservation_in.end_time,
        purpose=reservation_in.purpose,
        attendee_count=reservation_in.attendee_count,
        equipment_requested=reservation_in.equipment_requested,
        contact_name=reservation_in.contact_name,
        contact_email=reservation_in.contact_email or current_user.email,
        contact_phone=reservation_in.contact_phone,
        is_recurring=reservation_in.is_recurring,
        recurrence_pattern=reservation_in.recurrence_pattern,
        recurrence_end_date=reservation_in.recurrence_end_date,
        accommodation_requested=getattr(reservation_in, "accommodation_requested", False) or False,
        accommodation_details=getattr(reservation_in, "accommodation_details", None),
        policy_acknowledged=getattr(reservation_in, "policy_acknowledged", False) or False,
    )

    # Create child reservations for recurring bookings
    if reservation_in.is_recurring:
        await room_service.create_recurring_reservations(db, reservation, room)

    await db.commit()
    await db.refresh(reservation)

    # Send confirmation email
    try:
        await room_service.send_reservation_confirmation(reservation, room, current_user)
        reservation.confirmation_sent_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:  # noqa: BLE001  # best-effort confirmation email — reservation already created
        logger.error(f"Failed to send confirmation email: {e}")

    logger.info(
        "Room reservation created",
        extra={
            "reservation_id": reservation.id,
            "room_id": room_id,
            "patron_id": current_user.id,
            "status": str(reservation.status),
        }
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name,
        patron_name=f"{current_user.first_name} {current_user.last_name}",
    )

@router.get("/{room_id}/availability/range", response_model=list[RoomAvailabilityResponse])
@limiter.limit("30/minute")
async def get_room_availability_range(
    request: Request,
    room_id: int,
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get availability calendar for a room across a date range.

    Returns available time slots for each day in the range, excluding already-booked slots.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    if end <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")

    # Validate date range is not too large (max 90 days)
    date_diff = (end - start).days
    if date_diff > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 90 days"
        )

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Get room
    result = await db.execute(
        select(Room).where(Room.id == room_id).where(Room.is_active == True)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Validate dates are within advance booking limit
    if start < today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot check availability for past dates")

    max_date = today + timedelta(days=room.advance_booking_days)
    if start > max_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check availability more than {room.advance_booking_days} days in advance"
        )

    availability_list = []
    current_date = start

    while current_date < end:
        # Skip dates beyond advance booking limit
        max_date = today + timedelta(days=room.advance_booking_days)
        if current_date > max_date:
            break

        # Get available slots
        slots = await room_service.get_room_availability_slots(db, room, current_date)

        # Get reservations for this date (for display)
        day_start = current_date
        day_end = current_date + timedelta(days=1)

        reservations_result = await db.execute(
            select(RoomReservation)
            .where(RoomReservation.room_id == room_id)
            .where(
                RoomReservation.status.in_([
                    ReservationStatus.pending,
                    ReservationStatus.confirmed,
                    ReservationStatus.checked_in,
                ])
            )
            .where(RoomReservation.start_time >= day_start)
            .where(RoomReservation.start_time < day_end)
            .order_by(RoomReservation.start_time)
        )
        reservations = reservations_result.scalars().all()

        availability_list.append(
            RoomAvailabilityResponse(
                room_id=room.id,
                room_name=room.name,
                date=current_date.strftime("%Y-%m-%d"),
                available_slots=[
                    RoomAvailabilitySlot(
                        start_time=s["start_time"],
                        end_time=s["end_time"],
                        duration_minutes=s["duration_minutes"],
                    )
                    for s in slots
                ],
                reservations=[
                    ReservationBriefResponse(
                        id=r.id,
                        start_time=r.start_time,
                        end_time=r.end_time,
                        status=str(r.status),
                    )
                    for r in reservations
                ],
            )
        )

        current_date += timedelta(days=1)

    return availability_list


