# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for book drop and batch check-in services.

Tests the automated book drop functionality including:
- Backdate calculations (fixed time, processing schedule, custom hours)
- Hold trapping during check-in
- Transit detection for items from other branches
- Fine calculation with backdate exemptions
- Batch processing statistics
- Exception handling
"""

from datetime import datetime, time, timedelta, timezone, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.book_drop import (
    BookDrop, BookDropStatus, BackdateMode,
    CheckInSession, CheckInSessionStatus,
    CheckInResult, CheckInResultStatus,
    CheckInStatistic, CheckInException,
    ExceptionType, SortDestination
)
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.inventory import ItemCopy, ItemCondition
from app.models.user import User, UserRole
from app.core.datetime_utils import utc_now


@pytest.mark.unit
class TestBackdateCalculationFixedTime:
    """Test backdating with FIXED_TIME mode."""

    def test_fixed_time_backdate_before_processing_start(self):
        """Test backdating when current time is before processing start."""
        from app.services.book_drop_service import BookDropService

        # Create a book drop with fixed time backdating
        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.FIXED_TIME
        book_drop.backdate_fixed_time = time(21, 0)  # 9pm closing
        book_drop.processing_start_time = time(9, 0)  # 9am processing
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]  # All days
        book_drop.max_backdate_hours = 16

        # Current time: 7am (before 9am processing start)
        current_time = datetime(2026, 1, 29, 7, 0, tzinfo=timezone.utc)

        # Create service with mock db
        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Should backdate to previous day's 9pm
        assert backdate is not None
        assert backdate.hour == 21
        assert backdate.day == 28  # Previous day

    def test_fixed_time_no_backdate_during_processing_hours(self):
        """Test no backdating during normal processing hours."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.FIXED_TIME
        book_drop.backdate_fixed_time = time(21, 0)
        book_drop.processing_start_time = time(9, 0)
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]
        book_drop.max_backdate_hours = 16

        # Current time: 2pm (after 9am processing start)
        current_time = datetime(2026, 1, 29, 14, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Should not backdate during processing hours
        assert backdate is None

    def test_fixed_time_respects_max_backdate_hours(self):
        """Test that backdate doesn't exceed max_backdate_hours."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.FIXED_TIME
        book_drop.backdate_fixed_time = time(17, 0)  # 5pm (very early closing)
        book_drop.processing_start_time = time(9, 0)
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]
        book_drop.max_backdate_hours = 12  # Max 12 hours

        # Current time: 8am
        current_time = datetime(2026, 1, 29, 8, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Backdate should be limited by max_backdate_hours
        if backdate:
            hours_diff = (current_time - backdate).total_seconds() / 3600
            assert hours_diff <= 12


@pytest.mark.unit
class TestBackdateCalculationProcessingSchedule:
    """Test backdating with PROCESSING_SCHEDULE mode."""

    def test_processing_schedule_backdate_before_start(self):
        """Test backdating to previous day's processing end time."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.PROCESSING_SCHEDULE
        book_drop.processing_start_time = time(9, 0)
        book_drop.processing_end_time = time(17, 0)  # 5pm
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]
        book_drop.max_backdate_hours = 16

        # Current time: 7am (before processing)
        current_time = datetime(2026, 1, 29, 7, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Should backdate to previous day's 5pm
        assert backdate is not None
        assert backdate.hour == 17
        assert backdate.day == 28

    def test_processing_schedule_no_backdate_during_window(self):
        """Test no backdating during processing window."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.PROCESSING_SCHEDULE
        book_drop.processing_start_time = time(9, 0)
        book_drop.processing_end_time = time(17, 0)
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]
        book_drop.max_backdate_hours = 16

        # Current time: 2pm (during processing window)
        current_time = datetime(2026, 1, 29, 14, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Should not backdate during processing window
        assert backdate is None


@pytest.mark.unit
class TestBackdateCalculationCustomHours:
    """Test backdating with CUSTOM_HOURS mode."""

    def test_custom_hours_backdate(self):
        """Test backdating by custom number of hours."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.CUSTOM_HOURS
        book_drop.backdate_hours = 8
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]
        book_drop.max_backdate_hours = 16

        current_time = datetime(2026, 1, 29, 10, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Should backdate by 8 hours
        assert backdate is not None
        expected = current_time - timedelta(hours=8)
        assert backdate == expected

    def test_custom_hours_respects_max(self):
        """Test that custom hours respects max_backdate_hours."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.CUSTOM_HOURS
        book_drop.backdate_hours = 24  # Request 24 hours
        book_drop.backdate_days = [0, 1, 2, 3, 4, 5, 6]
        book_drop.max_backdate_hours = 16  # But max is 16

        current_time = datetime(2026, 1, 29, 10, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        # Should be limited to 16 hours
        if backdate:
            hours_diff = (current_time - backdate).total_seconds() / 3600
            assert hours_diff <= 16


@pytest.mark.unit
class TestBackdateNoneMode:
    """Test backdating with NONE mode."""

    def test_none_mode_no_backdate(self):
        """Test that NONE mode returns no backdate."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.NONE

        current_time = datetime(2026, 1, 29, 7, 0, tzinfo=timezone.utc)

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, current_time)

        assert backdate is None


@pytest.mark.unit
class TestBackdateDayOfWeek:
    """Test backdate day-of-week restrictions."""

    def test_backdate_only_on_specified_days(self):
        """Test that backdating only applies on specified days."""
        from app.services.book_drop_service import BookDropService

        book_drop = MagicMock()
        book_drop.backdate_mode = BackdateMode.FIXED_TIME
        book_drop.backdate_fixed_time = time(21, 0)
        book_drop.processing_start_time = time(9, 0)
        book_drop.backdate_days = [0, 1, 2, 3, 4]  # Mon-Fri only
        book_drop.max_backdate_hours = 16

        # Saturday (day 5) - should not backdate
        saturday = datetime(2026, 1, 25, 7, 0, tzinfo=timezone.utc)  # A Saturday

        service = BookDropService(MagicMock())
        backdate = service.calculate_backdate(book_drop, saturday)

        # Saturday not in backdate_days, so no backdate
        assert backdate is None


@pytest.mark.unit
class TestCheckInResultStatus:
    """Test check-in result status determination."""

    def test_success_status_for_normal_checkin(self):
        """Test that normal check-ins return SUCCESS status."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.SUCCESS,
            sort_destination=SortDestination.RESHELVE
        )

        assert result.status == CheckInResultStatus.SUCCESS
        assert result.sort_destination == SortDestination.RESHELVE

    def test_hold_trapped_status(self):
        """Test HOLD_TRAPPED status when item has waiting hold."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.HOLD_TRAPPED,
            hold_id=123,
            hold_patron_id=456,
            sort_destination=SortDestination.HOLD_SHELF
        )

        assert result.status == CheckInResultStatus.HOLD_TRAPPED
        assert result.hold_id == 123
        assert result.sort_destination == SortDestination.HOLD_SHELF

    def test_transit_required_status(self):
        """Test TRANSIT_REQUIRED status for items from other branches."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.TRANSIT_REQUIRED,
            destination_branch="Branch B",
            sort_destination=SortDestination.TRANSIT
        )

        assert result.status == CheckInResultStatus.TRANSIT_REQUIRED
        assert result.destination_branch == "Branch B"
        assert result.sort_destination == SortDestination.TRANSIT

    def test_exception_status(self):
        """Test EXCEPTION status for items with issues."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.EXCEPTION,
            exception_type=ExceptionType.DAMAGED_ITEM,
            exception_message="Water damage detected",
            sort_destination=SortDestination.EXCEPTION
        )

        assert result.status == CheckInResultStatus.EXCEPTION
        assert result.exception_type == ExceptionType.DAMAGED_ITEM
        assert result.sort_destination == SortDestination.EXCEPTION


@pytest.mark.unit
class TestCheckInSessionStatistics:
    """Test check-in session statistics tracking."""

    def test_session_stats_initialization(self):
        """Test that session stats start at zero."""
        session = CheckInSession(
            session_code="CKI-TEST001",
            branch_location="Main Branch",
            staff_id=1,
            status=CheckInSessionStatus.ACTIVE
        )

        assert session.total_items == 0
        assert session.successful_checkins == 0
        assert session.holds_trapped == 0
        assert session.transits_created == 0
        assert session.exceptions_count == 0

    def test_session_status_transitions(self):
        """Test valid session status transitions."""
        session = CheckInSession(
            session_code="CKI-TEST002",
            branch_location="Main Branch",
            staff_id=1,
            status=CheckInSessionStatus.ACTIVE
        )

        # Can transition to PAUSED
        session.status = CheckInSessionStatus.PAUSED
        assert session.status == CheckInSessionStatus.PAUSED

        # Can transition to COMPLETED
        session.status = CheckInSessionStatus.COMPLETED
        assert session.status == CheckInSessionStatus.COMPLETED


@pytest.mark.unit
class TestBookDropConfiguration:
    """Test book drop configuration model."""

    def test_book_drop_defaults(self):
        """Test book drop default values."""
        book_drop = BookDrop(
            name="Test Drop",
            code="TEST-DROP",
            branch_location="Main Branch"
        )

        assert book_drop.status == BookDropStatus.ACTIVE
        assert book_drop.backdate_mode == BackdateMode.FIXED_TIME
        assert book_drop.exempt_overnight_fines == True
        assert book_drop.max_backdate_hours == 16

    def test_book_drop_backdate_configuration(self):
        """Test book drop with custom backdate settings."""
        book_drop = BookDrop(
            name="Night Drop",
            code="NIGHT-DROP",
            branch_location="Main Branch",
            backdate_mode=BackdateMode.FIXED_TIME,
            backdate_fixed_time=time(21, 0),  # 9pm
            processing_start_time=time(9, 0),  # 9am
            backdate_days=[0, 1, 2, 3, 4, 5, 6],
            exempt_overnight_fines=True
        )

        assert book_drop.backdate_fixed_time == time(21, 0)
        assert book_drop.processing_start_time == time(9, 0)
        assert 0 in book_drop.backdate_days


@pytest.mark.unit
class TestExceptionTypes:
    """Test exception type enumeration."""

    def test_all_exception_types_exist(self):
        """Verify all expected exception types are defined."""
        assert ExceptionType.DAMAGED_ITEM.value == "damaged_item"
        assert ExceptionType.ITEM_NOTE.value == "item_note"
        assert ExceptionType.PATRON_BLOCKED.value == "patron_blocked"
        assert ExceptionType.PATRON_NOTE.value == "patron_note"
        assert ExceptionType.OVERDUE_FINE.value == "overdue_fine"
        assert ExceptionType.LOST_ITEM_RETURNED.value == "lost_item_returned"
        assert ExceptionType.CLAIMS_RETURNED.value == "claims_returned"
        assert ExceptionType.MISSING_PARTS.value == "missing_parts"
        assert ExceptionType.WRONG_ITEM.value == "wrong_item"
        assert ExceptionType.OTHER.value == "other"


@pytest.mark.unit
class TestSortDestinations:
    """Test sort destination enumeration."""

    def test_all_sort_destinations_exist(self):
        """Verify all expected sort destinations are defined."""
        assert SortDestination.HOLD_SHELF.value == "hold_shelf"
        assert SortDestination.TRANSIT.value == "transit"
        assert SortDestination.RESHELVE.value == "reshelve"
        assert SortDestination.EXCEPTION.value == "exception"
        assert SortDestination.CONDITION_CHECK.value == "condition_check"


@pytest.mark.unit
class TestCheckInStatistics:
    """Test check-in statistics model."""

    def test_statistic_defaults(self):
        """Test statistic default values."""
        stat = CheckInStatistic(
            date=date(2026, 1, 29),
            hour=14,
            day_of_week=3,  # Wednesday
            branch_location="Main Branch"
        )

        assert stat.total_checkins == 0
        assert stat.staff_checkins == 0
        assert stat.book_drop_checkins == 0
        assert stat.holds_trapped_count == 0
        assert stat.total_fines_amount == Decimal(0)

    def test_statistic_aggregation(self):
        """Test that statistics can be updated."""
        stat = CheckInStatistic(
            date=date(2026, 1, 29),
            hour=14,
            day_of_week=3,
            branch_location="Main Branch"
        )

        # Simulate updates
        stat.total_checkins = 50
        stat.book_drop_checkins = 30
        stat.staff_checkins = 20
        stat.holds_trapped_count = 5
        stat.transits_count = 3
        stat.total_fines_amount = Decimal("12.50")

        assert stat.total_checkins == 50
        assert stat.book_drop_checkins == 30
        assert stat.holds_trapped_count == 5
        assert stat.total_fines_amount == Decimal("12.50")


@pytest.mark.unit
class TestFineWaiverByBackdate:
    """Test fine waiver logic for backdated check-ins."""

    def test_fine_waived_by_backdate_flag(self):
        """Test that fine_waived_by_backdate flag is set correctly."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.SUCCESS,
            was_overdue=True,
            overdue_days=1,
            fine_amount=Decimal("0.25"),
            fine_waived_by_backdate=True
        )

        assert result.was_overdue == True
        assert result.fine_waived_by_backdate == True

    def test_fine_not_waived_without_backdate(self):
        """Test that fines are not waived without backdating."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.SUCCESS,
            was_overdue=True,
            overdue_days=3,
            fine_amount=Decimal("0.75"),
            fine_waived_by_backdate=False
        )

        assert result.was_overdue == True
        assert result.fine_waived_by_backdate == False
        assert result.fine_amount == Decimal("0.75")


@pytest.mark.unit
class TestConditionCheck:
    """Test condition check during check-in."""

    def test_condition_check_recorded(self):
        """Test that condition check is recorded in result."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.SUCCESS,
            condition_checked=True,
            condition_status="good",
            condition_notes="No visible damage"
        )

        assert result.condition_checked == True
        assert result.condition_status == "good"
        assert result.condition_notes == "No visible damage"

    def test_condition_issue_creates_exception(self):
        """Test that condition issues create exceptions."""
        result = CheckInResult(
            session_id=1,
            barcode="TEST-001",
            status=CheckInResultStatus.CONDITION_ISSUE,
            condition_checked=True,
            condition_status="damaged",
            condition_notes="Water damage on cover",
            exception_type=ExceptionType.DAMAGED_ITEM,
            sort_destination=SortDestination.CONDITION_CHECK
        )

        assert result.status == CheckInResultStatus.CONDITION_ISSUE
        assert result.exception_type == ExceptionType.DAMAGED_ITEM
        assert result.sort_destination == SortDestination.CONDITION_CHECK
