# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for LSC attendance tracking system.

Tests all critical functionality:
- Attendance session CRUD
- QR code token generation and check-in
- Library card scan check-in with patron lookup
- Walk-in quick-add
- Head count mode for large events
- Age range estimation from patron DOB
- Repeat attendee detection
- Post-event survey distribution
- Dashboard metrics aggregation
- ROI calculation (cost per attendee)
- Session lifecycle (open -> closed -> finalized)
- Duplicate check-in prevention
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import (
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceTrend,
    AgeRange,
    CheckInMethod,
    SurveyStatus,
)
from app.models.event import Event
from app.models.user import User, UserRole
from app.services.attendance_service import AttendanceService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def staff_member(test_db: AsyncSession):
    """Create a staff user for attendance operations."""
    from app.core.security import hash_password

    user = User(
        email="attendance_staff@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Staff",
        last_name="Tracker",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_with_card(test_db: AsyncSession):
    """Create a patron with a library card and DOB."""
    from app.core.security import hash_password

    user = User(
        email="patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Jane",
        last_name="Doe",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LIB00042",
        date_of_birth=date(1990, 5, 15),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def child_patron(test_db: AsyncSession):
    """Create a child patron for age range testing."""
    from app.core.security import hash_password

    user = User(
        email="child@example.com",
        password_hash=hash_password("ChildPassword123!"),
        first_name="Timmy",
        last_name="Smith",
        role=UserRole.CHILD,
        is_active=True,
        email_verified=True,
        library_card="LIB00099",
        date_of_birth=date(2018, 3, 10),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_event(test_db: AsyncSession):
    """Create a test event for attendance tracking."""
    event = Event(
        title="Summer Reading Kickoff",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        location="Main Library",
        category="Reading Program",
        audience="All ages",
        max_attendees=50,
        registration_required=False,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)
    return event


@pytest.fixture
async def open_session(test_db: AsyncSession, staff_member, test_event):
    """Create an open attendance session linked to an event."""
    session = await AttendanceService.create_session(
        db=test_db,
        session_name="Summer Reading Kickoff Attendance",
        session_date=date.today(),
        staff_id=staff_member.id,
        event_id=test_event.id,
        event_cost=Decimal("150.00"),
        survey_enabled=True,
        survey_link="https://forms.example.com/survey",
    )
    await test_db.commit()
    await test_db.refresh(session)
    return session


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionCreation:
    """Test attendance session creation and configuration."""

    @pytest.mark.asyncio
    async def test_create_session_with_all_fields(self, test_db: AsyncSession, staff_member, test_event):
        """Test creating a session with all optional fields populated."""
        session = await AttendanceService.create_session(
            db=test_db,
            session_name="Story Hour Attendance",
            session_date=date.today(),
            staff_id=staff_member.id,
            event_id=test_event.id,
            head_count_mode=False,
            event_cost=Decimal("75.50"),
            cost_notes="Supplies and snacks",
            survey_enabled=True,
            survey_link="https://forms.example.com/story-hour",
            notes="Expected high turnout",
        )
        await test_db.commit()

        assert session.id is not None
        assert session.session_name == "Story Hour Attendance"
        assert session.session_date == date.today()
        assert session.status == AttendanceSessionStatus.OPEN
        assert session.qr_code_token is not None
        assert len(session.qr_code_token) == 24
        assert session.head_count_mode is False
        assert session.event_cost == Decimal("75.50")
        assert session.cost_notes == "Supplies and snacks"
        assert session.survey_enabled is True
        assert session.survey_link == "https://forms.example.com/story-hour"
        assert session.opened_by_id == staff_member.id
        assert session.total_checked_in == 0
        assert session.total_walk_ins == 0
        assert session.total_card_scans == 0
        assert session.total_qr_scans == 0

    @pytest.mark.asyncio
    async def test_create_session_minimal_fields(self, test_db: AsyncSession, staff_member):
        """Test creating a session with only required fields."""
        session = await AttendanceService.create_session(
            db=test_db,
            session_name="Quick Event",
            session_date=date.today(),
            staff_id=staff_member.id,
        )
        await test_db.commit()

        assert session.id is not None
        assert session.event_id is None
        assert session.program_id is None
        assert session.head_count_mode is False
        assert session.event_cost is None
        assert session.survey_enabled is True

    @pytest.mark.asyncio
    async def test_create_session_generates_unique_qr_tokens(self, test_db: AsyncSession, staff_member):
        """Each session should have a unique QR code token."""
        session1 = await AttendanceService.create_session(
            db=test_db,
            session_name="Session 1",
            session_date=date.today(),
            staff_id=staff_member.id,
        )
        session2 = await AttendanceService.create_session(
            db=test_db,
            session_name="Session 2",
            session_date=date.today(),
            staff_id=staff_member.id,
        )
        await test_db.commit()

        assert session1.qr_code_token != session2.qr_code_token

    @pytest.mark.asyncio
    async def test_create_session_head_count_mode(self, test_db: AsyncSession, staff_member):
        """Test creating a session in head count mode for large events."""
        session = await AttendanceService.create_session(
            db=test_db,
            session_name="Community Concert",
            session_date=date.today(),
            staff_id=staff_member.id,
            head_count_mode=True,
        )
        await test_db.commit()

        assert session.head_count_mode is True
        assert session.head_count_total == 0


class TestSessionLifecycle:
    """Test session status transitions: open -> closed -> finalized."""

    @pytest.mark.asyncio
    async def test_close_session(self, test_db: AsyncSession, open_session, staff_member):
        """Test closing an open session stops check-ins."""
        session = await AttendanceService.close_session(
            test_db, open_session.id, staff_member.id
        )
        await test_db.commit()

        assert session.status == AttendanceSessionStatus.CLOSED
        assert session.closed_by_id == staff_member.id
        assert session.closed_at is not None

    @pytest.mark.asyncio
    async def test_close_already_closed_session_fails(self, test_db: AsyncSession, open_session, staff_member):
        """Cannot close a session that is already closed."""
        await AttendanceService.close_session(test_db, open_session.id, staff_member.id)
        await test_db.commit()

        with pytest.raises(ValueError, match="not open"):
            await AttendanceService.close_session(test_db, open_session.id, staff_member.id)

    @pytest.mark.asyncio
    async def test_finalize_session(self, test_db: AsyncSession, open_session, staff_member):
        """Test finalizing a session locks all data."""
        # Close first, then finalize
        await AttendanceService.close_session(test_db, open_session.id, staff_member.id)
        session = await AttendanceService.finalize_session(test_db, open_session.id)
        await test_db.commit()

        assert session.status == AttendanceSessionStatus.FINALIZED

    @pytest.mark.asyncio
    async def test_list_sessions_with_filters(self, test_db: AsyncSession, staff_member):
        """Test listing sessions with status and date filters."""
        # Create sessions on different dates
        await AttendanceService.create_session(
            db=test_db,
            session_name="Today's Session",
            session_date=date.today(),
            staff_id=staff_member.id,
        )
        await AttendanceService.create_session(
            db=test_db,
            session_name="Yesterday's Session",
            session_date=date.today() - timedelta(days=1),
            staff_id=staff_member.id,
        )
        await test_db.commit()

        # List all
        sessions, total = await AttendanceService.list_sessions(test_db)
        assert total >= 2

        # Filter by date
        sessions, total = await AttendanceService.list_sessions(
            test_db, start_date=date.today()
        )
        assert all(s.session_date >= date.today() for s in sessions)


# ============================================================================
# Check-In Tests
# ============================================================================


class TestQRCodeCheckIn:
    """Test QR code self-service check-in."""

    @pytest.mark.asyncio
    async def test_qr_check_in_anonymous(self, test_db: AsyncSession, open_session):
        """Test QR check-in without patron ID (anonymous)."""
        check_in = await AttendanceService.check_in_qr(
            db=test_db,
            qr_token=open_session.qr_code_token,
            guest_name="Walk-In Visitor",
            guest_email="visitor@example.com",
            age_range="18-34",
        )
        await test_db.commit()

        assert check_in.id is not None
        assert check_in.session_id == open_session.id
        assert check_in.check_in_method == CheckInMethod.QR_CODE
        assert check_in.guest_name == "Walk-In Visitor"
        assert check_in.guest_email == "visitor@example.com"
        assert check_in.age_range == "18-34"
        assert check_in.patron_id is None

    @pytest.mark.asyncio
    async def test_qr_check_in_with_patron(self, test_db: AsyncSession, open_session, patron_with_card):
        """Test QR check-in with a logged-in patron."""
        check_in = await AttendanceService.check_in_qr(
            db=test_db,
            qr_token=open_session.qr_code_token,
            patron_id=patron_with_card.id,
        )
        await test_db.commit()

        assert check_in.patron_id == patron_with_card.id
        assert check_in.check_in_method == CheckInMethod.QR_CODE

    @pytest.mark.asyncio
    async def test_qr_check_in_invalid_token(self, test_db: AsyncSession):
        """Test QR check-in with invalid token fails."""
        with pytest.raises(ValueError, match="Invalid QR code"):
            await AttendanceService.check_in_qr(
                db=test_db,
                qr_token="nonexistent_token",
            )

    @pytest.mark.asyncio
    async def test_qr_check_in_closed_session(self, test_db: AsyncSession, open_session, staff_member):
        """Test QR check-in on closed session fails."""
        await AttendanceService.close_session(test_db, open_session.id, staff_member.id)
        await test_db.commit()

        with pytest.raises(ValueError, match="no longer accepting"):
            await AttendanceService.check_in_qr(
                db=test_db,
                qr_token=open_session.qr_code_token,
            )

    @pytest.mark.asyncio
    async def test_qr_check_in_updates_session_counts(self, test_db: AsyncSession, open_session):
        """QR check-in should increment session QR scan count."""
        await AttendanceService.check_in_qr(
            db=test_db,
            qr_token=open_session.qr_code_token,
            guest_name="Visitor 1",
        )
        await test_db.commit()
        await test_db.refresh(open_session)

        assert open_session.total_checked_in == 1
        assert open_session.total_qr_scans == 1


class TestLibraryCardCheckIn:
    """Test library card scan check-in."""

    @pytest.mark.asyncio
    async def test_card_scan_registered_patron(
        self, test_db: AsyncSession, open_session, patron_with_card, staff_member
    ):
        """Test scanning a registered patron's library card."""
        check_in = await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=open_session.id,
            library_card_number=patron_with_card.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()

        assert check_in.patron_id == patron_with_card.id
        assert check_in.library_card_number == "LIB00042"
        assert check_in.check_in_method == CheckInMethod.LIBRARY_CARD
        assert check_in.checked_in_by_id == staff_member.id

    @pytest.mark.asyncio
    async def test_card_scan_auto_age_from_dob(
        self, test_db: AsyncSession, open_session, patron_with_card, staff_member
    ):
        """Library card scan should auto-derive age range from patron's DOB."""
        check_in = await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=open_session.id,
            library_card_number=patron_with_card.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()

        # Patron born 1990 => ~35 => age range 35-54
        assert check_in.age_range == AgeRange.ADULT_35_54

    @pytest.mark.asyncio
    async def test_card_scan_child_age_range(
        self, test_db: AsyncSession, open_session, child_patron, staff_member
    ):
        """Library card scan for child should get child age range."""
        check_in = await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=open_session.id,
            library_card_number=child_patron.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()

        # Child born 2018 => ~7 => age range 6-12
        assert check_in.age_range == AgeRange.CHILD_6_12

    @pytest.mark.asyncio
    async def test_card_scan_unknown_card(
        self, test_db: AsyncSession, open_session, staff_member
    ):
        """Scanning an unregistered card should still create a check-in."""
        check_in = await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=open_session.id,
            library_card_number="UNKNOWN123",
            staff_id=staff_member.id,
        )
        await test_db.commit()

        assert check_in.patron_id is None
        assert check_in.library_card_number == "UNKNOWN123"
        assert check_in.age_range == AgeRange.UNKNOWN

    @pytest.mark.asyncio
    async def test_card_scan_duplicate_prevention(
        self, test_db: AsyncSession, open_session, patron_with_card, staff_member
    ):
        """Cannot scan the same patron's card twice in one session."""
        await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=open_session.id,
            library_card_number=patron_with_card.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()

        with pytest.raises(ValueError, match="already checked in"):
            await AttendanceService.check_in_library_card(
                db=test_db,
                session_id=open_session.id,
                library_card_number=patron_with_card.library_card,
                staff_id=staff_member.id,
            )

    @pytest.mark.asyncio
    async def test_card_scan_updates_session_counts(
        self, test_db: AsyncSession, open_session, patron_with_card, staff_member
    ):
        """Card scan should increment session card scan count."""
        await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=open_session.id,
            library_card_number=patron_with_card.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()
        await test_db.refresh(open_session)

        assert open_session.total_checked_in == 1
        assert open_session.total_card_scans == 1


class TestWalkInCheckIn:
    """Test walk-in quick-add functionality."""

    @pytest.mark.asyncio
    async def test_walk_in_with_all_info(self, test_db: AsyncSession, open_session, staff_member):
        """Test adding a walk-in with name, email, and age range."""
        check_in = await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            guest_name="Walk-In Guest",
            guest_email="guest@example.com",
            guest_phone="555-0123",
            age_range="35-54",
            notes="Referred by friend",
        )
        await test_db.commit()

        assert check_in.check_in_method == CheckInMethod.WALK_IN
        assert check_in.guest_name == "Walk-In Guest"
        assert check_in.guest_email == "guest@example.com"
        assert check_in.guest_phone == "555-0123"
        assert check_in.age_range == "35-54"
        assert check_in.notes == "Referred by friend"
        assert check_in.checked_in_by_id == staff_member.id

    @pytest.mark.asyncio
    async def test_walk_in_anonymous(self, test_db: AsyncSession, open_session, staff_member):
        """Test adding a completely anonymous walk-in (just a count)."""
        check_in = await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            age_range="unknown",
        )
        await test_db.commit()

        assert check_in.guest_name is None
        assert check_in.guest_email is None
        assert check_in.age_range == "unknown"

    @pytest.mark.asyncio
    async def test_walk_in_updates_session_counts(self, test_db: AsyncSession, open_session, staff_member):
        """Walk-in should increment session walk-in count."""
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
        )
        await test_db.commit()
        await test_db.refresh(open_session)

        assert open_session.total_checked_in == 1
        assert open_session.total_walk_ins == 1


class TestHeadCountMode:
    """Test head count mode for large events."""

    @pytest.mark.asyncio
    async def test_update_head_count(self, test_db: AsyncSession, open_session):
        """Test setting head count total."""
        session = await AttendanceService.update_head_count(
            db=test_db,
            session_id=open_session.id,
            total=250,
        )
        await test_db.commit()

        assert session.head_count_total == 250

    @pytest.mark.asyncio
    async def test_update_head_count_with_age_breakdown(self, test_db: AsyncSession, open_session):
        """Test setting head count with age range breakdown."""
        age_breakdown = {
            "0-5": 20,
            "6-12": 45,
            "13-17": 15,
            "18-34": 60,
            "35-54": 70,
            "55-64": 25,
            "65+": 15,
        }
        session = await AttendanceService.update_head_count(
            db=test_db,
            session_id=open_session.id,
            total=250,
            by_age=age_breakdown,
        )
        await test_db.commit()

        assert session.head_count_total == 250
        assert session.head_count_by_age == age_breakdown

    @pytest.mark.asyncio
    async def test_head_count_can_be_updated_multiple_times(self, test_db: AsyncSession, open_session):
        """Head count can be revised as more people arrive."""
        await AttendanceService.update_head_count(test_db, open_session.id, total=100)
        await test_db.commit()

        session = await AttendanceService.update_head_count(test_db, open_session.id, total=175)
        await test_db.commit()

        assert session.head_count_total == 175


# ============================================================================
# Repeat Attendee Detection Tests
# ============================================================================


class TestRepeatAttendeeDetection:
    """Test repeat attendee recognition across sessions."""

    @pytest.mark.asyncio
    async def test_first_time_attendee(self, test_db: AsyncSession, open_session, staff_member):
        """First-time attendees should not be flagged as repeat."""
        check_in = await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            guest_email="firsttime@example.com",
        )
        await test_db.commit()

        assert check_in.is_repeat_attendee is False
        assert check_in.previous_visit_count == 0

    @pytest.mark.asyncio
    async def test_repeat_attendee_by_email(self, test_db: AsyncSession, staff_member):
        """Attendees should be recognized as repeat across sessions by email."""
        # Create first session and check in
        session1 = await AttendanceService.create_session(
            db=test_db,
            session_name="Session 1",
            session_date=date.today() - timedelta(days=7),
            staff_id=staff_member.id,
        )
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=session1.id,
            staff_id=staff_member.id,
            guest_email="repeat@example.com",
        )
        await test_db.commit()

        # Create second session and check in same email
        session2 = await AttendanceService.create_session(
            db=test_db,
            session_name="Session 2",
            session_date=date.today(),
            staff_id=staff_member.id,
        )
        check_in = await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=session2.id,
            staff_id=staff_member.id,
            guest_email="repeat@example.com",
        )
        await test_db.commit()

        assert check_in.is_repeat_attendee is True
        assert check_in.previous_visit_count == 1

    @pytest.mark.asyncio
    async def test_repeat_attendee_by_patron_id(
        self, test_db: AsyncSession, staff_member, patron_with_card
    ):
        """Patrons should be recognized as repeat across sessions by patron ID."""
        session1 = await AttendanceService.create_session(
            db=test_db,
            session_name="Session A",
            session_date=date.today() - timedelta(days=3),
            staff_id=staff_member.id,
        )
        await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=session1.id,
            library_card_number=patron_with_card.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()

        session2 = await AttendanceService.create_session(
            db=test_db,
            session_name="Session B",
            session_date=date.today(),
            staff_id=staff_member.id,
        )
        check_in = await AttendanceService.check_in_library_card(
            db=test_db,
            session_id=session2.id,
            library_card_number=patron_with_card.library_card,
            staff_id=staff_member.id,
        )
        await test_db.commit()

        assert check_in.is_repeat_attendee is True
        assert check_in.previous_visit_count >= 1


# ============================================================================
# Survey Distribution Tests
# ============================================================================


class TestSurveyDistribution:
    """Test post-event survey sending."""

    @pytest.mark.asyncio
    async def test_send_surveys_to_attendees_with_email(
        self, test_db: AsyncSession, open_session, staff_member
    ):
        """Surveys should be sent to attendees who provided email."""
        # Add some check-ins with and without email
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            guest_email="has_email@example.com",
        )
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            # No email
        )
        await test_db.commit()

        result = await AttendanceService.send_surveys(test_db, open_session.id)
        await test_db.commit()

        assert result["total_sent"] == 1
        assert result["total_eligible"] == 2

    @pytest.mark.asyncio
    async def test_send_surveys_without_link_fails(self, test_db: AsyncSession, staff_member):
        """Cannot send surveys if no survey link is configured."""
        session = await AttendanceService.create_session(
            db=test_db,
            session_name="No Survey Session",
            session_date=date.today(),
            staff_id=staff_member.id,
            survey_link=None,
        )
        await test_db.commit()

        with pytest.raises(ValueError, match="No survey link"):
            await AttendanceService.send_surveys(test_db, session.id)


# ============================================================================
# Dashboard & Analytics Tests
# ============================================================================


class TestDashboard:
    """Test attendance dashboard metrics."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_metrics(self, test_db: AsyncSession, open_session, staff_member):
        """Dashboard should return today's stats and distributions."""
        # Add some check-ins
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            age_range="18-34",
        )
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            age_range="35-54",
        )
        await test_db.commit()

        dashboard = await AttendanceService.get_dashboard(test_db)

        assert dashboard["today_sessions"] >= 1
        assert dashboard["today_total_attendance"] >= 2
        assert "age_distribution" in dashboard
        assert "method_distribution" in dashboard
        assert "recent_sessions" in dashboard
        assert isinstance(dashboard["repeat_attendee_rate"], float)


class TestROICalculation:
    """Test ROI (cost per attendee) calculation."""

    @pytest.mark.asyncio
    async def test_roi_report_basic(self, test_db: AsyncSession, open_session, staff_member):
        """ROI report should calculate cost per attendee."""
        # Add check-ins to the session that has event_cost=$150
        for i in range(5):
            await AttendanceService.check_in_walk_in(
                db=test_db,
                session_id=open_session.id,
                staff_id=staff_member.id,
                guest_name=f"Guest {i}",
            )
        await test_db.commit()

        report = await AttendanceService.get_roi_report(test_db)

        assert report["total_events"] >= 1
        assert report["total_attendance"] >= 5
        assert report["total_cost"] >= 150.0
        # Cost per attendee = $150 / 5 = $30
        assert report["cost_per_attendee"] > 0

    @pytest.mark.asyncio
    async def test_roi_report_empty_period(self, test_db: AsyncSession):
        """ROI report with no data should return zeros."""
        far_future = date.today() + timedelta(days=365 * 10)
        report = await AttendanceService.get_roi_report(
            test_db,
            start_date=far_future,
            end_date=far_future + timedelta(days=1),
        )

        assert report["total_events"] == 0
        assert report["total_attendance"] == 0
        assert report["cost_per_attendee"] == 0


# ============================================================================
# Session Check-In Listing
# ============================================================================


class TestCheckInListing:
    """Test retrieving check-in records for a session."""

    @pytest.mark.asyncio
    async def test_get_session_check_ins_ordered(
        self, test_db: AsyncSession, open_session, staff_member
    ):
        """Check-ins should be returned ordered by time."""
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            guest_name="First",
        )
        await AttendanceService.check_in_walk_in(
            db=test_db,
            session_id=open_session.id,
            staff_id=staff_member.id,
            guest_name="Second",
        )
        await test_db.commit()

        check_ins = await AttendanceService.get_session_check_ins(test_db, open_session.id)

        assert len(check_ins) == 2
        # Ordered by checked_in_at desc (most recent first)
        assert check_ins[0].checked_in_at >= check_ins[1].checked_in_at

    @pytest.mark.asyncio
    async def test_get_check_ins_empty_session(self, test_db: AsyncSession, open_session):
        """Empty session should return empty list."""
        check_ins = await AttendanceService.get_session_check_ins(test_db, open_session.id)
        assert check_ins == []


# ============================================================================
# Model Validation Tests
# ============================================================================


class TestModelValidation:
    """Test Pydantic schema validation."""

    def test_session_create_schema_validates(self):
        """Test AttendanceSessionCreate schema accepts valid data."""
        from app.schemas.attendance import AttendanceSessionCreate

        schema = AttendanceSessionCreate(
            session_name="Test Session",
            session_date=date.today(),
            head_count_mode=False,
            survey_enabled=True,
        )
        assert schema.session_name == "Test Session"

    def test_session_create_schema_rejects_empty_name(self):
        """Test AttendanceSessionCreate rejects empty session name."""
        from app.schemas.attendance import AttendanceSessionCreate

        with pytest.raises(Exception):
            AttendanceSessionCreate(
                session_name="",
                session_date=date.today(),
            )

    def test_walk_in_schema_validates_age_range(self):
        """Test WalkInCheckIn schema validates age_range values."""
        from app.schemas.attendance import WalkInCheckIn

        schema = WalkInCheckIn(session_id=1, age_range="18-34")
        assert schema.age_range == "18-34"

    def test_walk_in_schema_rejects_invalid_age_range(self):
        """Test WalkInCheckIn schema rejects invalid age_range."""
        from app.schemas.attendance import WalkInCheckIn

        with pytest.raises(Exception):
            WalkInCheckIn(session_id=1, age_range="invalid-range")

    def test_qr_check_in_schema_validates(self):
        """Test QRCodeCheckIn schema."""
        from app.schemas.attendance import QRCodeCheckIn

        schema = QRCodeCheckIn(
            qr_token="abc123",
            guest_name="Test",
            age_range="65+",
        )
        assert schema.qr_token == "abc123"
        assert schema.age_range == "65+"

    def test_head_count_schema_rejects_negative(self):
        """Test HeadCountUpdate rejects negative total."""
        from app.schemas.attendance import HeadCountUpdate

        with pytest.raises(Exception):
            HeadCountUpdate(session_id=1, total=-5)
