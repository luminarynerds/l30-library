# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Edge case tests for the room reservation system.

Tests boundary conditions, invalid inputs, race conditions,
and unusual but valid scenarios.
"""

import os

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.room import (
    Room, RoomReservation, RoomType, ReservationStatus
)
from app.models.user import User, UserRole
from app.services import room_service


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def study_room(test_db):
    """Create a study room with specific operating hours."""
    room = Room(
        name="Edge Case Study Room",
        room_type=RoomType.study_room,
        capacity=4,
        floor="1st Floor",
        room_number="E01",
        amenities=["WiFi"],
        requires_approval=False,
        max_duration_minutes=120,
        min_duration_minutes=30,
        advance_booking_days=14,
        min_advance_hours=1,
        operating_hours={
            "monday": {"open": "09:00", "close": "21:00"},
            "tuesday": {"open": "09:00", "close": "21:00"},
            "wednesday": {"open": "09:00", "close": "21:00"},
            "thursday": {"open": "09:00", "close": "21:00"},
            "friday": {"open": "09:00", "close": "18:00"},
            "saturday": {"open": "10:00", "close": "17:00"},
        },
        is_active=True,
    )
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def meeting_room(test_db):
    """Create a meeting room requiring approval."""
    room = Room(
        name="Edge Case Meeting Room",
        room_type=RoomType.meeting_room,
        capacity=12,
        requires_approval=True,
        max_duration_minutes=240,
        min_duration_minutes=60,
        advance_booking_days=30,
        min_advance_hours=24,
        operating_hours={
            "monday": {"open": "09:00", "close": "20:00"},
            "tuesday": {"open": "09:00", "close": "20:00"},
            "wednesday": {"open": "09:00", "close": "20:00"},
            "thursday": {"open": "09:00", "close": "20:00"},
            "friday": {"open": "09:00", "close": "17:00"},
        },
        is_active=True,
    )
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def capacity_one_room(test_db):
    """Create a room with capacity of exactly 1."""
    room = Room(
        name="Solo Study Pod",
        room_type=RoomType.study_room,
        capacity=1,
        requires_approval=False,
        max_duration_minutes=60,
        min_duration_minutes=30,
        advance_booking_days=7,
        min_advance_hours=0,
        operating_hours={
            "monday": {"open": "00:00", "close": "23:59"},
            "tuesday": {"open": "00:00", "close": "23:59"},
            "wednesday": {"open": "00:00", "close": "23:59"},
            "thursday": {"open": "00:00", "close": "23:59"},
            "friday": {"open": "00:00", "close": "23:59"},
            "saturday": {"open": "00:00", "close": "23:59"},
            "sunday": {"open": "00:00", "close": "23:59"},
        },
        is_active=True,
    )
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def patron(test_db):
    """Create a test patron."""
    from app.core.security import hash_password

    user = User(
        email="edgecase@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Edge",
        last_name="Case",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def second_patron(test_db):
    """Create a second test patron for conflict tests."""
    from app.core.security import hash_password

    user = User(
        email="edgecase2@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Edge",
        last_name="Case2",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


def _next_weekday(weekday: int) -> datetime:
    """Get the next occurrence of a weekday (0=Monday). Always future.

    Returned in America/New_York, not UTC: room_service.validate_reservation_rules
    and get_room_availability_slots compare against Room.operating_hours by
    converting to the library's local timezone (default America/New_York
    when no LibrarySystem row is configured), and operating_hours are
    wall-clock local times (e.g. "09:00"-"21:00"). Callers do
    `.replace(hour=..., minute=...)` on the result, which must therefore
    already be in local time or the hour comparison is off by the UTC
    offset.
    """
    eastern = ZoneInfo("America/New_York")
    now = datetime.now(eastern)
    target = now + timedelta(days=1)
    while target.weekday() != weekday:
        target += timedelta(days=1)
    return target.replace(hour=0, minute=0, second=0, microsecond=0)


# ============================================================================
# Boundary: Exact duration limits
# ============================================================================

class TestDurationBoundaries:
    """Test reservations at exact min/max duration limits."""

    async def test_reservation_at_exact_min_duration(self, test_db, study_room, patron):
        """Booking exactly at min_duration_minutes (30 min) should pass."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(minutes=30)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert len(errors) == 0

    async def test_reservation_one_minute_below_min_duration(self, test_db, study_room, patron):
        """Booking 1 minute under min_duration_minutes should fail."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(minutes=29)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("minimum" in e.lower() for e in errors)

    async def test_reservation_at_exact_max_duration(self, test_db, study_room, patron):
        """Booking exactly at max_duration_minutes (120 min) should pass."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(minutes=120)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert len(errors) == 0

    async def test_reservation_one_minute_over_max_duration(self, test_db, study_room, patron):
        """Booking 1 minute over max_duration_minutes should fail."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(minutes=121)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("maximum" in e.lower() for e in errors)


# ============================================================================
# Boundary: Operating hours edges
# ============================================================================

class TestOperatingHoursBoundaries:
    """Test reservations at the exact boundaries of operating hours."""

    async def test_booking_starts_at_exact_open_time(self, test_db, study_room, patron):
        """Booking starting exactly when the room opens should be valid."""
        monday = _next_weekday(0)
        start = monday.replace(hour=9, minute=0)
        end = start + timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        # Should have no operating-hours errors (may have advance booking errors
        # depending on timing, so just check no "opens at" error)
        assert not any("opens at" in e.lower() for e in errors)

    async def test_booking_ends_at_exact_close_time(self, test_db, study_room, patron):
        """Booking ending exactly at closing time should be valid."""
        monday = _next_weekday(0)
        end = monday.replace(hour=21, minute=0)
        start = end - timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert not any("closes at" in e.lower() for e in errors)

    async def test_booking_before_open(self, test_db, study_room, patron):
        """Booking before room opens should fail."""
        monday = _next_weekday(0)
        start = monday.replace(hour=8, minute=30)
        end = start + timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("opens at" in e.lower() for e in errors)

    async def test_booking_ends_after_close(self, test_db, study_room, patron):
        """Booking that extends past closing should fail."""
        monday = _next_weekday(0)
        start = monday.replace(hour=20, minute=30)
        end = start + timedelta(minutes=60)  # ends at 21:30, past 21:00 close

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("closes at" in e.lower() for e in errors)

    async def test_booking_on_closed_day(self, test_db, study_room, patron):
        """Booking on a day with no operating hours (Sunday) should fail."""
        sunday = _next_weekday(6)
        start = sunday.replace(hour=12, minute=0)
        end = start + timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("closed" in e.lower() for e in errors)

    async def test_meeting_room_closed_on_weekend(self, test_db, meeting_room, patron):
        """Meeting room with no weekend hours should reject Saturday booking."""
        saturday = _next_weekday(5)
        start = saturday.replace(hour=10, minute=0)
        end = start + timedelta(hours=2)

        errors = await room_service.validate_reservation_rules(
            test_db, meeting_room, start, end, patron
        )
        assert any("closed" in e.lower() for e in errors)


# ============================================================================
# Boundary: Advance booking limits
# ============================================================================

class TestAdvanceBookingBoundaries:
    """Test advance booking day limits and min advance hour limits."""

    async def test_booking_at_exact_advance_day_limit(self, test_db, study_room, patron):
        """Booking exactly at advance_booking_days should be valid."""
        now = datetime.now(timezone.utc)
        target = now + timedelta(days=study_room.advance_booking_days)
        # Find valid operating day
        while target.strftime("%A").lower() not in study_room.operating_hours:
            target -= timedelta(days=1)
        start = target.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert not any("advance" in e.lower() for e in errors)

    async def test_booking_one_day_beyond_advance_limit(self, test_db, study_room, patron):
        """Booking 1 day past advance_booking_days should fail."""
        now = datetime.now(timezone.utc)
        target = now + timedelta(days=study_room.advance_booking_days + 1)
        start = target.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("advance" in e.lower() for e in errors)

    async def test_booking_in_the_past(self, test_db, study_room, patron):
        """Booking in the past should always fail."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=2)
        end = start + timedelta(minutes=60)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        assert any("past" in e.lower() for e in errors)

    async def test_booking_just_barely_in_future(self, test_db, study_room, patron):
        """Booking that starts just seconds from now should check min_advance_hours."""
        now = datetime.now(timezone.utc)
        start = now + timedelta(minutes=30)  # Less than 1 hour advance
        end = start + timedelta(minutes=30)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        # study_room requires 1 hour advance
        assert any("advance" in e.lower() or "hour" in e.lower() for e in errors)


# ============================================================================
# Overlap and conflict edge cases
# ============================================================================

class TestOverlapEdgeCases:
    """Test various overlap scenarios for availability checking."""

    async def test_back_to_back_reservations_no_conflict(self, test_db, study_room, patron):
        """Two reservations where one ends exactly as another starts should not conflict."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=10, minute=0)
        end1 = start1 + timedelta(hours=1)

        # Create first reservation
        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.confirmed,
            purpose="First",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Second reservation starts exactly when first ends
        is_available = await room_service.check_room_availability(
            test_db, study_room.id, end1, end1 + timedelta(hours=1)
        )
        assert is_available is True

    async def test_one_minute_overlap_is_conflict(self, test_db, study_room, patron):
        """Even 1 minute of overlap should be detected as a conflict."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=10, minute=0)
        end1 = start1 + timedelta(hours=1)

        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.confirmed,
            purpose="First",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Second reservation overlaps by 1 minute
        overlap_start = end1 - timedelta(minutes=1)
        is_available = await room_service.check_room_availability(
            test_db, study_room.id, overlap_start, overlap_start + timedelta(hours=1)
        )
        assert is_available is False

    async def test_new_booking_completely_inside_existing(self, test_db, study_room, patron):
        """A shorter booking entirely within an existing one should conflict."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=10, minute=0)
        end1 = start1 + timedelta(hours=2)

        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.confirmed,
            purpose="Long session",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Shorter booking inside the existing one
        inner_start = start1 + timedelta(minutes=30)
        inner_end = end1 - timedelta(minutes=30)
        is_available = await room_service.check_room_availability(
            test_db, study_room.id, inner_start, inner_end
        )
        assert is_available is False

    async def test_new_booking_completely_encompasses_existing(self, test_db, study_room, patron):
        """A longer booking that encompasses an existing one should conflict."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=11, minute=0)
        end1 = start1 + timedelta(hours=1)

        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.confirmed,
            purpose="Short session",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Larger booking that surrounds the existing one
        outer_start = start1 - timedelta(minutes=30)
        outer_end = end1 + timedelta(minutes=30)
        is_available = await room_service.check_room_availability(
            test_db, study_room.id, outer_start, outer_end
        )
        assert is_available is False

    async def test_cancelled_reservation_does_not_block(self, test_db, study_room, patron):
        """Cancelled reservations should not block new bookings."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        cancelled_res = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.cancelled,
            purpose="Cancelled",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(cancelled_res)
        await test_db.commit()

        is_available = await room_service.check_room_availability(
            test_db, study_room.id, start, end
        )
        assert is_available is True

    async def test_no_show_reservation_does_not_block(self, test_db, study_room, patron):
        """No-show reservations should not block new bookings."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        no_show_res = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.no_show,
            purpose="Missed",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(no_show_res)
        await test_db.commit()

        is_available = await room_service.check_room_availability(
            test_db, study_room.id, start, end
        )
        assert is_available is True

    async def test_rejected_reservation_does_not_block(self, test_db, study_room, patron):
        """Rejected reservations should not block new bookings."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        rejected_res = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.rejected,
            purpose="Rejected",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(rejected_res)
        await test_db.commit()

        is_available = await room_service.check_room_availability(
            test_db, study_room.id, start, end
        )
        assert is_available is True

    async def test_pending_reservation_blocks(self, test_db, study_room, patron):
        """Pending reservations should still block new bookings."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        pending_res = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.pending,
            purpose="Pending",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(pending_res)
        await test_db.commit()

        is_available = await room_service.check_room_availability(
            test_db, study_room.id, start, end
        )
        assert is_available is False


# ============================================================================
# One reservation per day per patron
# ============================================================================

class TestOneReservationPerDay:
    """Test the 1 reservation per day per patron rule."""

    async def test_second_booking_same_day_same_patron_rejected(
        self, test_db, study_room, patron
    ):
        """A patron can only have 1 reservation per day."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=10, minute=0)
        end1 = start1 + timedelta(hours=1)

        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.confirmed,
            purpose="Morning session",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Same patron, same day, different time
        start2 = monday.replace(hour=14, minute=0)
        end2 = start2 + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start2, end2, patron
        )
        assert any("already have a reservation" in e.lower() for e in errors)

    async def test_different_patron_same_day_allowed(
        self, test_db, study_room, patron, second_patron
    ):
        """Different patrons can book the same day."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=10, minute=0)
        end1 = start1 + timedelta(hours=1)

        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.confirmed,
            purpose="Patron 1",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Different patron, same day, different time slot
        start2 = monday.replace(hour=14, minute=0)
        end2 = start2 + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start2, end2, second_patron
        )
        assert not any("already have a reservation" in e.lower() for e in errors)

    async def test_cancelled_reservation_frees_daily_slot(
        self, test_db, study_room, patron
    ):
        """A cancelled reservation should not count against the daily limit."""
        monday = _next_weekday(0)
        start1 = monday.replace(hour=10, minute=0)
        end1 = start1 + timedelta(hours=1)

        res1 = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start1,
            end_time=end1,
            status=ReservationStatus.cancelled,
            purpose="Cancelled session",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(res1)
        await test_db.commit()

        # Same patron, same day, should be allowed since first was cancelled
        start2 = monday.replace(hour=14, minute=0)
        end2 = start2 + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start2, end2, patron
        )
        assert not any("already have a reservation" in e.lower() for e in errors)


# ============================================================================
# Inactive / non-existent rooms
# ============================================================================

class TestInactiveRoom:
    """Test booking against inactive rooms."""

    async def test_inactive_room_rejected(self, test_db, patron):
        """Booking an inactive room should fail validation."""
        room = Room(
            name="Decommissioned Room",
            room_type=RoomType.study_room,
            capacity=4,
            is_active=False,
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)

        now = datetime.now(timezone.utc)
        start = now + timedelta(days=1, hours=10)
        end = start + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, room, start, end, patron
        )
        assert any("not available" in e.lower() for e in errors)

    async def test_inactive_room_returns_early(self, test_db, patron):
        """Inactive room validation should return immediately without checking other rules."""
        room = Room(
            name="Inactive Room",
            room_type=RoomType.study_room,
            capacity=4,
            is_active=False,
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)

        # Even with valid time parameters, inactive room should fail
        now = datetime.now(timezone.utc)
        start = now + timedelta(days=1, hours=10)
        end = start + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, room, start, end, patron
        )
        # Only 1 error (room not available), not checking other rules
        assert len(errors) == 1
        assert "not available" in errors[0].lower()


# ============================================================================
# Capacity edge cases
# ============================================================================

class TestCapacityEdgeCases:
    """Test attendee count vs room capacity boundaries."""

    async def test_attendee_count_at_exact_capacity(self, test_db, study_room, patron):
        """Booking with attendee_count == room capacity should succeed."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=study_room,
            patron=patron,
            start_time=start,
            end_time=end,
            purpose="Full room",
            attendee_count=study_room.capacity,  # exactly 4
        )
        await test_db.commit()

        assert reservation.attendee_count == study_room.capacity

    async def test_single_person_in_capacity_one_room(self, test_db, capacity_one_room, patron):
        """Booking with 1 person in a capacity-1 room should work."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(minutes=30)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=capacity_one_room,
            patron=patron,
            start_time=start,
            end_time=end,
            purpose="Solo study",
            attendee_count=1,
        )
        await test_db.commit()

        assert reservation.attendee_count == 1
        assert reservation.status == ReservationStatus.confirmed


# ============================================================================
# Auto-approval vs pending logic
# ============================================================================

class TestApprovalLogic:
    """Test auto-approval vs pending status assignment."""

    async def test_study_room_auto_confirmed(self, test_db, study_room, patron):
        """Study room bookings should be auto-confirmed."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=study_room,
            patron=patron,
            start_time=start,
            end_time=end,
            attendee_count=2,
        )

        assert reservation.status == ReservationStatus.confirmed
        assert reservation.approved_at is not None

    async def test_meeting_room_pending(self, test_db, meeting_room, patron):
        """Meeting room bookings should require approval."""
        wednesday = _next_weekday(2)
        start = wednesday.replace(hour=10, minute=0)
        end = start + timedelta(hours=2)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=meeting_room,
            patron=patron,
            start_time=start,
            end_time=end,
            attendee_count=4,
        )

        assert reservation.status == ReservationStatus.pending
        assert reservation.approved_at is None

    async def test_recurring_reservation_always_pending(self, test_db, study_room, patron):
        """Recurring reservations should always be pending, even for study rooms."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=study_room,
            patron=patron,
            start_time=start,
            end_time=end,
            attendee_count=2,
            is_recurring=True,
            recurrence_pattern="weekly",
            recurrence_end_date=start + timedelta(weeks=4),
        )

        assert reservation.status == ReservationStatus.pending


# ============================================================================
# Check-in edge cases
# ============================================================================

class TestCheckInEdgeCases:
    """Test check-in boundary conditions."""

    async def test_check_in_at_exact_start_time(self, test_db, study_room, patron):
        """Check-in at exact start time should succeed."""
        now = datetime.now(timezone.utc)
        start = now
        end = start + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.confirmed,
            purpose="On-time check-in",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Ensure timezone info is present (SQLite strips tzinfo)
        if reservation.start_time.tzinfo is None:
            reservation.start_time = reservation.start_time.replace(tzinfo=timezone.utc)
        if reservation.end_time.tzinfo is None:
            reservation.end_time = reservation.end_time.replace(tzinfo=timezone.utc)

        await room_service.check_in_reservation(test_db, reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        assert reservation.status == ReservationStatus.checked_in
        assert reservation.checked_in_at is not None

    async def test_check_in_just_before_grace_period_ends(self, test_db, study_room, patron):
        """Check-in at 14 min after start (within 15-min grace) should succeed."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=14)
        end = start + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.confirmed,
            purpose="Late but within grace",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Ensure timezone info is present (SQLite strips tzinfo)
        if reservation.start_time.tzinfo is None:
            reservation.start_time = reservation.start_time.replace(tzinfo=timezone.utc)
        if reservation.end_time.tzinfo is None:
            reservation.end_time = reservation.end_time.replace(tzinfo=timezone.utc)

        await room_service.check_in_reservation(test_db, reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        assert reservation.status == ReservationStatus.checked_in

    async def test_no_show_at_exactly_grace_boundary(self, test_db, study_room, patron):
        """Reservation at exactly 15 min past IS marked as no-show (uses <= comparison)."""
        start = datetime.now(timezone.utc) - timedelta(minutes=15)
        end = start + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.confirmed,
            purpose="Grace boundary",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        no_show_count = await room_service.process_no_shows(test_db)
        await test_db.commit()
        await test_db.refresh(reservation)

        # At exactly 15 minutes, the system marks it as no-show (start_time <= cutoff)
        assert reservation.status == ReservationStatus.no_show
        assert no_show_count == 1

    async def test_no_show_one_minute_before_grace_still_safe(self, test_db, study_room, patron):
        """Reservation at 14 min past should NOT be marked as no-show."""
        start = datetime.now(timezone.utc) - timedelta(minutes=14)
        end = start + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=study_room.id,
            patron_id=patron.id,
            start_time=start,
            end_time=end,
            status=ReservationStatus.confirmed,
            purpose="Within grace",
            attendee_count=1,
            contact_email=patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        no_show_count = await room_service.process_no_shows(test_db)
        await test_db.commit()
        await test_db.refresh(reservation)

        assert reservation.status == ReservationStatus.confirmed
        assert no_show_count == 0


# ============================================================================
# Availability slots edge cases
# ============================================================================

class TestAvailabilitySlotsEdgeCases:
    """Test slot generation in unusual scenarios."""

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("DATABASE_URL", "sqlite"),
        reason="SQLite strips timezone info causing tz-naive vs tz-aware comparison errors",
    )
    async def test_fully_booked_day_returns_no_slots(self, test_db, study_room, patron):
        """A day with wall-to-wall bookings should return no available slots."""
        monday = _next_weekday(0)

        # Book the entire operating day (09:00-21:00) in 2-hour chunks
        for hour in range(9, 21, 2):
            start = monday.replace(hour=hour, minute=0)
            end = start + timedelta(hours=2)
            res = RoomReservation(
                room_id=study_room.id,
                patron_id=patron.id,
                start_time=start,
                end_time=end,
                status=ReservationStatus.confirmed,
                purpose=f"Slot {hour}",
                attendee_count=1,
                contact_email=patron.email,
            )
            test_db.add(res)

        await test_db.commit()

        slots = await room_service.get_room_availability_slots(
            test_db, study_room, monday
        )
        assert len(slots) == 0

    async def test_room_with_no_operating_hours_on_date(self, test_db, study_room, patron):
        """A day with no defined operating hours should return no slots."""
        sunday = _next_weekday(6)  # study_room has no Sunday hours

        slots = await room_service.get_room_availability_slots(
            test_db, study_room, sunday
        )
        assert len(slots) == 0


# ============================================================================
# Contact info edge cases
# ============================================================================

class TestContactInfoEdgeCases:
    """Test contact information handling in reservations."""

    async def test_reservation_without_optional_contact_info(self, test_db, study_room, patron):
        """Creating a reservation without phone should work."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=study_room,
            patron=patron,
            start_time=start,
            end_time=end,
            attendee_count=1,
            contact_phone=None,
        )

        assert reservation.contact_phone is None
        assert reservation.contact_name is not None  # auto-populated from patron
        assert reservation.contact_email is not None

    async def test_explicit_contact_overrides_patron_info(self, test_db, study_room, patron):
        """Explicit contact info should override auto-populated patron info."""
        monday = _next_weekday(0)
        start = monday.replace(hour=10, minute=0)
        end = start + timedelta(hours=1)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=study_room,
            patron=patron,
            start_time=start,
            end_time=end,
            attendee_count=1,
            contact_name="Custom Name",
            contact_email="custom@example.com",
            contact_phone="555-0000",
        )

        assert reservation.contact_name == "Custom Name"
        assert reservation.contact_email == "custom@example.com"
        assert reservation.contact_phone == "555-0000"


# ============================================================================
# Multiple validation errors at once
# ============================================================================

class TestMultipleValidationErrors:
    """Test that multiple validation errors are accumulated."""

    async def test_multiple_errors_returned(self, test_db, study_room, patron):
        """A booking violating multiple rules should return all errors."""
        # Past date + too short + before opening hours
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=1)
        start = start.replace(hour=7, minute=0)  # before 9:00 open
        end = start + timedelta(minutes=15)  # below 30-min minimum

        errors = await room_service.validate_reservation_rules(
            test_db, study_room, start, end, patron
        )
        # Should have at least 2 errors (past + too short)
        assert len(errors) >= 2
