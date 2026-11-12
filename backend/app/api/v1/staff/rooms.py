# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff room management routes."""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.pagination import PaginationParams, calculate_total_pages
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.room import (RecurrencePattern, ReservationStatus, Room,
                            RoomEquipment, RoomReservation, RoomType,
                            RoomUsageStats)
from ....models.user import User
from ....schemas.room import (AccommodationAcknowledge, EquipmentCreate,
                             EquipmentResponse, EquipmentUpdate, NoShowReport,
                             PopularTimesReport, ReservationApproval,
                             ReservationCancellation, ReservationDeny,
                             ReservationDetailResponse, ReservationListResponse,
                             ReservationResponse, RoomCreate, RoomListResponse,
                             RoomResponse, RoomUpdate, RoomUtilizationReport,
                             StaffOverrideCreate, UsageReportResponse)
from ....services import room_service
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/rooms", tags=["staff-rooms"])


# ============================================================================
# Room Management
# ============================================================================

@router.get("", response_model=RoomListResponse)
@limiter.limit("60/minute")
async def list_all_rooms(
    request: Request,
    include_inactive: bool = Query(False, description="Include inactive rooms"),
    room_type: str | None = Query(None),
    branch_id: int | None = Query(None),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all rooms for staff management."""
    query = select(Room)
    count_query = select(func.count(Room.id))

    if not include_inactive:
        query = query.where(Room.is_active == True)
        count_query = count_query.where(Room.is_active == True)

    if room_type:
        try:
            rt = RoomType(room_type)
            query = query.where(Room.room_type == rt)
            count_query = count_query.where(Room.room_type == rt)
        except ValueError:
            logger.warning("Invalid room_type filter ignored: %s", room_type)

    if branch_id:
        query = query.where(Room.branch_id == branch_id)
        count_query = count_query.where(Room.branch_id == branch_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(pagination.offset).limit(pagination.limit).order_by(Room.name)

    result = await db.execute(query)
    rooms = result.scalars().all()

    return {
        "items": [RoomResponse.model_validate(r) for r in rooms],
        "total": total,
        "page": pagination.page,
        "per_page": pagination.page_size,
    }


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_room(
    request: Request,
    room_in: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new room."""
    # Check for duplicate name
    existing = await db.execute(
        select(Room).where(Room.name == room_in.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A room with this name already exists")

    room_data = room_in.model_dump()

    # Convert room_type string to enum
    room_data["room_type"] = RoomType(room_data["room_type"])

    # Handle operating_hours - convert from Pydantic model to dict
    if room_data.get("operating_hours"):
        if hasattr(room_data["operating_hours"], "model_dump"):
            room_data["operating_hours"] = room_data["operating_hours"].model_dump(exclude_none=True)

    # Handle available_equipment - convert from Pydantic models to dicts
    if room_data.get("available_equipment"):
        room_data["available_equipment"] = [
            e.model_dump() if hasattr(e, "model_dump") else e
            for e in room_data["available_equipment"]
        ]

    # Set requires_approval based on room type if not explicitly set
    if room_data["room_type"] in [RoomType.meeting_room, RoomType.event_space]:
        room_data["requires_approval"] = True

    room = Room(**room_data)
    db.add(room)
    await db.commit()
    await db.refresh(room)

    logger.info(
        "Room created by staff",
        extra={"room_id": room.id, "room_name": room.name, "staff_id": current_user.id}
    )

    return RoomResponse.model_validate(room)


@router.get("/{room_id:int}", response_model=RoomResponse)
@limiter.limit("60/minute")
async def get_room_details(
    request: Request,
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get detailed information about a room."""
    room = await get_or_404(db, Room, room_id, "Room not found")

    return RoomResponse.model_validate(room)


@router.put("/{room_id:int}", response_model=RoomResponse)
@limiter.limit("10/minute")
async def update_room(
    request: Request,
    room_id: int,
    room_in: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a room."""
    room = await get_or_404(db, Room, room_id, "Room not found")

    update_data = room_in.model_dump(exclude_unset=True)

    # Convert room_type string to enum if provided
    if "room_type" in update_data and update_data["room_type"]:
        update_data["room_type"] = RoomType(update_data["room_type"])

    # Handle operating_hours
    if "operating_hours" in update_data and update_data["operating_hours"]:
        if hasattr(update_data["operating_hours"], "model_dump"):
            update_data["operating_hours"] = update_data["operating_hours"].model_dump(exclude_none=True)

    # Handle available_equipment
    if "available_equipment" in update_data and update_data["available_equipment"]:
        update_data["available_equipment"] = [
            e.model_dump() if hasattr(e, "model_dump") else e
            for e in update_data["available_equipment"]
        ]

    for field, value in update_data.items():
        setattr(room, field, value)

    await db.commit()
    await db.refresh(room)

    logger.info(
        "Room updated by staff",
        extra={"room_id": room_id, "staff_id": current_user.id}
    )

    return RoomResponse.model_validate(room)


@router.delete("/{room_id:int}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def deactivate_room(
    request: Request,
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Deactivate a room (soft delete)."""
    room = await get_or_404(db, Room, room_id, "Room not found")

    # Check for active reservations
    active_count = await db.execute(
        select(func.count(RoomReservation.id))
        .where(RoomReservation.room_id == room_id)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
            ])
        )
        .where(RoomReservation.start_time >= datetime.now(timezone.utc))
    )
    count = active_count.scalar() or 0

    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot deactivate room with {count} active/upcoming reservations. Cancel them first."
        )

    room.is_active = False
    await db.commit()

    logger.info(
        "Room deactivated by staff",
        extra={"room_id": room_id, "staff_id": current_user.id}
    )

    return None


@router.post("/{room_id:int}/activate")
@limiter.limit("10/minute")
async def activate_room(
    request: Request,
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Reactivate a deactivated room."""
    room = await get_or_404(db, Room, room_id, "Room not found")

    room.is_active = True
    await db.commit()

    logger.info(
        "Room activated by staff",
        extra={"room_id": room_id, "staff_id": current_user.id}
    )

    return {"message": "Room activated successfully"}


# ============================================================================
# Reservation Management
# ============================================================================

@router.get("/reservations/pending", response_model=ReservationListResponse)
@limiter.limit("60/minute")
async def list_pending_reservations(
    request: Request,
    room_id: int | None = Query(None),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all pending reservations awaiting approval."""
    query = (
        select(RoomReservation)
        .where(RoomReservation.status == ReservationStatus.pending)
    )
    count_query = (
        select(func.count(RoomReservation.id))
        .where(RoomReservation.status == ReservationStatus.pending)
    )

    if room_id:
        query = query.where(RoomReservation.room_id == room_id)
        count_query = count_query.where(RoomReservation.room_id == room_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(pagination.offset).limit(pagination.limit).order_by(RoomReservation.created_at)

    result = await db.execute(query)
    reservations = result.scalars().all()

    # Get room and patron info
    room_ids = {r.room_id for r in reservations}
    patron_ids = {r.patron_id for r in reservations if r.patron_id}

    rooms_result = await db.execute(select(Room).where(Room.id.in_(room_ids)))
    rooms_map = {r.id: r for r in rooms_result.scalars().all()}

    patrons_map = {}
    if patron_ids:
        patrons_result = await db.execute(select(User).where(User.id.in_(patron_ids)))
        patrons_map = {p.id: p for p in patrons_result.scalars().all()}

    items = []
    for r in reservations:
        room = rooms_map.get(r.room_id)
        patron = patrons_map.get(r.patron_id) if r.patron_id else None
        items.append(ReservationResponse(
            **{k: v for k, v in r.__dict__.items() if not k.startswith("_")},
            room_name=room.name if room else None,
            patron_name=f"{patron.first_name} {patron.last_name}" if patron else r.contact_name,
        ))

    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "per_page": pagination.page_size,
    }


@router.get("/reservations/all", response_model=ReservationListResponse)
@limiter.limit("60/minute")
async def list_all_reservations(
    request: Request,
    room_id: int | None = Query(None),
    status_filter: str | None = Query(None),
    patron_id: int | None = Query(None),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all reservations with filtering options."""
    query = select(RoomReservation)
    count_query = select(func.count(RoomReservation.id))

    if room_id:
        query = query.where(RoomReservation.room_id == room_id)
        count_query = count_query.where(RoomReservation.room_id == room_id)

    if status_filter:
        try:
            status_enum = ReservationStatus(status_filter)
            query = query.where(RoomReservation.status == status_enum)
            count_query = count_query.where(RoomReservation.status == status_enum)
        except ValueError:
            logger.warning("Invalid reservation status filter ignored: %s", status_filter)

    if patron_id:
        query = query.where(RoomReservation.patron_id == patron_id)
        count_query = count_query.where(RoomReservation.patron_id == patron_id)

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.where(RoomReservation.start_time >= start)
            count_query = count_query.where(RoomReservation.start_time >= start)
        except ValueError:
            logger.warning("Invalid start_date filter ignored: %s", start_date)

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            query = query.where(RoomReservation.start_time < end)
            count_query = count_query.where(RoomReservation.start_time < end)
        except ValueError:
            logger.warning("Invalid end_date filter ignored: %s", end_date)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(pagination.offset).limit(pagination.limit).order_by(RoomReservation.start_time.desc())

    result = await db.execute(query)
    reservations = result.scalars().all()

    # Get room and patron info
    room_ids = {r.room_id for r in reservations}
    patron_ids = {r.patron_id for r in reservations if r.patron_id}

    rooms_result = await db.execute(select(Room).where(Room.id.in_(room_ids)))
    rooms_map = {r.id: r for r in rooms_result.scalars().all()}

    patrons_map = {}
    if patron_ids:
        patrons_result = await db.execute(select(User).where(User.id.in_(patron_ids)))
        patrons_map = {p.id: p for p in patrons_result.scalars().all()}

    items = []
    for r in reservations:
        room = rooms_map.get(r.room_id)
        patron = patrons_map.get(r.patron_id) if r.patron_id else None
        items.append(ReservationResponse(
            **{k: v for k, v in r.__dict__.items() if not k.startswith("_")},
            room_name=room.name if room else None,
            patron_name=f"{patron.first_name} {patron.last_name}" if patron else r.contact_name,
        ))

    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "per_page": pagination.page_size,
    }


@router.get("/reservations/{reservation_id:int}", response_model=ReservationDetailResponse)
@limiter.limit("60/minute")
async def get_reservation_details(
    request: Request,
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get detailed information about a reservation (staff view with internal notes)."""
    reservation = await get_or_404(db, RoomReservation, reservation_id, "Reservation not found")

    # Get room
    room_result = await db.execute(select(Room).where(Room.id == reservation.room_id))
    room = room_result.scalar_one_or_none()

    # Get patron
    patron = None
    if reservation.patron_id:
        patron_result = await db.execute(select(User).where(User.id == reservation.patron_id))
        patron = patron_result.scalar_one_or_none()

    # Get approver
    approver = None
    if reservation.approved_by:
        approver_result = await db.execute(select(User).where(User.id == reservation.approved_by))
        approver = approver_result.scalar_one_or_none()

    # Get child reservations if this is a recurring parent
    child_reservations = None
    if reservation.is_recurring:
        children_result = await db.execute(
            select(RoomReservation)
            .where(RoomReservation.parent_reservation_id == reservation.id)
            .order_by(RoomReservation.start_time)
        )
        children = children_result.scalars().all()
        child_reservations = [
            {"id": c.id, "start_time": c.start_time, "end_time": c.end_time, "status": c.status}
            for c in children
        ]

    return ReservationDetailResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else reservation.contact_name,
        approver_name=f"{approver.first_name} {approver.last_name}" if approver else None,
        room=RoomResponse.model_validate(room) if room else None,
        child_reservations=child_reservations,
    )


@router.post("/reservations/{reservation_id:int}/approve", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def approve_reservation(
    request: Request,
    reservation_id: int,
    approval: ReservationApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Approve or reject a pending reservation."""
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservation is not pending (current status: {reservation.status})"
        )

    # Get room for email
    room_result = await db.execute(select(Room).where(Room.id == reservation.room_id))
    room = room_result.scalar_one_or_none()

    # Get patron
    patron = None
    if reservation.patron_id:
        patron_result = await db.execute(select(User).where(User.id == reservation.patron_id))
        patron = patron_result.scalar_one_or_none()

    if approval.approved:
        # Check for conflicts before approving
        is_available = await room_service.check_room_availability(
            db, reservation.room_id, reservation.start_time, reservation.end_time,
            exclude_reservation_id=reservation_id
        )
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot approve: conflicting reservation exists for this time slot"
            )

        await room_service.approve_reservation(
            db, reservation, current_user, approval.internal_notes
        )
        logger.info(
            "Reservation approved",
            extra={"reservation_id": reservation_id, "approver_id": current_user.id}
        )
    else:
        if not approval.rejection_reason_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rejection_reason_code is required when rejecting a reservation"
            )
        await room_service.reject_reservation(
            db, reservation, current_user,
            reason=approval.rejection_reason,
            internal_notes=approval.internal_notes,
            rejection_reason_code=approval.rejection_reason_code,
        )
        logger.info(
            "Reservation rejected",
            extra={
                "reservation_id": reservation_id,
                "approver_id": current_user.id,
                "reason": approval.rejection_reason
            }
        )

    await db.commit()
    await db.refresh(reservation)

    # Send approval/rejection notification
    if room:
        try:
            await room_service.send_approval_notification(
                reservation, room, approval.approved, approval.rejection_reason, patron
            )
        except Exception as e:  # noqa: BLE001  # best-effort notification — main operation already committed
            logger.error(f"Failed to send approval notification: {e}")

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else reservation.contact_name,
        approver_name=f"{current_user.first_name} {current_user.last_name}",
    )


@router.post("/reservations/{reservation_id:int}/cancel", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def staff_cancel_reservation(
    request: Request,
    reservation_id: int,
    cancellation: ReservationCancellation,
    cancel_future: bool = Query(False, description="Cancel future occurrences"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Cancel a reservation on behalf of the patron."""
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status in [ReservationStatus.cancelled, ReservationStatus.completed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel reservation with status '{reservation.status}'"
        )

    # Get room and patron for email
    room_result = await db.execute(select(Room).where(Room.id == reservation.room_id))
    room = room_result.scalar_one_or_none()

    patron = None
    if reservation.patron_id:
        patron_result = await db.execute(select(User).where(User.id == reservation.patron_id))
        patron = patron_result.scalar_one_or_none()

    await room_service.cancel_reservation(
        db, reservation, current_user, cancellation.reason, cancel_future_occurrences=cancel_future
    )

    await db.commit()
    await db.refresh(reservation)

    # Send cancellation email
    if room:
        try:
            await room_service.send_cancellation_notification(
                reservation, room, cancelled_by_staff=True, reason=cancellation.reason, patron=patron
            )
        except Exception as e:  # noqa: BLE001  # best-effort notification — main operation already committed
            logger.error(f"Failed to send cancellation notification: {e}")

    logger.info(
        "Reservation cancelled by staff",
        extra={
            "reservation_id": reservation_id,
            "staff_id": current_user.id,
            "reason": cancellation.reason
        }
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else reservation.contact_name,
    )


@router.post("/reservations/override", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_override_booking(
    request: Request,
    override: StaffOverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Create a staff override booking that bypasses normal availability checks.

    Use for emergency situations, priority bookings, or administrative needs.
    Existing conflicting reservations will be automatically cancelled.
    """
    # Get room
    room_result = await db.execute(
        select(Room).where(Room.id == override.room_id).with_for_update()
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Get patron if specified
    patron = None
    if override.patron_id:
        patron = await get_or_404(db, User, override.patron_id, "Patron not found")

    # Find and cancel conflicting reservations
    conflicts = await room_service.get_conflicting_reservations(
        db, room.id, override.start_time, override.end_time
    )

    for conflict in conflicts:
        conflict.status = ReservationStatus.cancelled
        conflict.cancelled_at = datetime.now(timezone.utc)
        conflict.cancelled_by = current_user.id
        conflict.cancellation_reason = f"Cancelled due to staff override booking: {override.override_reason}"

        # Send cancellation notification for displaced reservations
        conflict_patron = None
        if conflict.patron_id:
            conflict_patron_result = await db.execute(
                select(User).where(User.id == conflict.patron_id)
            )
            conflict_patron = conflict_patron_result.scalar_one_or_none()

        try:
            await room_service.send_cancellation_notification(
                conflict, room, cancelled_by_staff=True,
                reason="Your reservation has been cancelled to accommodate a priority booking.",
                patron=conflict_patron
            )
        except Exception as e:  # noqa: BLE001  # best-effort notification — main operation already committed
            logger.error(f"Failed to send cancellation notification: {e}")

    # Create the override booking
    reservation = RoomReservation(
        room_id=room.id,
        patron_id=override.patron_id,
        start_time=override.start_time,
        end_time=override.end_time,
        status=ReservationStatus.confirmed,
        purpose=override.purpose,
        attendee_count=1,
        contact_name=override.contact_name or (
            f"{patron.first_name} {patron.last_name}" if patron else f"{current_user.first_name} {current_user.last_name}"
        ),
        contact_email=override.contact_email or (patron.email if patron else current_user.email),
        is_staff_override=True,
        override_reason=override.override_reason,
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
        internal_notes=override.internal_notes,
    )

    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)

    logger.info(
        "Staff override booking created",
        extra={
            "reservation_id": reservation.id,
            "staff_id": current_user.id,
            "conflicts_cancelled": len(conflicts),
            "reason": override.override_reason
        }
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else override.contact_name,
        approver_name=f"{current_user.first_name} {current_user.last_name}",
    )


@router.post("/reservations/{reservation_id:int}/check-in", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def staff_check_in_patron(
    request: Request,
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Check in a patron for their reservation (staff action)."""
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status != ReservationStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in reservation with status '{reservation.status}'"
        )

    reservation.status = ReservationStatus.checked_in
    reservation.checked_in_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(reservation)

    # Get room
    room_result = await db.execute(select(Room).where(Room.id == reservation.room_id))
    room = room_result.scalar_one_or_none()

    logger.info(
        "Staff checked in patron",
        extra={"reservation_id": reservation_id, "staff_id": current_user.id}
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
    )


# ============================================================================
# Equipment Management
# ============================================================================

@router.get("/equipment", response_model=list[EquipmentResponse])
@limiter.limit("60/minute")
async def list_all_equipment(
    request: Request,
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all equipment items."""
    query = select(RoomEquipment)
    if not include_inactive:
        query = query.where(RoomEquipment.is_active == True)
    query = query.order_by(RoomEquipment.name)

    result = await db.execute(query)
    equipment = result.scalars().all()

    return [EquipmentResponse.model_validate(e) for e in equipment]


@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_equipment(
    request: Request,
    equipment_in: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new equipment item."""
    # Check for duplicate code
    existing = await db.execute(
        select(RoomEquipment).where(RoomEquipment.equipment_code == equipment_in.equipment_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Equipment code already exists")

    equipment = RoomEquipment(**equipment_in.model_dump())
    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)

    logger.info(
        "Equipment created",
        extra={"equipment_id": equipment.id, "staff_id": current_user.id}
    )

    return EquipmentResponse.model_validate(equipment)


@router.put("/equipment/{equipment_id:int}", response_model=EquipmentResponse)
@limiter.limit("10/minute")
async def update_equipment(
    request: Request,
    equipment_id: int,
    equipment_in: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an equipment item."""
    equipment = await get_or_404(db, RoomEquipment, equipment_id, "Equipment not found")

    update_data = equipment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(equipment, field, value)

    await db.commit()
    await db.refresh(equipment)

    return EquipmentResponse.model_validate(equipment)


# ============================================================================
# Reports
# ============================================================================

@router.get("/reports/utilization", response_model=list[RoomUtilizationReport])
@limiter.limit("30/minute")
async def get_utilization_report(
    request: Request,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    room_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get room utilization report."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    # Get rooms
    room_query = select(Room).where(Room.is_active == True)
    if room_id:
        room_query = room_query.where(Room.id == room_id)

    rooms_result = await db.execute(room_query)
    rooms = rooms_result.scalars().all()

    reports = []
    for room in rooms:
        stats = await room_service.get_room_utilization_stats(db, room.id, start, end)

        avg_duration = 0
        avg_attendees = 0
        if stats["completed_reservations"] > 0:
            avg_duration = (stats["total_hours_booked"] * 60) / stats["completed_reservations"]
            avg_attendees = stats["total_attendees"] / stats["completed_reservations"]

        reports.append(RoomUtilizationReport(
            room_id=room.id,
            room_name=room.name,
            period_start=start,
            period_end=end,
            total_reservations=stats["total_reservations"],
            completed_reservations=stats["completed_reservations"],
            cancelled_reservations=stats["cancelled_reservations"],
            no_show_count=stats["no_show_count"],
            no_show_rate=stats["no_show_rate"],
            total_hours_available=(end - start).days * 12,  # Assuming 12-hour days
            total_hours_booked=stats["total_hours_booked"],
            utilization_rate=stats["utilization_rate"],
            average_booking_duration_minutes=avg_duration,
            total_attendees=stats["total_attendees"],
            average_attendees_per_booking=avg_attendees,
        ))

    return reports


@router.get("/reports/popular-times", response_model=PopularTimesReport)
@limiter.limit("30/minute")
async def get_popular_times_report(
    request: Request,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    room_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get popular booking times report."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    stats = await room_service.get_popular_times(db, room_id, start, end)

    # Get room name if specified
    room_name = None
    if room_id:
        room_result = await db.execute(select(Room).where(Room.id == room_id))
        room = room_result.scalar_one_or_none()
        room_name = room.name if room else None

    return PopularTimesReport(
        room_id=room_id,
        room_name=room_name,
        day_of_week=stats["by_day"],
        hourly_distribution=stats["by_hour"],
        peak_hour=stats["peak_hour"],
        peak_day=stats["peak_day"],
    )


@router.get("/reports/no-shows", response_model=NoShowReport)
@limiter.limit("30/minute")
async def get_no_show_report(
    request: Request,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get no-show pattern report."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from None

    # Get total reservations and no-shows
    total_result = await db.execute(
        select(func.count(RoomReservation.id))
        .where(RoomReservation.start_time >= start)
        .where(RoomReservation.start_time < end)
        .where(RoomReservation.status.in_([
            ReservationStatus.completed,
            ReservationStatus.no_show,
            ReservationStatus.checked_in,
        ]))
    )
    total = total_result.scalar() or 0

    no_show_result = await db.execute(
        select(func.count(RoomReservation.id))
        .where(RoomReservation.start_time >= start)
        .where(RoomReservation.start_time < end)
        .where(RoomReservation.status == ReservationStatus.no_show)
    )
    no_show_count = no_show_result.scalar() or 0

    # Get by room breakdown
    by_room_result = await db.execute(
        select(
            Room.id,
            Room.name,
            func.count(RoomReservation.id)
        )
        .join(Room, RoomReservation.room_id == Room.id)
        .where(RoomReservation.start_time >= start)
        .where(RoomReservation.start_time < end)
        .where(RoomReservation.status == ReservationStatus.no_show)
        .group_by(Room.id, Room.name)
    )
    by_room = [
        {"room_id": row[0], "room_name": row[1], "no_show_count": row[2]}
        for row in by_room_result.all()
    ]

    # Get by day of week
    dow_result = await db.execute(
        select(
            func.extract("dow", RoomReservation.start_time),
            func.count(RoomReservation.id)
        )
        .where(RoomReservation.start_time >= start)
        .where(RoomReservation.start_time < end)
        .where(RoomReservation.status == ReservationStatus.no_show)
        .group_by(func.extract("dow", RoomReservation.start_time))
    )
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    by_day = {day: 0 for day in day_names}
    for row in dow_result.all():
        by_day[day_names[int(row[0])]] = row[1]

    # Get repeat no-show patrons
    repeat_result = await db.execute(
        select(
            RoomReservation.patron_id,
            User.first_name,
            User.last_name,
            User.email,
            func.count(RoomReservation.id).label("no_show_count")
        )
        .join(User, RoomReservation.patron_id == User.id)
        .where(RoomReservation.start_time >= start)
        .where(RoomReservation.start_time < end)
        .where(RoomReservation.status == ReservationStatus.no_show)
        .group_by(RoomReservation.patron_id, User.first_name, User.last_name, User.email)
        .having(func.count(RoomReservation.id) > 1)
        .order_by(func.count(RoomReservation.id).desc())
        .limit(20)
    )
    repeat_no_shows = [
        {
            "patron_id": row[0],
            "name": f"{row[1]} {row[2]}",
            "email": row[3],
            "no_show_count": row[4]
        }
        for row in repeat_result.all()
    ]

    return NoShowReport(
        period_start=start,
        period_end=end,
        total_reservations=total,
        no_show_count=no_show_count,
        no_show_rate=(no_show_count / total * 100) if total > 0 else 0,
        by_room=by_room,
        by_day_of_week=by_day,
        repeat_no_show_patrons=repeat_no_shows,
    )


@router.get("/equipment/{equipment_id:int}")
async def get_equipment__equipment_id_(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get /equipment/{equipment_id:int} information."""
    from app.models.equipment import Equipment
    from app.schemas.equipment import EquipmentResponse

    stmt = select(Equipment).where(Equipment.id == equipment_id)
    result = await db.execute(stmt)
    equipment = result.scalars().first()

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    return EquipmentResponse.model_validate(equipment)


# ============================================================================
# Structured deny + accommodation acknowledgement
# ============================================================================

@router.post("/reservations/{reservation_id:int}/deny", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def deny_reservation(
    request: Request,
    reservation_id: int,
    deny: ReservationDeny,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Staff: deny a pending reservation with a structured rejection code.

    rejection_reason_code is a controlled, content-neutral category
    (RejectionReason); rejection_reason is supplementary free-text notes.
    """
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservation is not pending (current status: {reservation.status})",
        )

    # Get room and patron for notification
    room_result = await db.execute(select(Room).where(Room.id == reservation.room_id))
    room = room_result.scalar_one_or_none()
    patron = None
    if reservation.patron_id:
        patron_result = await db.execute(select(User).where(User.id == reservation.patron_id))
        patron = patron_result.scalar_one_or_none()

    await room_service.reject_reservation(
        db, reservation, current_user,
        reason=deny.rejection_reason,
        internal_notes=deny.internal_notes,
        rejection_reason_code=deny.rejection_reason_code,
    )

    await db.commit()
    await db.refresh(reservation)

    if room:
        try:
            await room_service.send_approval_notification(
                reservation, room, approved=False,
                rejection_reason=deny.rejection_reason or deny.rejection_reason_code,
                patron=patron,
            )
        except Exception as e:  # noqa: BLE001  # best-effort notification — main operation already committed
            logger.error(f"Failed to send rejection notification: {e}")

    logger.info(
        "Reservation denied",
        extra={
            "reservation_id": reservation_id,
            "approver_id": current_user.id,
            "rejection_reason_code": deny.rejection_reason_code,
        },
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else reservation.contact_name,
        approver_name=f"{current_user.first_name} {current_user.last_name}",
    )


@router.post("/{reservation_id:int}/acknowledge-accommodation", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def acknowledge_accommodation(
    request: Request,
    reservation_id: int,
    payload: AccommodationAcknowledge,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Staff: acknowledge a patron's accommodation request on a reservation.

    Sets accommodation_acknowledged_at and accommodation_acknowledged_by.
    """
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if not reservation.accommodation_requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No accommodation request on this reservation",
        )

    reservation.accommodation_acknowledged_at = datetime.now(timezone.utc)
    reservation.accommodation_acknowledged_by = current_user.id
    if payload.notes:
        # Append to internal_notes rather than overwriting
        prefix = (reservation.internal_notes or "").rstrip()
        sep = "\n\n" if prefix else ""
        reservation.internal_notes = f"{prefix}{sep}[accommodation ack] {payload.notes}"

    await db.commit()
    await db.refresh(reservation)

    room_result = await db.execute(select(Room).where(Room.id == reservation.room_id))
    room = room_result.scalar_one_or_none()
    patron = None
    if reservation.patron_id:
        patron_result = await db.execute(select(User).where(User.id == reservation.patron_id))
        patron = patron_result.scalar_one_or_none()

    logger.info(
        "Accommodation acknowledged",
        extra={"reservation_id": reservation_id, "staff_id": current_user.id},
    )

    return ReservationResponse(
        **{k: v for k, v in reservation.__dict__.items() if not k.startswith("_")},
        room_name=room.name if room else None,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else reservation.contact_name,
    )

