# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for walk-in room management."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .auth import get_current_user
from .dependencies import require_staff
from ...models.room import Room, RoomOccupancySensor, RoomQueue, RoomReservation
from ...models.user import User
from ...services.walk_in_service import (
    auto_release_after_booking_end,
    create_walkin_reservation,
    extend_reservation,
    get_available_walkin_rooms,
    notify_queue_patron,
    record_occupancy_sensor_reading,
    release_room_early,
)

router = APIRouter(prefix="/walk-in", tags=["Walk-in Rooms"])


# Schemas
class WalkInRoomResponse(BaseModel):

    id: int
    name: str
    description: Optional[str]
    room_type: str
    capacity: int
    floor: Optional[str]
    room_number: Optional[str]
    amenities: list[str]
    walk_in_duration_minutes: int
    image_url: Optional[str]

    class Config:
        from_attributes = True


class WalkInReservationRequest(BaseModel):

    room_id: int
    duration_minutes: Optional[int] = Field(None, description="Override room's default duration")


class WalkInReservationResponse(BaseModel):

    status: str  # "confirmed" or "queued"
    reservation_id: Optional[int] = None
    queue_position: Optional[int] = None
    estimated_ready_minutes: Optional[int] = None
    message: str

    class Config:
        from_attributes = True


class ReleaseRoomRequest(BaseModel):

    reservation_id: int


class ExtendReservationRequest(BaseModel):

    reservation_id: int
    additional_minutes: int = Field(15, ge=5, le=60)


class OccupancySensorRequest(BaseModel):

    room_id: int
    is_occupied: bool
    confidence: int = Field(100, ge=0, le=100)
    sensor_type: Optional[str] = None


class QueueDisplayResponse(BaseModel):

    room_id: int
    room_name: str
    queue_length: int
    first_in_queue_wait_minutes: Optional[int]
    rooms_available_now: int


# Endpoints


@router.get("/rooms/available", response_model=list[WalkInRoomResponse])
async def get_available_walkin_rooms_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WalkInRoomResponse]:
    """Get all rooms currently available for walk-in booking."""
    rooms = await get_available_walkin_rooms(db)
    return [WalkInRoomResponse.model_validate(room) for room in rooms]


@router.post("/reservations", response_model=WalkInReservationResponse)
async def create_walkin_reservation_endpoint(
    request: WalkInReservationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WalkInReservationResponse:
    """
    Create a walk-in room reservation.

    If room is available immediately, returns confirmed status.
    If room is busy, adds patron to queue and returns queued status with estimated ready time.
    """
    # Get room
    room = await db.get(Room, request.room_id)
    if not room or not room.is_walkable or not room.walk_in_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is not available for walk-in bookings",
        )

    # Create reservation
    result, status_str = await create_walkin_reservation(
        db,
        room,
        user,
        request.duration_minutes,
    )

    await db.commit()

    if status_str == "confirmed":
        return WalkInReservationResponse(
            status="confirmed",
            reservation_id=result.id,
            message=f"Room {room.name} is ready! Check-in now.",
        )
    else:
        # Security fix: Replace raw SQL with SQLAlchemy ORM to prevent SQL injection
        queue_query = select(RoomQueue).where(
            RoomQueue.room_id == request.room_id,
            RoomQueue.patron_id == user.id
        )
        queue_result = await db.execute(queue_query)
        queue = queue_result.scalar_one_or_none()

        estimated_wait = None
        if queue and queue.estimated_ready_at:
            now = datetime.now(timezone.utc)
            estimated_wait = int((queue.estimated_ready_at - now).total_seconds() / 60)

        return WalkInReservationResponse(
            status="queued",
            queue_position=queue.position if queue else None,
            estimated_ready_minutes=estimated_wait,
            message=f"Added to queue for {room.name}. You'll be notified when room is ready.",
        )


@router.post("/reservations/{reservation_id}/release-early", response_model=dict)
async def release_room_early_endpoint(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Release a room early, making it available for next person."""
    reservation = await db.get(RoomReservation, reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    if reservation.patron_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot release someone else's reservation",
        )

    await release_room_early(db, reservation, user)
    await db.commit()

    room = await db.get(Room, reservation.room_id)
    return {
        "status": "released",
        "message": f"Thank you! {room.name} is now available for others.",
    }


@router.post("/reservations/{reservation_id}/extend", response_model=dict)
async def extend_reservation_endpoint(
    reservation_id: int,
    request: ExtendReservationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Extend a walk-in reservation by additional minutes."""
    reservation = await db.get(RoomReservation, reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    if reservation.patron_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot extend someone else's reservation",
        )

    try:
        extended = await extend_reservation(db, reservation, request.additional_minutes)
        await db.commit()

        await db.get(Room, extended.room_id)
        return {
            "status": "extended",
            "new_end_time": extended.end_time.isoformat(),
            "message": f"Room extended by {request.additional_minutes} minutes until {extended.end_time.strftime('%I:%M %p')}",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/rooms/{room_id}/auto-release", response_model=dict)
async def auto_release_rooms_endpoint(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    """
    Manually trigger auto-release of finished bookings.
    Called by background job periodically.
    """
    released = await auto_release_after_booking_end(db, room_id)
    await db.commit()

    return {
        "status": "processed",
        "released_count": len(released),
        "message": f"Auto-released {len(released)} finished bookings",
    }


@router.post("/sensor-reading", response_model=dict)
async def record_sensor_reading_endpoint(
    request: OccupancySensorRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Record an occupancy sensor reading for a room."""
    room = await db.get(Room, request.room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    sensor = await record_occupancy_sensor_reading(
        db,
        request.room_id,
        request.is_occupied,
        request.confidence,
        request.sensor_type,
    )
    await db.commit()

    return {
        "status": "recorded",
        "sensor_id": sensor.id,
        "message": "Sensor reading recorded",
    }


@router.get("/queue-display/{room_id}", response_model=QueueDisplayResponse)
async def get_queue_display_endpoint(
    room_id: int,
    db: AsyncSession = Depends(get_db),
) -> QueueDisplayResponse:
    """Get queue display info for a specific room."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    # Count queue
    from sqlalchemy import count, select

    queue_query = select(count(RoomQueue.id)).where(
        RoomQueue.room_id == room_id,
        RoomQueue.notified_at == None,
    )
    queue_result = await db.execute(queue_query)
    queue_length = queue_result.scalar() or 0

    # Get first person's wait time
    first_query = select(RoomQueue).where(
        RoomQueue.room_id == room_id,
        RoomQueue.notified_at == None,
    ).order_by(RoomQueue.position).limit(1)
    first_result = await db.execute(first_query)
    first_in_queue = first_result.scalar_one_or_none()

    wait_minutes = None
    if first_in_queue and first_in_queue.estimated_ready_at:
        now = datetime.now(timezone.utc)
        wait_minutes = int((first_in_queue.estimated_ready_at - now).total_seconds() / 60)

    # Count available rooms
    available = await get_available_walkin_rooms(db)
    available_count = len([r for r in available if r.id == room_id])

    return QueueDisplayResponse(
        room_id=room_id,
        room_name=room.name,
        queue_length=queue_length,
        first_in_queue_wait_minutes=wait_minutes,
        rooms_available_now=available_count,
    )


@router.get("/entrance-display", response_model=list[QueueDisplayResponse])
async def get_entrance_display_endpoint(
    db: AsyncSession = Depends(get_db),
) -> list[QueueDisplayResponse]:
    """
    Get display data for entrance showing all walk-in rooms status.
    Used for "Room available NOW" display at entrance.
    """
    # Security fix: Replace raw SQL with SQLAlchemy ORM to prevent SQL injection
    rooms_query = select(Room).where(
        Room.is_walkable == True,
        Room.walk_in_enabled == True,
        Room.is_active == True
    )
    rooms_result = await db.execute(rooms_query)
    rooms = rooms_result.scalars().all()

    displays = []
    for room in rooms:
        from sqlalchemy import count

        queue_query = select(count(RoomQueue.id)).where(
            RoomQueue.room_id == room.id,
            RoomQueue.notified_at == None,
        )
        queue_result = await db.execute(queue_query)
        queue_length = queue_result.scalar() or 0

        # Check if immediately available
        available = await get_available_walkin_rooms(db)
        is_available = any(r.id == room.id for r in available)

        displays.append(
            QueueDisplayResponse(
                room_id=room.id,
                room_name=room.name,
                queue_length=queue_length,
                first_in_queue_wait_minutes=0 if is_available else None,
                rooms_available_now=1 if is_available else 0,
            )
        )

    return displays
