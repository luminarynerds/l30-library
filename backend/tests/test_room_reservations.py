# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the room reservation system.
"""

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.room import (
    Room, RoomReservation, RoomEquipment, RoomType, ReservationStatus
)
from app.models.user import User, UserRole
from app.services import room_service


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_study_room(test_db):
    """Create a test study room (auto-approve)."""
    room = Room(
        name="Test Study Room",
        description="A small study room for testing",
        room_type=RoomType.study_room,
        capacity=4,
        floor="1st Floor",
        room_number="101",
        amenities=["WiFi", "Power Outlets"],
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
            "sunday": {"open": "12:00", "close": "17:00"},
        },
        is_active=True,
    )
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def test_meeting_room(test_db):
    """Create a test meeting room (requires approval)."""
    room = Room(
        name="Test Meeting Room",
        description="A meeting room requiring approval",
        room_type=RoomType.meeting_room,
        capacity=12,
        floor="2nd Floor",
        room_number="201",
        amenities=["WiFi", "Power Outlets", "Projector"],
        available_equipment=[
            {"id": "projector", "name": "Projector", "requires_staff": False},
            {"id": "video_conf", "name": "Video Conferencing", "requires_staff": True},
        ],
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
async def test_reservation(test_db, test_study_room, test_patron):
    """Create a test reservation."""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(days=1, hours=2)
    end_time = start_time + timedelta(hours=1)

    reservation = RoomReservation(
        room_id=test_study_room.id,
        patron_id=test_patron.id,
        start_time=start_time,
        end_time=end_time,
        status=ReservationStatus.confirmed,
        purpose="Study session",
        attendee_count=2,
        contact_name=f"{test_patron.first_name} {test_patron.last_name}",
        contact_email=test_patron.email,
    )
    test_db.add(reservation)
    await test_db.commit()
    await test_db.refresh(reservation)
    return reservation


# ============================================================================
# Room Model Tests
# ============================================================================

class TestRoomModel:
    """Test Room model functionality."""

    async def test_create_room(self, test_db):
        """Test creating a room."""
        room = Room(
            name="New Test Room",
            room_type=RoomType.study_room,
            capacity=6,
            is_active=True,
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)

        assert room.id is not None
        assert room.name == "New Test Room"
        assert room.room_type == RoomType.study_room
        assert room.capacity == 6
        assert room.is_active is True

    async def test_room_defaults(self, test_db):
        """Test room default values."""
        room = Room(
            name="Minimal Room",
            room_type=RoomType.study_room,
            capacity=2,
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)

        assert room.requires_approval is False
        assert room.max_duration_minutes == 120
        assert room.min_duration_minutes == 30
        assert room.advance_booking_days == 14
        assert room.is_active is True

    async def test_meeting_room_requires_approval(self, test_meeting_room):
        """Test that meeting rooms require approval."""
        assert test_meeting_room.requires_approval is True
        assert test_meeting_room.room_type == RoomType.meeting_room


# ============================================================================
# Reservation Service Tests
# ============================================================================

class TestRoomAvailability:
    """Test room availability checking."""

    async def test_check_room_availability_empty(self, test_db, test_study_room):
        """Test availability check with no existing reservations."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=1, hours=10)
        end_time = start_time + timedelta(hours=1)

        is_available = await room_service.check_room_availability(
            test_db, test_study_room.id, start_time, end_time
        )
        assert is_available is True

    async def test_check_room_availability_conflict(self, test_db, test_reservation):
        """Test availability check with conflicting reservation."""
        # Try to book overlapping time
        is_available = await room_service.check_room_availability(
            test_db,
            test_reservation.room_id,
            test_reservation.start_time,
            test_reservation.end_time,
        )
        assert is_available is False

    async def test_check_room_availability_adjacent(self, test_db, test_reservation):
        """Test that adjacent (non-overlapping) times are available."""
        # Book right after existing reservation
        start_time = test_reservation.end_time
        end_time = start_time + timedelta(hours=1)

        is_available = await room_service.check_room_availability(
            test_db, test_reservation.room_id, start_time, end_time
        )
        assert is_available is True

    async def test_check_room_availability_exclude_self(self, test_db, test_reservation):
        """Test that excluding a reservation ID works."""
        is_available = await room_service.check_room_availability(
            test_db,
            test_reservation.room_id,
            test_reservation.start_time,
            test_reservation.end_time,
            exclude_reservation_id=test_reservation.id,
        )
        assert is_available is True


class TestReservationValidation:
    """Test reservation rule validation."""

    async def test_validate_rules_valid(self, test_db, test_study_room, test_patron):
        """Test validation with valid reservation."""
        # room_service.validate_reservation_rules converts start/end to the
        # library's local timezone (default America/New_York when no
        # LibrarySystem row is configured) before comparing against
        # operating_hours, which are wall-clock local times. A UTC "now +
        # 10h" can land outside 09:00-21:00 local depending on both the
        # local UTC offset and the day of week it lands on. Anchor to a
        # guaranteed weekday (Monday) at a fixed local mid-morning time
        # instead.
        eastern = ZoneInfo("America/New_York")
        now_local = datetime.now(eastern)
        days_ahead = (7 - now_local.weekday()) or 7  # next Monday, always future
        next_monday = (now_local + timedelta(days=days_ahead)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        start_time = next_monday
        end_time = start_time + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, test_study_room, start_time, end_time, test_patron
        )
        assert len(errors) == 0

    async def test_validate_rules_past_time(self, test_db, test_study_room, test_patron):
        """Test validation rejects past times."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=1)
        end_time = now

        errors = await room_service.validate_reservation_rules(
            test_db, test_study_room, start_time, end_time, test_patron
        )
        assert any("past" in e.lower() for e in errors)

    async def test_validate_rules_too_short(self, test_db, test_study_room, test_patron):
        """Test validation rejects too-short reservations."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=1, hours=10)
        end_time = start_time + timedelta(minutes=15)  # Less than min 30 minutes

        errors = await room_service.validate_reservation_rules(
            test_db, test_study_room, start_time, end_time, test_patron
        )
        assert any("minimum" in e.lower() for e in errors)

    async def test_validate_rules_too_long(self, test_db, test_study_room, test_patron):
        """Test validation rejects too-long reservations."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=1, hours=10)
        end_time = start_time + timedelta(hours=5)  # More than max 2 hours

        errors = await room_service.validate_reservation_rules(
            test_db, test_study_room, start_time, end_time, test_patron
        )
        assert any("maximum" in e.lower() for e in errors)

    async def test_validate_rules_too_far_advance(self, test_db, test_study_room, test_patron):
        """Test validation rejects bookings too far in advance."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=30)  # More than 14 day limit
        end_time = start_time + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, test_study_room, start_time, end_time, test_patron
        )
        assert any("advance" in e.lower() for e in errors)

    async def test_validate_rules_inactive_room(self, test_db, test_patron):
        """Test validation rejects inactive rooms."""
        room = Room(
            name="Inactive Room",
            room_type=RoomType.study_room,
            capacity=2,
            is_active=False,
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)

        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=1, hours=10)
        end_time = start_time + timedelta(hours=1)

        errors = await room_service.validate_reservation_rules(
            test_db, room, start_time, end_time, test_patron
        )
        assert any("not available" in e.lower() for e in errors)


class TestReservationCreation:
    """Test reservation creation."""

    async def test_create_study_room_reservation_auto_approves(
        self, test_db, test_study_room, test_patron
    ):
        """Test that study room reservations are auto-approved."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=2, hours=10)
        end_time = start_time + timedelta(hours=1)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=test_study_room,
            patron=test_patron,
            start_time=start_time,
            end_time=end_time,
            purpose="Study session",
            attendee_count=2,
        )

        assert reservation.status == ReservationStatus.confirmed
        assert reservation.approved_at is not None

    async def test_create_meeting_room_reservation_pending(
        self, test_db, test_meeting_room, test_patron
    ):
        """Test that meeting room reservations require approval."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=2, hours=10)
        end_time = start_time + timedelta(hours=2)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=test_meeting_room,
            patron=test_patron,
            start_time=start_time,
            end_time=end_time,
            purpose="Team meeting",
            attendee_count=8,
        )

        assert reservation.status == ReservationStatus.pending
        assert reservation.approved_at is None


class TestApprovalWorkflow:
    """Test reservation approval workflow."""

    async def test_approve_reservation(self, test_db, test_meeting_room, test_patron, test_staff):
        """Test approving a pending reservation."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=3, hours=10)
        end_time = start_time + timedelta(hours=2)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=test_meeting_room,
            patron=test_patron,
            start_time=start_time,
            end_time=end_time,
            purpose="Meeting",
            attendee_count=6,
        )
        await test_db.commit()
        await test_db.refresh(reservation)

        assert reservation.status == ReservationStatus.pending

        # Approve the reservation
        await room_service.approve_reservation(
            test_db, reservation, test_staff, "Approved for team meeting"
        )
        await test_db.commit()
        await test_db.refresh(reservation)

        assert reservation.status == ReservationStatus.confirmed
        assert reservation.approved_by == test_staff.id
        assert reservation.approved_at is not None

    async def test_reject_reservation(self, test_db, test_meeting_room, test_patron, test_staff):
        """Test rejecting a pending reservation."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(days=3, hours=14)
        end_time = start_time + timedelta(hours=2)

        reservation = await room_service.create_reservation(
            db=test_db,
            room=test_meeting_room,
            patron=test_patron,
            start_time=start_time,
            end_time=end_time,
            purpose="Party",
            attendee_count=50,  # Exceeds capacity
        )
        await test_db.commit()
        await test_db.refresh(reservation)

        # Reject the reservation
        await room_service.reject_reservation(
            test_db, reservation, test_staff, "Exceeds room capacity"
        )
        await test_db.commit()
        await test_db.refresh(reservation)

        assert reservation.status == ReservationStatus.rejected
        assert reservation.rejection_reason == "Exceeds room capacity"


class TestCheckInAndNoShow:
    """Test check-in and no-show functionality."""

    async def test_check_in_reservation(self, test_db, test_reservation):
        """Test checking in to a reservation."""
        # Move start time to now for check-in
        test_reservation.start_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        test_reservation.end_time = test_reservation.start_time + timedelta(hours=1)
        await test_db.commit()
        await test_db.refresh(test_reservation)

        await room_service.check_in_reservation(test_db, test_reservation)
        await test_db.commit()
        await test_db.refresh(test_reservation)

        assert test_reservation.status == ReservationStatus.checked_in
        assert test_reservation.checked_in_at is not None

    async def test_check_in_too_early(self, test_db, test_reservation):
        """Test that early check-in fails."""
        # Reservation starts in 30 minutes (more than 15 min early limit)
        test_reservation.start_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        test_reservation.end_time = test_reservation.start_time + timedelta(hours=1)
        await test_db.commit()

        with pytest.raises(ValueError, match="not yet available"):
            await room_service.check_in_reservation(test_db, test_reservation)

    async def test_process_no_shows(self, test_db, test_study_room, test_patron):
        """Test no-show processing."""
        # Create a reservation that started 20 minutes ago without check-in
        start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        end_time = start_time + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Missed meeting",
            attendee_count=1,
            contact_email=test_patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Process no-shows
        no_show_count = await room_service.process_no_shows(test_db)
        await test_db.commit()
        await test_db.refresh(reservation)

        assert no_show_count >= 1
        assert reservation.status == ReservationStatus.no_show

    async def test_no_show_tracking_patron_count(self, test_db, test_study_room, test_patron):
        """Test that patron no-show count is tracked."""
        # Get initial no-show count
        await test_db.refresh(test_patron)
        initial_count = test_patron.room_reservation_no_show_count

        # Create a reservation that started 20 minutes ago without check-in
        start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        end_time = start_time + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Missed meeting",
            attendee_count=1,
            contact_email=test_patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()

        # Process no-shows
        await room_service.process_no_shows(test_db)
        await test_db.commit()

        # Verify patron no-show count increased
        await test_db.refresh(test_patron)
        assert test_patron.room_reservation_no_show_count == initial_count + 1

    async def test_no_show_within_grace_period_not_marked(self, test_db, test_study_room, test_patron):
        """Test that reservations within grace period are not marked as no-show."""
        # Create a reservation that started 10 minutes ago (within 15-min grace period)
        start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        end_time = start_time + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Within grace period",
            attendee_count=1,
            contact_email=test_patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Process no-shows
        no_show_count = await room_service.process_no_shows(test_db)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Should NOT be marked as no-show (still within 15-minute grace period)
        assert no_show_count == 0
        assert reservation.status == ReservationStatus.confirmed

    async def test_no_show_past_grace_period_marked(self, test_db, test_study_room, test_patron):
        """Test that reservations past grace period are marked as no-show."""
        # Create a reservation that started 16 minutes ago (beyond 15-min grace period)
        start_time = datetime.now(timezone.utc) - timedelta(minutes=16)
        end_time = start_time + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Past grace period",
            attendee_count=1,
            contact_email=test_patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Process no-shows
        no_show_count = await room_service.process_no_shows(test_db)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Should be marked as no-show
        assert no_show_count == 1
        assert reservation.status == ReservationStatus.no_show

    async def test_room_available_after_no_show(self, test_db, test_study_room, test_patron):
        """Test that room becomes available for walk-ins after no-show."""
        # Create a no-show reservation
        start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        end_time = start_time + timedelta(hours=1)

        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="No-show test",
            attendee_count=1,
            contact_email=test_patron.email,
        )
        test_db.add(reservation)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Process no-shows
        await room_service.process_no_shows(test_db)
        await test_db.commit()
        await test_db.refresh(reservation)

        # Verify room status can now be used for walk-ins by checking availability
        # (The slot should now be available since the reservation is marked no-show)
        is_available = await room_service.check_room_availability(
            test_db,
            test_study_room.id,
            start_time,
            end_time
        )
        assert is_available is True

    async def test_multiple_no_shows_tracked(self, test_db, test_study_room, test_patron):
        """Test that multiple no-shows are accumulated for a patron."""
        # Get initial count
        await test_db.refresh(test_patron)
        initial_count = test_patron.room_reservation_no_show_count

        # Create and process multiple no-shows
        for i in range(3):
            start_time = datetime.now(timezone.utc) - timedelta(minutes=20, days=i)
            end_time = start_time + timedelta(hours=1)

            reservation = RoomReservation(
                room_id=test_study_room.id,
                patron_id=test_patron.id,
                start_time=start_time,
                end_time=end_time,
                status=ReservationStatus.confirmed,
                purpose=f"No-show #{i+1}",
                attendee_count=1,
                contact_email=test_patron.email,
            )
            test_db.add(reservation)

        await test_db.commit()

        # Process all no-shows
        no_show_count = await room_service.process_no_shows(test_db)
        await test_db.commit()

        # Verify all no-shows were tracked
        await test_db.refresh(test_patron)
        assert no_show_count == 3
        assert test_patron.room_reservation_no_show_count == initial_count + 3


class TestCancellation:
    """Test reservation cancellation."""

    async def test_cancel_reservation(self, test_db, test_reservation, test_patron):
        """Test cancelling a reservation."""
        await room_service.cancel_reservation(
            test_db, test_reservation, test_patron, "Schedule conflict"
        )
        await test_db.commit()
        await test_db.refresh(test_reservation)

        assert test_reservation.status == ReservationStatus.cancelled
        assert test_reservation.cancelled_by == test_patron.id
        assert test_reservation.cancellation_reason == "Schedule conflict"


class TestAvailabilitySlots:
    """Test availability slot calculation."""

    async def test_get_available_slots_empty_day(self, test_db, test_study_room):
        """Test getting available slots with no reservations."""
        # Use a Monday (room is open 09:00-21:00)
        test_date = datetime.now(timezone.utc) + timedelta(days=1)
        # Find next Monday
        while test_date.weekday() != 0:
            test_date += timedelta(days=1)

        slots = await room_service.get_room_availability_slots(
            test_db, test_study_room, test_date
        )

        # Should have at least one slot covering most of the day
        assert len(slots) >= 1
        total_minutes = sum(s["duration_minutes"] for s in slots)
        assert total_minutes > 0

    async def test_get_available_slots_with_reservation(
        self, test_db, test_study_room, test_patron
    ):
        """Test that reservations create gaps in availability."""
        # Use next Monday
        test_date = datetime.now(timezone.utc) + timedelta(days=1)
        while test_date.weekday() != 0:
            test_date += timedelta(days=1)

        # Create a reservation in the middle of the day
        start_time = test_date.replace(hour=12, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=2)

        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Lunch meeting",
            attendee_count=2,
        )
        test_db.add(reservation)
        await test_db.commit()

        slots = await room_service.get_room_availability_slots(
            test_db, test_study_room, test_date
        )

        # Should have slots before and after the reservation
        assert len(slots) >= 2


# ============================================================================
# Statistics Tests
# ============================================================================

class TestUsageStatistics:
    """Test usage statistics calculation."""

    async def test_get_utilization_stats(self, test_db, test_study_room, test_patron):
        """Test calculating utilization statistics."""
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=7)
        end_date = now

        # Create some completed reservations
        for i in range(3):
            reservation = RoomReservation(
                room_id=test_study_room.id,
                patron_id=test_patron.id,
                start_time=start_date + timedelta(days=i, hours=10),
                end_time=start_date + timedelta(days=i, hours=12),
                status=ReservationStatus.completed,
                purpose=f"Session {i}",
                attendee_count=2,
            )
            test_db.add(reservation)

        await test_db.commit()

        stats = await room_service.get_room_utilization_stats(
            test_db, test_study_room.id, start_date, end_date
        )

        assert stats["completed_reservations"] >= 3
        assert stats["total_hours_booked"] > 0

    async def test_get_popular_times(self, test_db, test_study_room, test_patron):
        """Test getting popular times analysis."""
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=30)

        # Create reservations at various times
        for i in range(5):
            # Create reservations at 10 AM on different days
            reservation = RoomReservation(
                room_id=test_study_room.id,
                patron_id=test_patron.id,
                start_time=start_date + timedelta(days=i * 2, hours=10),
                end_time=start_date + timedelta(days=i * 2, hours=11),
                status=ReservationStatus.completed,
                purpose=f"Morning session {i}",
                attendee_count=2,
            )
            test_db.add(reservation)

        await test_db.commit()

        popular = await room_service.get_popular_times(
            test_db, test_study_room.id, start_date, now
        )

        assert "by_day" in popular
        assert "by_hour" in popular
        assert "peak_hour" in popular
        assert "peak_day" in popular


# ============================================================================
# Date Range Availability Tests
# ============================================================================

class TestDateRangeAvailability:
    """Test date range availability endpoint."""

    async def test_get_availability_date_range(
        self, client, test_study_room, test_patron
    ):
        """Test getting availability across a date range."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/rooms/{test_study_room.id}/availability/range",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check structure of first availability response
        first_availability = data[0]
        assert "room_id" in first_availability
        assert first_availability["room_id"] == test_study_room.id
        assert "room_name" in first_availability
        assert "date" in first_availability
        assert "available_slots" in first_availability
        assert "reservations" in first_availability

        # Check available slots structure
        if first_availability["available_slots"]:
            slot = first_availability["available_slots"][0]
            assert "start_time" in slot
            assert "end_time" in slot
            assert "duration_minutes" in slot

    async def test_date_range_excludes_booked_slots(
        self, client, test_db, test_study_room, test_patron
    ):
        """Test that already-booked slots are excluded from availability."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        booking_date = today + timedelta(days=2)
        
        # Create a confirmed reservation
        start_time = booking_date.replace(hour=10, minute=0)
        end_time = start_time + timedelta(hours=2)
        
        reservation = RoomReservation(
            room_id=test_study_room.id,
            patron_id=test_patron.id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.confirmed,
            purpose="Booked session",
            attendee_count=2,
        )
        test_db.add(reservation)
        await test_db.commit()

        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/rooms/{test_study_room.id}/availability/range",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 200
        data = response.json()

        # Find the booked date in response
        booked_day_data = None
        for availability in data:
            if availability["date"] == booking_date.strftime("%Y-%m-%d"):
                booked_day_data = availability
                break

        assert booked_day_data is not None
        
        # Check that the reservation appears in the reservations list
        assert len(booked_day_data["reservations"]) > 0
        booked_res = booked_day_data["reservations"][0]
        # Compare as datetimes, not raw strings: the API serializes UTC with
        # a "Z" suffix (e.g. Pydantic v2's default), while start_time.isoformat()
        # produces "+00:00" -- both are the same instant.
        assert datetime.fromisoformat(booked_res["start_time"]) == start_time
        assert datetime.fromisoformat(booked_res["end_time"]) == end_time
        assert booked_res["status"] == "confirmed"

        # Check that available slots don't overlap with the reservation
        for slot in booked_day_data["available_slots"]:
            slot_start = datetime.fromisoformat(slot["start_time"])
            slot_end = datetime.fromisoformat(slot["end_time"])
            
            # Slots should not overlap with the reservation
            assert not (slot_start < end_time and slot_end > start_time)

    async def test_date_range_invalid_dates(self, client, test_study_room):
        """Test date range with invalid dates."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Test with past date
        past_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/rooms/{test_study_room.id}/availability/range",
            params={"start_date": past_date, "end_date": end_date},
        )

        assert response.status_code == 400

        # Test with end_date before start_date
        start_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/rooms/{test_study_room.id}/availability/range",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 400

        # Test with date range exceeding 90 days
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=100)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/rooms/{test_study_room.id}/availability/range",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 400


# ============================================================================
# Multi-Room Availability Tests
# ============================================================================

class TestMultiRoomAvailability:
    """Test multi-room availability endpoint."""

    @pytest.fixture
    async def three_rooms(self, test_db):
        """Create three test rooms."""
        rooms = []
        for i in range(3):
            room = Room(
                name=f"Multi Test Room {i+1}",
                room_type=RoomType.study_room,
                capacity=4,
                floor="1st Floor",
                room_number=f"10{i+1}",
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
                    "sunday": {"open": "12:00", "close": "17:00"},
                },
                is_active=True,
            )
            test_db.add(room)
            rooms.append(room)

        await test_db.commit()
        for room in rooms:
            await test_db.refresh(room)
        return rooms

    async def test_multi_room_availability(
        self, client, three_rooms
    ):
        """Test getting availability across multiple rooms."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        room_ids = ",".join(str(r.id) for r in three_rooms)

        response = await client.get(
            "/api/v1/rooms/availability/multi",
            params={
                "room_ids": room_ids,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == 200
        data = response.json()
        
        # Check that we have data for all three rooms
        assert len(data) == 3
        for room in three_rooms:
            assert str(room.id) in data
            room_availability = data[str(room.id)]
            assert isinstance(room_availability, list)
            assert len(room_availability) > 0

    async def test_multi_room_with_bookings(
        self, client, test_db, three_rooms, test_patron
    ):
        """Test multi-room availability with different booking patterns."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        booking_date = today + timedelta(days=2)

        # Book room 1 at 10:00-12:00
        res1 = RoomReservation(
            room_id=three_rooms[0].id,
            patron_id=test_patron.id,
            start_time=booking_date.replace(hour=10, minute=0),
            end_time=booking_date.replace(hour=12, minute=0),
            status=ReservationStatus.confirmed,
            purpose="Session 1",
            attendee_count=2,
        )

        # Book room 2 at 14:00-16:00
        res2 = RoomReservation(
            room_id=three_rooms[1].id,
            patron_id=test_patron.id,
            start_time=booking_date.replace(hour=14, minute=0),
            end_time=booking_date.replace(hour=16, minute=0),
            status=ReservationStatus.confirmed,
            purpose="Session 2",
            attendee_count=2,
        )

        # Room 3 has no bookings

        test_db.add(res1)
        test_db.add(res2)
        await test_db.commit()

        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        room_ids = ",".join(str(r.id) for r in three_rooms)

        response = await client.get(
            "/api/v1/rooms/availability/multi",
            params={
                "room_ids": room_ids,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check room 1 has a reservation on booking_date
        room1_data = data[str(three_rooms[0].id)]
        booking_date_str = booking_date.strftime("%Y-%m-%d")
        room1_booking_day = next(
            (av for av in room1_data if av["date"] == booking_date_str), None
        )
        assert room1_booking_day is not None
        assert len(room1_booking_day["reservations"]) == 1

        # Check room 2 has a reservation on booking_date
        room2_data = data[str(three_rooms[1].id)]
        room2_booking_day = next(
            (av for av in room2_data if av["date"] == booking_date_str), None
        )
        assert room2_booking_day is not None
        assert len(room2_booking_day["reservations"]) == 1

        # Check room 3 has no reservations on booking_date
        room3_data = data[str(three_rooms[2].id)]
        room3_booking_day = next(
            (av for av in room3_data if av["date"] == booking_date_str), None
        )
        assert room3_booking_day is not None
        assert len(room3_booking_day["reservations"]) == 0

    async def test_multi_room_too_many_rooms(self, client, test_study_room):
        """Test multi-room endpoint with too many rooms."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        # Try to request more than 20 rooms
        room_ids = ",".join(str(i) for i in range(1, 22))

        response = await client.get(
            "/api/v1/rooms/availability/multi",
            params={
                "room_ids": room_ids,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == 400

    async def test_multi_room_invalid_room_ids(self, client, test_study_room):
        """Test multi-room endpoint with invalid room IDs."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=4)).strftime("%Y-%m-%d")

        # Test with non-existent room IDs
        room_ids = "9999,9998,9997"

        response = await client.get(
            "/api/v1/rooms/availability/multi",
            params={
                "room_ids": room_ids,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == 404

    async def test_multi_room_date_range_limit(self, client, test_study_room):
        """Test multi-room endpoint respects 30-day limit."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=40)).strftime("%Y-%m-%d")  # 40 days, exceeds 30-day limit

        response = await client.get(
            "/api/v1/rooms/availability/multi",
            params={
                "room_ids": str(test_study_room.id),
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == 400
