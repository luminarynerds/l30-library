# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..models.room import (
    Room,
    RoomOccupancySensor,
    RoomQueue,
    RoomReservation,
    RoomType,
    ReservationStatus,
)
from ..models.user import User
from .room_service import check_room_availability

logger = get_logger(__name__)
settings = get_settings()

# Constants
WALK_IN_GRACE_MINUTES = 15  # Minutes after booking ends to consider room walkout
QUEUE_NOTIFICATION_TIMEOUT_MINUTES = 5  # How long patron has to accept ready notification


async def get_available_walkin_rooms(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> list[Room]:
    if now is None:
        now = datetime.now(timezone.utc)

    query = (
        select(Room)
        .where(Room.is_active == True)
        .where(Room.is_walkable == True)
        .where(Room.walk_in_enabled == True)
    )

    result = await db.execute(query)
    rooms = result.scalars().all()

    # Filter to only rooms with availability
    available = []
    for room in rooms:
        is_available = await check_room_availability(
            db,
            room.id,
            now,
            now + timedelta(minutes=room.walk_in_duration_minutes),
        )
        if is_available:
            available.append(room)

    return available


async def create_walkin_reservation(
    db: AsyncSession,
    room: Room,
    patron: User,
    duration_minutes: Optional[int] = None,
    now: Optional[datetime] = None,
) -> tuple[RoomReservation, str]:
    if now is None:
        now = datetime.now(timezone.utc)

    if duration_minutes is None:
        duration_minutes = room.walk_in_duration_minutes

    # Check if room is available immediately
    start_time = now
    end_time = now + timedelta(minutes=duration_minutes)

    is_available = await check_room_availability(db, room.id, start_time, end_time)

    # Check current walk-in count
    current_walkins = await _count_active_walkins(db, room.id, now)

    if is_available and current_walkins < room.max_concurrent_walkins:
        # Create reservation immediately
        reservation = RoomReservation(
            room_id=room.id,
            patron_id=patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Walk-in booking",
            attendee_count=1,
            is_walkin=True,
            approved_at=now,
            contact_name=f"{patron.first_name} {patron.last_name}",
            contact_email=patron.email,
        )
        db.add(reservation)
        await db.flush()

        return reservation, "confirmed"
    else:
        # Add to queue
        queue_count = await _count_queue_entries(db, room.id)
        queue_entry = RoomQueue(
            room_id=room.id,
            patron_id=patron.id,
            position=queue_count + 1,
        )
        db.add(queue_entry)
        await db.flush()

        # Estimate when room will be ready
        estimated_ready = await _estimate_room_ready_time(db, room, now, duration_minutes)
        queue_entry.estimated_ready_at = estimated_ready
        await db.flush()

        return None, "queued"


async def release_room_early(
    db: AsyncSession,
    reservation: RoomReservation,
    user: User,
) -> RoomReservation:
    now = datetime.now(timezone.utc)

    reservation.released_early_at = now
    reservation.released_early_by = user.id
    reservation.status = ReservationStatus.completed
    await db.flush()

    # Process next person in queue
    await _process_queue_next(db, reservation.room_id, now)

    return reservation


async def extend_reservation(
    db: AsyncSession,
    reservation: RoomReservation,
    additional_minutes: int = 15,
) -> RoomReservation:
    room = await db.get(Room, reservation.room_id)

    new_end_time = reservation.end_time + timedelta(minutes=additional_minutes)

    # Check if next slot is available
    is_available = await check_room_availability(
        db,
        room.id,
        reservation.end_time,
        new_end_time,
        exclude_reservation_id=reservation.id,
    )

    if not is_available:
        raise ValueError("Cannot extend: room is already booked for next slot")

    reservation.extended_until = new_end_time
    reservation.end_time = new_end_time
    await db.flush()

    return reservation


async def auto_release_after_booking_end(
    db: AsyncSession,
    room_id: int,
    now: Optional[datetime] = None,
) -> list[RoomReservation]:
    if now is None:
        now = datetime.now(timezone.utc)

    # Find reservations that should be auto-released
    grace_end = now - timedelta(minutes=WALK_IN_GRACE_MINUTES)

    query = (
        select(RoomReservation)
        .where(RoomReservation.room_id == room_id)
        .where(RoomReservation.status == ReservationStatus.checked_in)
        .where(RoomReservation.end_time <= grace_end)
        .where(RoomReservation.released_early_at == None)
    )

    result = await db.execute(query)
    reservations = result.scalars().all()

    for reservation in reservations:
        reservation.status = ReservationStatus.completed
        await db.flush()

    # Process queue for next person
    if reservations:
        await _process_queue_next(db, room_id, now)

    return reservations


async def notify_queue_patron(
    db: AsyncSession,
    queue_entry: RoomQueue,
    room: Room,
) -> RoomQueue:
    from ..models.sms import SMSNotificationType
    from ..services.sms_service import SMSService

    now = datetime.now(timezone.utc)
    patron = await db.get(User, queue_entry.patron_id)

    if not patron or not patron.phone:
        logger.warning(
            "Unable to send walk-in queue SMS; missing patron or phone",
            extra={"queue_entry_id": queue_entry.id, "room_id": room.id}
        )
        return queue_entry

    message = (
        f"Your {room.name} reservation is ready! "
        f"You have {QUEUE_NOTIFICATION_TIMEOUT_MINUTES} minutes to accept."
    )

    sms_queue = await SMSService.queue_sms(
        user_id=patron.id,
        phone_number=patron.phone,
        notification_type=SMSNotificationType.WALK_IN_ALERT,
        message=message,
        context_data={
            "room_id": room.id,
            "room_name": room.name,
            "queue_position": queue_entry.position,
        },
        db=db,
        check_opt_out=False,
        check_dnd=False,
    )
    await SMSService.send_queued_sms(sms_queue.id, db)

    queue_entry.notified_at = now
    queue_entry.ready_timeout_at = now + timedelta(minutes=QUEUE_NOTIFICATION_TIMEOUT_MINUTES)
    await db.flush()

    return queue_entry


async def record_occupancy_sensor_reading(
    db: AsyncSession,
    room_id: int,
    is_occupied: bool,
    confidence: int = 100,
    sensor_type: Optional[str] = None,
) -> RoomOccupancySensor:
    # Find active reservation if any
    now = datetime.now(timezone.utc)
    query = (
        select(RoomReservation)
        .where(RoomReservation.room_id == room_id)
        .where(RoomReservation.status.in_([ReservationStatus.confirmed, ReservationStatus.checked_in]))
        .where(RoomReservation.start_time <= now)
        .where(RoomReservation.end_time >= now)
    )
    result = await db.execute(query)
    reservation = result.scalar_one_or_none()

    sensor_reading = RoomOccupancySensor(
        room_id=room_id,
        reservation_id=reservation.id if reservation else None,
        is_occupied=is_occupied,
        confidence=confidence,
        sensor_type=sensor_type,
        last_motion_at=now if is_occupied else None,
    )
    db.add(sensor_reading)
    await db.flush()

    # Update reservation occupancy status if active
    if reservation:
        reservation.occupancy_sensor_active = is_occupied

    return sensor_reading


# Private helper functions


async def _count_active_walkins(
    db: AsyncSession,
    room_id: int,
    now: Optional[datetime] = None,
) -> int:
    if now is None:
        now = datetime.now(timezone.utc)

    query = (
        select(func.count(RoomReservation.id))
        .where(RoomReservation.room_id == room_id)
        .where(RoomReservation.is_walkin == True)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ])
        )
        .where(RoomReservation.start_time <= now)
        .where(RoomReservation.end_time >= now)
    )

    result = await db.execute(query)
    return result.scalar() or 0


async def _count_queue_entries(
    db: AsyncSession,
    room_id: int,
) -> int:
    query = (
        select(func.count(RoomQueue.id))
        .where(RoomQueue.room_id == room_id)
        .where(RoomQueue.notified_at == None)
    )

    result = await db.execute(query)
    return result.scalar() or 0


async def _estimate_room_ready_time(
    db: AsyncSession,
    room: Room,
    now: datetime,
    duration_needed: int,
) -> datetime:
    # Find next available slot
    query = (
        select(RoomReservation)
        .where(RoomReservation.room_id == room.id)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ])
        )
        .where(RoomReservation.start_time >= now)
        .order_by(RoomReservation.start_time)
    )

    result = await db.execute(query)
    reservations = result.scalars().all()

    if not reservations:
        return now

    # Find first gap that fits
    for i, res in enumerate(reservations):
        if i == 0:
            if (res.start_time - now).total_seconds() / 60 >= duration_needed:
                return now

        if i > 0:
            prev_end = reservations[i - 1].end_time
            gap_minutes = (res.start_time - prev_end).total_seconds() / 60
            if gap_minutes >= duration_needed:
                return prev_end

    # Return end of last reservation + grace period
    last_end = reservations[-1].end_time
    return last_end + timedelta(minutes=room.walkout_grace_minutes)


async def _process_queue_next(
    db: AsyncSession,
    room_id: int,
    now: datetime,
) -> Optional[RoomQueue]:
    # Get next person in queue (by position)
    query = (
        select(RoomQueue)
        .where(RoomQueue.room_id == room_id)
        .where(RoomQueue.notified_at == None)
        .order_by(RoomQueue.position)
        .limit(1)
    )

    result = await db.execute(query)
    queue_entry = result.scalar_one_or_none()

    if not queue_entry:
        return None

    room = await db.get(Room, room_id)

    # Notify them
    await notify_queue_patron(db, queue_entry, room)

    return queue_entry


async def notify_queue_patrons(
    db: AsyncSession,
    room_id: int,
) -> int:
    from ..models.sms import SMSNotificationType
    from ..services.sms_service import SMSService

    # Get next queued entry ordered by position
    query = (
        select(RoomQueue)
        .where(RoomQueue.room_id == room_id)
        .where(RoomQueue.notified_at == None)
        .order_by(RoomQueue.position)
        .limit(1)
    )

    result = await db.execute(query)
    queue_entry = result.scalar_one_or_none()

    if not queue_entry:
        return 0

    # Get patron and room info
    patron = await db.get(User, queue_entry.patron_id)
    room = await db.get(Room, room_id)

    if not patron or not room:
        logger.error(
            "Failed to get patron or room for queue notification",
            extra={
                "room_id": room_id,
                "patron_id": queue_entry.patron_id if queue_entry else None,
            }
        )
        return 0

    # Check if patron has phone number
    if not patron.phone:
        logger.warning(
            "Patron has no phone number for walk-in notification",
            extra={
                "patron_id": patron.id,
                "room_id": room_id,
            }
        )
        return 0

    # Construct SMS message
    message = (
        f"Your {room.name} reservation is ready! "
        f"You have {QUEUE_NOTIFICATION_TIMEOUT_MINUTES} minutes to accept."
    )

    # Prepare context data
    context_data = {
        "room_id": room.id,
        "room_name": room.name,
        "queue_position": queue_entry.position,
    }

    try:
        # Send SMS via SMSService
        sms_queue = await SMSService.queue_sms(
            user_id=patron.id,
            phone_number=patron.phone,
            notification_type=SMSNotificationType.WALK_IN_ALERT,
            message=message,
            context_data=context_data,
            check_opt_out=False,  # Emergency notification, bypass opt-out
            check_dnd=False,      # Emergency notification, bypass DND
            db=db,
        )

        # Actually deliver the queued SMS immediately
        await SMSService.send_queued_sms(sms_queue.id, db)

        logger.info(
            "Walk-in SMS notification sent",
            extra={
                "patron_id": patron.id,
                "room_id": room_id,
                "phone": patron.phone[-4:] if patron.phone else None,
            }
        )

        return 1

    except Exception as e:  # noqa: BLE001 - notification boundary — SMS queue failure must not crash walk-in flow
        logger.error(
            "Failed to queue walk-in SMS notification",
            extra={
                "patron_id": patron.id,
                "room_id": room_id,
                "phone": patron.phone[-4:] if patron.phone else None,
                "error": str(e),
            }
        )
        return 0


async def _send_text_notification(
    patron: User,
    message: str,
) -> bool:
    if not patron.phone:
        logger.warning(f"Patron {patron.id} has no phone number for SMS notification")
        return False

    try:
        from ..core.sms import send_sms

        # Send via SMS provider
        response = await send_sms(
            to_phone=patron.phone,
            message=message,
        )

        logger.info(
            f"Walk-in SMS sent to patron {patron.id}",
            extra={
                "patron_id": patron.id,
                "phone": patron.phone[-4:],  # Log last 4 digits only
                "sms_sid": response.get("sid"),
            }
        )
        return True
    except Exception as e:  # noqa: BLE001 - notification boundary — SMS provider failure must not crash walk-in flow
        logger.error(f"Failed to send SMS to {patron.phone[-4:]}: {str(e)}")
        return False
