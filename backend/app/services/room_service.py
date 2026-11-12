# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import COLORS, send_email
from ..core.frontend_routes import routes
from ..models.room import (RecurrencePattern, ReservationStatus, Room,
                           RoomEquipment, RoomReservation, RoomType,
                           RoomUsageStats, RoomWaitlist, RoomWaitlistStatus)
from ..models.user import User

logger = get_logger(__name__)
settings = get_settings()


async def _get_library_timezone(db: AsyncSession) -> ZoneInfo:
    from ..models.multi_branch import LibrarySystem
    result = await db.execute(select(LibrarySystem.timezone).limit(1))
    tz_str = result.scalar_one_or_none()
    try:
        return ZoneInfo(tz_str) if tz_str else ZoneInfo("America/New_York")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("America/New_York")

# Constants
NO_SHOW_GRACE_MINUTES = 15  # Minutes after start time before marking as no-show
REMINDER_HOURS_BEFORE = 24  # Hours before reservation to send reminder


async def _get_room_buffers(db: AsyncSession, room_id: int) -> tuple[int, int]:
    row = await db.execute(
        select(Room.setup_buffer_minutes, Room.teardown_buffer_minutes).where(Room.id == room_id)
    )
    res = row.first()
    if not res:
        return (0, 0)
    setup = int(res[0] or 0)
    teardown = int(res[1] or 0)
    return (setup, teardown)


async def check_room_availability(
    db: AsyncSession,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_reservation_id: int | None = None,
) -> bool:
    setup, teardown = await _get_room_buffers(db, room_id)

    if setup > 0 or teardown > 0:
        # Expand query window to catch existing reservations whose buffered
        # footprint overlaps with the new reservation's buffered footprint.
        # Both existing and new reservations need [setup] before and [teardown] after.
        effective_start = start_time - timedelta(minutes=setup + teardown)
        effective_end = end_time + timedelta(minutes=setup + teardown)
    else:
        effective_start = start_time
        effective_end = end_time

    query = (
        select(RoomReservation)
        .where(RoomReservation.room_id == room_id)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ])
        )
        # Check for overlapping time ranges (buffer-expanded if applicable)
        .where(
            and_(
                RoomReservation.start_time < effective_end,
                RoomReservation.end_time > effective_start,
            )
        )
    )

    if exclude_reservation_id:
        query = query.where(RoomReservation.id != exclude_reservation_id)

    result = await db.execute(query)
    conflicting = result.scalars().first()

    return conflicting is None


async def get_conflicting_reservations(
    db: AsyncSession,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_reservation_id: int | None = None,
) -> list[RoomReservation]:
    setup, teardown = await _get_room_buffers(db, room_id)
    if setup > 0 or teardown > 0:
        # Expand query window to catch existing reservations whose buffered
        # footprint overlaps with the new reservation's buffered footprint.
        # Both existing and new reservations need [setup] before and [teardown] after.
        effective_start = start_time - timedelta(minutes=setup + teardown)
        effective_end = end_time + timedelta(minutes=setup + teardown)
    else:
        effective_start = start_time
        effective_end = end_time

    query = (
        select(RoomReservation)
        .where(RoomReservation.room_id == room_id)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ])
        )
        .where(
            and_(
                RoomReservation.start_time < effective_end,
                RoomReservation.end_time > effective_start,
            )
        )
    )

    if exclude_reservation_id:
        query = query.where(RoomReservation.id != exclude_reservation_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def count_patron_room_bookings_last_30_days(
    db: AsyncSession,
    patron_id: int,
    room_id: int,
) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    result = await db.execute(
        select(func.count(RoomReservation.id))
        .where(RoomReservation.patron_id == patron_id)
        .where(RoomReservation.room_id == room_id)
        .where(RoomReservation.start_time >= cutoff)
        .where(RoomReservation.status.in_([
            ReservationStatus.pending,
            ReservationStatus.confirmed,
            ReservationStatus.checked_in,
        ]))
    )
    return int(result.scalar() or 0)


async def validate_reservation_rules(
    db: AsyncSession,
    room: Room,
    start_time: datetime,
    end_time: datetime,
    user: User | None = None,
    exclude_reservation_id: int | None = None,
) -> list[str]:
    errors = []
    now = datetime.now(timezone.utc)

    # Ensure start_time and end_time are timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Check if room is active
    if not room.is_active:
        errors.append("This room is not available for reservations")
        return errors

    # Check duration
    duration_minutes = (end_time - start_time).total_seconds() / 60
    if duration_minutes < room.min_duration_minutes:
        errors.append(
            f"Minimum reservation duration is {room.min_duration_minutes} minutes"
        )
    if duration_minutes > room.max_duration_minutes:
        errors.append(
            f"Maximum reservation duration is {room.max_duration_minutes} minutes"
        )

    # Check advance booking time
    if start_time < now:
        errors.append("Cannot book in the past")
    else:
        hours_until = (start_time - now).total_seconds() / 3600
        if hours_until < room.min_advance_hours:
            errors.append(
                f"Reservations must be made at least {room.min_advance_hours} hours in advance"
            )

        days_until = (start_time.date() - now.date()).days
        if days_until > room.advance_booking_days:
            errors.append(
                f"Cannot book more than {room.advance_booking_days} days in advance"
            )

    # Check operating hours if defined
    if room.operating_hours:
        # Convert UTC times to library local time for operating hours comparison
        local_tz = await _get_library_timezone(db)
        local_start = start_time.astimezone(local_tz)
        local_end = end_time.astimezone(local_tz)

        day_name = local_start.strftime("%A").lower()
        day_hours = room.operating_hours.get(day_name)

        if not day_hours:
            errors.append(f"Room is closed on {local_start.strftime('%A')}")
        else:
            open_time = datetime.strptime(day_hours.get("open", "00:00"), "%H:%M").time()
            close_time = datetime.strptime(day_hours.get("close", "23:59"), "%H:%M").time()

            if local_start.time() < open_time:
                errors.append(f"Room opens at {day_hours['open']}")
            if local_end.time() > close_time:
                errors.append(f"Room closes at {day_hours['close']}")

    # Check patron-specific rules if user provided
    if user:
        # Check 1 reservation per day rule for patrons
        same_day_query = (
            select(RoomReservation)
            .where(RoomReservation.patron_id == user.id)
            .where(RoomReservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ]))
            .where(func.date(RoomReservation.start_time) == start_time.date())
        )

        if exclude_reservation_id:
            same_day_query = same_day_query.where(RoomReservation.id != exclude_reservation_id)

        result = await db.execute(same_day_query)
        existing_today = result.scalar_one_or_none()

        if existing_today:
            errors.append("You already have a reservation for this day. Maximum 1 reservation per day per patron.")

    return errors


async def create_reservation(
    db: AsyncSession,
    room: Room,
    patron: User | None,
    start_time: datetime,
    end_time: datetime,
    purpose: str | None = None,
    attendee_count: int = 1,
    equipment_requested: list[str] | None = None,
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    is_recurring: bool = False,
    recurrence_pattern: str | None = None,
    recurrence_end_date: datetime | None = None,
    accommodation_requested: bool = False,
    accommodation_details: str | None = None,
    policy_acknowledged: bool = False,
) -> RoomReservation:
    # Determine initial status based on room type
    if room.requires_approval or room.room_type in [RoomType.meeting_room, RoomType.event_space]:
        initial_status = ReservationStatus.pending
    else:
        initial_status = ReservationStatus.confirmed

    # For recurring reservations, always require approval
    if is_recurring:
        initial_status = ReservationStatus.pending

    now_utc = datetime.now(timezone.utc)
    reservation = RoomReservation(
        room_id=room.id,
        patron_id=patron.id if patron else None,
        start_time=start_time,
        end_time=end_time,
        status=initial_status,
        purpose=purpose,
        attendee_count=attendee_count,
        equipment_requested=equipment_requested or [],
        contact_name=contact_name or (f"{patron.first_name} {patron.last_name}" if patron else None),
        contact_email=contact_email or (patron.email if patron else None),
        contact_phone=contact_phone,
        is_recurring=is_recurring or False,
        is_staff_override=False,
        recurrence_pattern=RecurrencePattern(recurrence_pattern) if recurrence_pattern else None,
        recurrence_end_date=recurrence_end_date,
        accommodation_requested=bool(accommodation_requested),
        accommodation_details=accommodation_details,
        policy_acknowledged=bool(policy_acknowledged),
        policy_acknowledged_at=now_utc if policy_acknowledged else None,
    )

    db.add(reservation)
    await db.flush()

    # If auto-approved, mark approval time
    if initial_status == ReservationStatus.confirmed:
        reservation.approved_at = datetime.now(timezone.utc)

    return reservation


async def create_recurring_reservations(
    db: AsyncSession,
    parent_reservation: RoomReservation,
    room: Room,
) -> list[RoomReservation]:
    if not parent_reservation.is_recurring or not parent_reservation.recurrence_pattern:
        return []

    child_reservations = []
    current_date = parent_reservation.start_time
    end_date = parent_reservation.recurrence_end_date
    duration = parent_reservation.end_time - parent_reservation.start_time

    # Determine interval based on pattern
    if parent_reservation.recurrence_pattern == RecurrencePattern.daily:
        interval = timedelta(days=1)
    elif parent_reservation.recurrence_pattern == RecurrencePattern.weekly:
        interval = timedelta(weeks=1)
    elif parent_reservation.recurrence_pattern == RecurrencePattern.biweekly:
        interval = timedelta(weeks=2)
    elif parent_reservation.recurrence_pattern == RecurrencePattern.monthly:
        interval = timedelta(days=30)  # Approximate
    else:
        return []

    # Skip the first occurrence (already created as parent)
    current_date += interval

    while current_date <= end_date:
        child_start = current_date
        child_end = current_date + duration

        # Check availability for this occurrence
        is_available = await check_room_availability(
            db, room.id, child_start, child_end
        )

        if is_available:
            child = RoomReservation(
                room_id=room.id,
                patron_id=parent_reservation.patron_id,
                start_time=child_start,
                end_time=child_end,
                status=ReservationStatus.pending,
                purpose=parent_reservation.purpose,
                attendee_count=parent_reservation.attendee_count,
                equipment_requested=parent_reservation.equipment_requested,
                contact_name=parent_reservation.contact_name,
                contact_email=parent_reservation.contact_email,
                contact_phone=parent_reservation.contact_phone,
                is_recurring=False,  # Children are not marked as recurring
                parent_reservation_id=parent_reservation.id,
            )
            db.add(child)
            child_reservations.append(child)

        current_date += interval

    return child_reservations


async def approve_reservation(
    db: AsyncSession,
    reservation: RoomReservation,
    approver: User,
    internal_notes: str | None = None,
) -> RoomReservation:
    reservation.status = ReservationStatus.confirmed
    reservation.approved_by = approver.id
    reservation.approved_at = datetime.now(timezone.utc)
    if internal_notes:
        reservation.internal_notes = internal_notes

    # If this is a parent recurring reservation, approve all children
    if reservation.is_recurring:
        await db.execute(
            text("""
                UPDATE room_reservations
                SET status = :status, approved_by = :approver, approved_at = :approved_at
                WHERE parent_reservation_id = :parent_id AND status = 'pending'
            """),
            {
                "status": ReservationStatus.confirmed.value,
                "approver": approver.id,
                "approved_at": datetime.now(timezone.utc),
                "parent_id": reservation.id,
            }
        )

    return reservation


async def reject_reservation(
    db: AsyncSession,
    reservation: RoomReservation,
    approver: User,
    reason: str | None = None,
    internal_notes: str | None = None,
    rejection_reason_code: str | None = None,
) -> RoomReservation:
    from ..models.room import RejectionReason
    reservation.status = ReservationStatus.rejected
    reservation.approved_by = approver.id
    reservation.approved_at = datetime.now(timezone.utc)
    reservation.rejection_reason = reason
    if rejection_reason_code:
        reservation.rejection_reason_code = RejectionReason(rejection_reason_code)
    if internal_notes:
        reservation.internal_notes = internal_notes

    # If this is a parent recurring reservation, reject all children
    if reservation.is_recurring:
        await db.execute(
            text("""
                UPDATE room_reservations
                SET status = :status, approved_by = :approver, approved_at = :approved_at,
                    rejection_reason = :reason
                WHERE parent_reservation_id = :parent_id AND status = 'pending'
            """),
            {
                "status": ReservationStatus.rejected.value,
                "approver": approver.id,
                "approved_at": datetime.now(timezone.utc),
                "reason": reason,
                "parent_id": reservation.id,
            }
        )

    return reservation


async def cancel_reservation(
    db: AsyncSession,
    reservation: RoomReservation,
    cancelled_by: User | None,
    reason: str | None = None,
    cancel_future_occurrences: bool = False,
) -> RoomReservation:
    reservation.status = ReservationStatus.cancelled
    reservation.cancelled_at = datetime.now(timezone.utc)
    reservation.cancelled_by = cancelled_by.id if cancelled_by else None
    reservation.cancellation_reason = reason

    # Optionally cancel future occurrences of recurring reservation
    if cancel_future_occurrences and reservation.parent_reservation_id:
        now = datetime.now(timezone.utc)
        await db.execute(
            text("""
                UPDATE room_reservations
                SET status = :status, cancelled_at = :cancelled_at, cancelled_by = :cancelled_by,
                    cancellation_reason = :reason
                WHERE parent_reservation_id = :parent_id
                AND start_time > :now
                AND status IN ('pending', 'confirmed')
            """),
            {
                "status": ReservationStatus.cancelled.value,
                "cancelled_at": now,
                "cancelled_by": cancelled_by.id if cancelled_by else None,
                "reason": reason,
                "parent_id": reservation.parent_reservation_id,
                "now": now,
            }
        )

    # Notify waitlisted patrons of the freed time slot
    room_result = await db.execute(
        select(Room).where(Room.id == reservation.room_id)
    )
    room = room_result.scalar_one_or_none()

    if room:
        await notify_waitlist_if_available(
            db, room,
            reservation.start_time,
            reservation.end_time
        )

    return reservation


async def check_in_reservation(
    db: AsyncSession,
    reservation: RoomReservation,
) -> RoomReservation:
    if reservation.status != ReservationStatus.confirmed:
        raise ValueError("Only confirmed reservations can be checked in")

    now = datetime.now(timezone.utc)

    # Allow check-in up to 15 minutes early
    earliest_checkin = reservation.start_time - timedelta(minutes=15)
    if now < earliest_checkin:
        raise ValueError("Check-in is not yet available. Please return closer to your reservation time.")

    # Check if reservation has already passed the no-show window
    no_show_cutoff = reservation.start_time + timedelta(minutes=NO_SHOW_GRACE_MINUTES)
    if now > no_show_cutoff and reservation.checked_in_at is None:
        raise ValueError("This reservation has expired due to no check-in")

    reservation.status = ReservationStatus.checked_in
    reservation.checked_in_at = now

    return reservation


async def add_to_waitlist(
    db: AsyncSession,
    room: Room,
    patron: User,
    desired_start_time: datetime,
    desired_end_time: datetime,
    waitlist_duration_days: int = 7,
) -> RoomWaitlist:
    waitlist_entry = RoomWaitlist(
        room_id=room.id,
        patron_id=patron.id,
        desired_start_time=desired_start_time,
        desired_end_time=desired_end_time,
        expires_at=datetime.now(timezone.utc) + timedelta(days=waitlist_duration_days),
    )
    db.add(waitlist_entry)
    return waitlist_entry


async def get_active_waitlist(
    db: AsyncSession,
    room_id: int,
) -> list[RoomWaitlist]:
    result = await db.execute(
        select(RoomWaitlist)
        .where(RoomWaitlist.room_id == room_id)
        .where(RoomWaitlist.status == RoomWaitlistStatus.pending)
        .where(RoomWaitlist.expires_at > datetime.now(timezone.utc))
        .order_by(RoomWaitlist.created_at)
    )
    return list(result.scalars().all())


async def get_waitlist_position(
    db: AsyncSession,
    waitlist_entry: RoomWaitlist,
) -> int:
    result = await db.execute(
        select(func.count(RoomWaitlist.id) + 1)
        .where(RoomWaitlist.room_id == waitlist_entry.room_id)
        .where(RoomWaitlist.status == RoomWaitlistStatus.pending)
        .where(RoomWaitlist.expires_at > datetime.now(timezone.utc))
        .where(RoomWaitlist.created_at < waitlist_entry.created_at)
    )
    position = result.scalar() or 1
    return position


async def notify_waitlist_if_available(
    db: AsyncSession,
    room: Room,
    released_start_time: datetime,
    released_end_time: datetime,
) -> int:
    waitlist = await get_active_waitlist(db, room.id)
    notified_count = 0

    for entry in waitlist:
        # Check if the released slot matches the patron's desired time
        # Allow flexibility: released slot overlaps with desired window
        if (released_start_time < entry.desired_end_time and
            released_end_time > entry.desired_start_time):

            # Check if slot is still available
            is_available = await check_room_availability(
                db, room.id, released_start_time, released_end_time
            )

            if is_available:
                entry.status = RoomWaitlistStatus.notified
                entry.notified_at = datetime.now(timezone.utc)

                # Send notification email
                patron_result = await db.execute(
                    select(User).where(User.id == entry.patron_id)
                )
                patron = patron_result.scalar_one_or_none()

                if patron:
                    await send_waitlist_notification(
                        entry, room, patron,
                        released_start_time, released_end_time
                    )
                    notified_count += 1

    return notified_count


async def expire_old_waitlist_entries(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RoomWaitlist)
        .where(RoomWaitlist.status == RoomWaitlistStatus.pending)
        .where(RoomWaitlist.expires_at <= now)
        .with_for_update()
    )
    expired = result.scalars().all()

    for entry in expired:
        entry.status = RoomWaitlistStatus.expired

    return len(expired)


async def process_no_shows(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    no_show_cutoff = now - timedelta(minutes=NO_SHOW_GRACE_MINUTES)

    # Find confirmed reservations that started but weren't checked in
    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.status == ReservationStatus.confirmed)
        .where(RoomReservation.start_time <= no_show_cutoff)
        .where(RoomReservation.checked_in_at.is_(None))
        .with_for_update()
    )
    no_shows = result.scalars().all()

    for reservation in no_shows:
        reservation.status = ReservationStatus.no_show

        # Track no-show count for patron (atomic SQL increment)
        if reservation.patron_id:
            await db.execute(
                update(User)
                .where(User.id == reservation.patron_id)
                .values(room_reservation_no_show_count=func.coalesce(User.room_reservation_no_show_count, 0) + 1)
            )

        # Notify waitlist when a slot becomes available - room becomes available for walk-ins
        room_result = await db.execute(
            select(Room).where(Room.id == reservation.room_id)
        )
        room = room_result.scalar_one_or_none()

        if room:
            await notify_waitlist_if_available(
                db, room,
                reservation.start_time,
                reservation.end_time
            )

        logger.info(
            f"Marked reservation {reservation.id} as no-show",
            extra={"room_id": reservation.room_id, "patron_id": reservation.patron_id}
        )

    return len(no_shows)


async def complete_finished_reservations(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.status == ReservationStatus.checked_in)
        .where(RoomReservation.end_time <= now)
        .with_for_update()
    )
    finished = result.scalars().all()

    for reservation in finished:
        reservation.status = ReservationStatus.completed

    return len(finished)


async def get_upcoming_reminders(
    db: AsyncSession,
    hours_ahead: int = REMINDER_HOURS_BEFORE,
) -> list[RoomReservation]:
    now = datetime.now(timezone.utc)
    reminder_window = now + timedelta(hours=hours_ahead)

    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.status == ReservationStatus.confirmed)
        .where(RoomReservation.start_time > now)
        .where(RoomReservation.start_time <= reminder_window)
        .where(RoomReservation.reminder_sent_at.is_(None))
    )

    return list(result.scalars().all())


async def get_room_availability_slots(
    db: AsyncSession,
    room: Room,
    date: datetime,
    slot_duration_minutes: int = 30,
) -> list[dict[str, Any]]:
    local_tz = await _get_library_timezone(db)

    # Get operating hours for this day
    day_name = date.strftime("%A").lower()
    if room.operating_hours:
        day_hours = room.operating_hours.get(day_name)
        if not day_hours:
            return []  # Closed this day
        open_time = datetime.strptime(day_hours.get("open", "09:00"), "%H:%M").time()
        close_time = datetime.strptime(day_hours.get("close", "21:00"), "%H:%M").time()
    else:
        # Default hours if not specified
        open_time = datetime.strptime("09:00", "%H:%M").time()
        close_time = datetime.strptime("21:00", "%H:%M").time()

    # Interpret operating hours in library's local timezone, then convert to UTC
    day_start = datetime.combine(date.date(), open_time, tzinfo=local_tz).astimezone(timezone.utc)
    day_end = datetime.combine(date.date(), close_time, tzinfo=local_tz).astimezone(timezone.utc)

    result = await db.execute(
        select(RoomReservation)
        .where(RoomReservation.room_id == room.id)
        .where(
            RoomReservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
                ReservationStatus.checked_in,
            ])
        )
        .where(RoomReservation.start_time < day_end)
        .where(RoomReservation.end_time > day_start)
        .order_by(RoomReservation.start_time)
    )
    reservations = list(result.scalars().all())

    # Collect free gaps between reservations
    gaps = []
    current_time = day_start

    for reservation in reservations:
        if reservation.start_time > current_time:
            gaps.append((current_time, reservation.start_time))
        current_time = max(current_time, reservation.end_time)

    if current_time < day_end:
        gaps.append((current_time, day_end))

    # Subdivide each gap into bookable slots
    slot_delta = timedelta(minutes=slot_duration_minutes)
    available_slots = []

    for gap_start, gap_end in gaps:
        slot_start = gap_start
        while slot_start + slot_delta <= gap_end:
            slot_end = slot_start + slot_delta
            remaining = int((gap_end - slot_start).total_seconds() / 60)
            available_slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
                "duration_minutes": slot_duration_minutes,
                "max_available_minutes": remaining,
            })
            slot_start += slot_delta

    return available_slots


async def get_room_utilization_stats(
    db: AsyncSession,
    room_id: int,
    start_date: datetime,
    end_date: datetime,
) -> dict[str, Any]:
    # Count reservations by status
    result = await db.execute(
        select(
            RoomReservation.status,
            func.count(RoomReservation.id),
            func.sum(
                func.extract("epoch", RoomReservation.end_time - RoomReservation.start_time) / 3600
            ),
            func.sum(RoomReservation.attendee_count),
        )
        .where(RoomReservation.room_id == room_id)
        .where(RoomReservation.start_time >= start_date)
        .where(RoomReservation.start_time < end_date)
        .group_by(RoomReservation.status)
    )

    stats = {
        "total_reservations": 0,
        "completed_reservations": 0,
        "cancelled_reservations": 0,
        "no_show_count": 0,
        "total_hours_booked": 0,
        "total_attendees": 0,
    }

    for row in result.all():
        status, count, hours, attendees = row
        stats["total_reservations"] += count or 0
        if status == ReservationStatus.completed:
            stats["completed_reservations"] = count or 0
            stats["total_hours_booked"] = float(hours or 0)
            stats["total_attendees"] = attendees or 0
        elif status == ReservationStatus.cancelled:
            stats["cancelled_reservations"] = count or 0
        elif status == ReservationStatus.no_show:
            stats["no_show_count"] = count or 0

    # Calculate rates
    if stats["total_reservations"] > 0:
        stats["no_show_rate"] = (stats["no_show_count"] / stats["total_reservations"]) * 100
        stats["cancellation_rate"] = (stats["cancelled_reservations"] / stats["total_reservations"]) * 100
    else:
        stats["no_show_rate"] = 0
        stats["cancellation_rate"] = 0

    # Calculate utilization (assuming 12-hour days)
    total_days = (end_date - start_date).days or 1
    total_available_hours = total_days * 12  # Assuming 12-hour operating day
    stats["utilization_rate"] = (stats["total_hours_booked"] / total_available_hours) * 100 if total_available_hours > 0 else 0

    return stats


async def get_popular_times(
    db: AsyncSession,
    room_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    query = select(
        func.extract("dow", RoomReservation.start_time).label("day_of_week"),
        func.extract("hour", RoomReservation.start_time).label("hour"),
        func.count(RoomReservation.id),
    ).where(
        RoomReservation.status.in_([
            ReservationStatus.completed,
            ReservationStatus.checked_in,
            ReservationStatus.confirmed,
        ])
    )

    if room_id:
        query = query.where(RoomReservation.room_id == room_id)
    if start_date:
        query = query.where(RoomReservation.start_time >= start_date)
    if end_date:
        query = query.where(RoomReservation.start_time < end_date)

    query = query.group_by("day_of_week", "hour")

    result = await db.execute(query)

    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    by_day = {day: 0 for day in day_names}
    by_hour = {f"{h:02d}": 0 for h in range(24)}

    for row in result.all():
        dow, hour, count = row
        by_day[day_names[int(dow)]] += count
        by_hour[f"{int(hour):02d}"] += count

    peak_day = max(by_day, key=by_day.get)
    peak_hour = max(by_hour, key=by_hour.get)

    return {
        "by_day": by_day,
        "by_hour": by_hour,
        "peak_day": peak_day,
        "peak_hour": peak_hour,
    }


# ============================================================================
# Email Functions
# ============================================================================

async def send_waitlist_notification(
    waitlist_entry: RoomWaitlist,
    room: Room,
    patron: User,
    available_start_time: datetime,
    available_end_time: datetime,
) -> bool:
    if not patron.email:
        return False

    start_formatted = available_start_time.strftime("%A, %B %d, %Y at %I:%M %p")
    end_formatted = available_end_time.strftime("%I:%M %p")
    name = patron.first_name

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Great News! A Room Became Available</h2>
        <p>Hi {name},</p>
        <p>The {room.name} has become available during a time you're interested in!</p>

        <div style="background-color: #D4EDDA; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #155724; margin-top: 0;">{room.name}</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: #155724;">Date & Time:</td>
                    <td style="padding: 10px 0; color: #155724;">{start_formatted} - {end_formatted}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: #155724;">Capacity:</td>
                    <td style="padding: 10px 0; color: #155724;">{room.capacity} people</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            This slot will only be held for a short time, so book quickly to secure it!
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.room_book, id=room.id)}?start={available_start_time.isoformat()}&end={available_end_time.isoformat()}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Book This Time Slot
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """

    return await send_email(patron.email, f"Room Available: {room.name}", html)


async def send_reservation_confirmation(
    reservation: RoomReservation,
    room: Room,
    patron: User | None = None,
) -> bool:
    email = reservation.contact_email or (patron.email if patron else None)
    if not email:
        return False

    name = reservation.contact_name or (patron.first_name if patron else "Guest")
    start_formatted = reservation.start_time.strftime("%A, %B %d, %Y at %I:%M %p")
    end_formatted = reservation.end_time.strftime("%I:%M %p")

    equipment_section = ""
    if reservation.equipment_requested:
        equipment_list = ", ".join(reservation.equipment_requested)
        equipment_section = f"""
        <tr>
            <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Equipment:</td>
            <td style="padding: 10px 0; color: {COLORS['body']};">{equipment_list}</td>
        </tr>"""

    status_message = ""
    if reservation.status == ReservationStatus.pending:
        status_message = """
        <p style="background-color: #FFF3CD; padding: 15px; border-radius: 5px; color: #856404;">
            <strong>Note:</strong> Your reservation is pending approval. You will receive another
            email once it has been reviewed by staff.
        </p>"""
    else:
        status_message = """
        <p style="background-color: #D4EDDA; padding: 15px; border-radius: 5px; color: #155724;">
            <strong>Confirmed!</strong> Your reservation has been automatically approved.
            Please remember to check in when you arrive.
        </p>"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Room Reservation {
            'Request Received' if reservation.status == ReservationStatus.pending else 'Confirmed'
        }</h2>
        <p>Hi {name},</p>
        <p>Thank you for your room reservation at {settings.app_name}.</p>

        {status_message}

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{room.name}</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Date & Time:</td>
                    <td style="padding: 10px 0; color: {COLORS['body']};">{start_formatted} - {end_formatted}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Room:</td>
                    <td style="padding: 10px 0; color: {COLORS['body']};">{room.name} (Capacity: {room.capacity})</td>
                </tr>
                {equipment_section}
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Attendees:</td>
                    <td style="padding: 10px 0; color: {COLORS['body']};">{reservation.attendee_count}</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            <strong>Important:</strong> Please check in at the front desk or kiosk within 15 minutes
            of your reservation start time. Reservations not checked in may be released to other patrons.
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.rooms_my_reservations)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Reservations
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """

    subject = f"Room Reservation {'Request' if reservation.status == ReservationStatus.pending else 'Confirmation'}: {room.name}"
    return await send_email(email, subject, html)


async def send_reservation_reminder(
    reservation: RoomReservation,
    room: Room,
    patron: User | None = None,
) -> bool:
    email = reservation.contact_email or (patron.email if patron else None)
    if not email:
        return False

    name = reservation.contact_name or (patron.first_name if patron else "Guest")
    start_formatted = reservation.start_time.strftime("%A, %B %d, %Y at %I:%M %p")

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Reservation Reminder</h2>
        <p>Hi {name},</p>
        <p>This is a friendly reminder about your upcoming room reservation.</p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{room.name}</h3>
            <p style="font-size: 18px; color: {COLORS['body']};">
                <strong>{start_formatted}</strong>
            </p>
        </div>

        <p style="color: {COLORS['body']};">
            <strong>Remember:</strong> Please check in at the front desk or kiosk within 15 minutes
            of your reservation start time to avoid your reservation being released.
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.rooms_my_reservations)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View Reservation
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            Need to cancel? Visit your reservations page or contact us.
        </p>
    </div>
    """

    return await send_email(email, f"Reminder: Room Reservation Tomorrow - {room.name}", html)


async def send_approval_notification(
    reservation: RoomReservation,
    room: Room,
    approved: bool,
    reason: str | None = None,
    patron: User | None = None,
) -> bool:
    email = reservation.contact_email or (patron.email if patron else None)
    if not email:
        return False

    name = reservation.contact_name or (patron.first_name if patron else "Guest")
    start_formatted = reservation.start_time.strftime("%A, %B %d, %Y at %I:%M %p")

    if approved:
        status_section = """
        <div style="background-color: #D4EDDA; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #155724; margin-top: 0;">✓ Reservation Approved!</h3>
            <p style="color: #155724; margin-bottom: 0;">
                Your room reservation has been approved. You're all set!
            </p>
        </div>"""
        subject = f"Reservation Approved: {room.name} - {start_formatted}"
    else:
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        status_section = f"""
        <div style="background-color: #F8D7DA; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #721C24; margin-top: 0;">Reservation Not Approved</h3>
            <p style="color: #721C24;">
                We're sorry, but your room reservation request could not be approved at this time.
            </p>
            {reason_text}
        </div>"""
        subject = f"Reservation Update: {room.name}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Room Reservation Update</h2>
        <p>Hi {name},</p>

        {status_section}

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{room.name}</h3>
            <p style="color: {COLORS['body']};">
                <strong>{start_formatted}</strong>
            </p>
        </div>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.rooms)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Browse Rooms
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            Questions? Contact us for assistance.
        </p>
    </div>
    """

    return await send_email(email, subject, html)


async def send_cancellation_notification(
    reservation: RoomReservation,
    room: Room,
    cancelled_by_staff: bool = False,
    reason: str | None = None,
    patron: User | None = None,
) -> bool:
    email = reservation.contact_email or (patron.email if patron else None)
    if not email:
        return False

    name = reservation.contact_name or (patron.first_name if patron else "Guest")
    start_formatted = reservation.start_time.strftime("%A, %B %d, %Y at %I:%M %p")

    if cancelled_by_staff:
        intro = "Your room reservation has been cancelled by library staff."
        reason_section = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
    else:
        intro = "Your room reservation has been cancelled as requested."
        reason_section = ""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Reservation Cancelled</h2>
        <p>Hi {name},</p>
        <p>{intro}</p>
        {reason_section}

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{room.name}</h3>
            <p style="color: {COLORS['body']};">
                <strong>{start_formatted}</strong>
            </p>
        </div>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.rooms)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Book Another Room
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}
        </p>
    </div>
    """

    return await send_email(email, f"Reservation Cancelled: {room.name}", html)
