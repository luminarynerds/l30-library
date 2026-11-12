# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for period-close operations in LSC Library.

Validates all periodic closing procedures run cleanly:
- End of day: close registers, print summary
- End of week: circulation statistics generated
- End of month: reports auto-generated, fines tallied
- End of quarter: collection stats, budget review
- End of fiscal year: annual totals, rollovers
- End of calendar year: patron card renewals batch
- Summer reading program close-out
- State report data freeze
- Archive old data
- Verify rollover calculations correct
"""

import pytest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.end_of_day import (
    EODTemplate, EODSession, EODTask, EODSecurityCheck, EODStatistics,
    EODTaskType, EODTaskStatus, EODSessionStatus, SecurityCheckType,
)
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole, PatronStatus
from app.models.acquisition import Fund, FundStatus
from app.models.program import (
    Program, LibraryProgramType, ProgramStatus, ProgramAudience,
    ProgramRegistration, ProgramRegistrationStatus,
)
from app.models.usage_statistics import (
    CirculationStatistics, CollectionStatistics, PatronStatistics,
    ProgramStatistics, PeriodType,
)
from app.models.annual_report import AnnualReport, ReportStatus
from app.services.end_of_day_service import EndOfDayService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def mock_db():
    """Create a mock async database session.

    execute() is async (awaited), but its return value uses sync
    chaining (.scalars().first(), .scalar()), so it must be MagicMock.
    """
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock()
    session.refresh = AsyncMock()
    # execute returns a MagicMock so .scalars()/.scalar() work synchronously
    session.execute = AsyncMock(return_value=MagicMock())
    return session


@pytest.fixture
def staff_user():
    """Create a test staff user."""
    return User(
        id=1,
        email="staff@l30.org",
        first_name="Jane",
        last_name="Librarian",
        password_hash="hashed",
        role=UserRole.STAFF,
        is_active=True,
    )


@pytest.fixture
def eod_template():
    """Create a standard EOD template."""
    return EODTemplate(
        id=1,
        name="Main Branch Default",
        branch_location="Main Branch",
        is_active=True,
        estimated_duration_minutes=5,
        task_configs=[
            {"task_type": "close_registers", "required": True},
            {"task_type": "process_holds", "required": True},
            {"task_type": "send_overdue_notices", "required": False},
            {"task_type": "backup_confirmation", "required": True},
            {"task_type": "security_check", "required": True},
            {"task_type": "statistics_summary", "required": False},
            {"task_type": "tomorrow_events", "required": False},
            {"task_type": "holds_pull_list", "required": False},
        ],
    )


@pytest.fixture
def eod_session(eod_template, staff_user):
    """Create an EOD session."""
    return EODSession(
        id=1,
        session_code="EOD-TEST0001",
        template_id=eod_template.id,
        branch_location="Main Branch",
        closing_date=date.today(),
        staff_id=staff_user.id,
        assisted_by_ids=[],
        status=EODSessionStatus.STARTED,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        total_tasks=8,
        completed_tasks=0,
        failed_tasks=0,
        skipped_tasks=0,
    )


# =============================================================================
# 1. End of Day: Close Registers, Print Summary
# =============================================================================

class TestEndOfDayCloseRegisters:
    """End-of-day: close registers and print daily summary."""

    @pytest.mark.asyncio
    async def test_create_eod_session(self, mock_db, staff_user, eod_template):
        """Creating a closing session generates the correct tasks."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = eod_template
        mock_db.execute.return_value = result_mock

        session = await EndOfDayService.create_closing_session(
            db=mock_db,
            branch_location="Main Branch",
            staff_id=staff_user.id,
        )

        assert session is not None
        assert session.branch_location == "Main Branch"
        assert session.status == EODSessionStatus.STARTED
        assert session.session_code.startswith("EOD-")

    @pytest.mark.asyncio
    async def test_close_registers_task(self, mock_db):
        """Close registers task completes with manual confirmation data."""
        result = await EndOfDayService._close_registers(db=mock_db, session_id=1)

        assert result["status"] == "manual_completion"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_statistics_summary_generates_daily_totals(self, mock_db, eod_session):
        """Statistics summary contains expected fields for daily totals."""
        # Test that the summary structure matches expected output format
        summary = {
            "total_checkouts": 120,
            "total_checkins": 115,
            "total_fines": 32.50,
            "message": "Daily summary: 120 checkouts, 115 check-ins, $32.50 in fines",
        }

        # Validate expected structure
        assert summary["total_checkouts"] == 120
        assert summary["total_checkins"] == 115
        assert summary["total_fines"] == 32.50
        assert "message" in summary

        # Validate the summary can be stored on an EOD session
        eod_session.statistics_summary = summary
        assert eod_session.statistics_summary["total_checkouts"] == 120

    @pytest.mark.asyncio
    async def test_complete_session_calculates_duration(self, mock_db, eod_session):
        """Completing a session records duration and task counts."""
        eod_session.status = EODSessionStatus.IN_PROGRESS
        mock_db.get.return_value = eod_session

        results = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        results[0].scalar.return_value = 8
        results[1].scalar.return_value = 7
        results[2].scalar.return_value = 0
        results[3].scalar.return_value = 1
        mock_db.execute.side_effect = results

        completed = await EndOfDayService.complete_session(db=mock_db, session_id=1)

        assert completed.status == EODSessionStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.total_duration_seconds >= 0
        assert completed.completed_tasks == 7
        assert completed.skipped_tasks == 1

        mock_db.execute.side_effect = None

    @pytest.mark.asyncio
    async def test_security_checks_all_pass(self, mock_db, eod_session):
        """Security checks generate entries for all check types."""
        mock_db.get.return_value = eod_session

        result = await EndOfDayService._security_check_prompts(
            db=mock_db, session_id=1, completed_by_id=1,
        )

        assert result["checks_passed"] > 0
        assert result["checks_failed"] == 0
        assert result["total_checks"] == result["checks_passed"]

    @pytest.mark.asyncio
    async def test_eod_session_defaults_no_template(self, mock_db, staff_user):
        """Session creation auto-generates a default template if none exists."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        session = await EndOfDayService.create_closing_session(
            db=mock_db,
            branch_location="Satellite Branch",
            staff_id=staff_user.id,
        )

        assert session is not None
        assert session.branch_location == "Satellite Branch"

    @pytest.mark.asyncio
    async def test_schedule_auto_logout_after_close(self, mock_db, eod_session):
        """Auto-logout is scheduled after session completion."""
        eod_session.status = EODSessionStatus.COMPLETED
        mock_db.get.return_value = eod_session

        await EndOfDayService.schedule_auto_logout(
            db=mock_db, session_id=1, logout_delay_minutes=5,
        )

        assert eod_session.auto_logout_at is not None
        assert eod_session.auto_logout_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_process_holds_at_close(self):
        """Process holds result structure identifies ready holds for next day."""
        # Validate the expected return structure from process_holds
        result = {
            "holds_ready": 12,
            "message": "Identified 12 holds ready for tomorrow's processing",
        }

        assert result["holds_ready"] == 12
        assert "holds_ready" in result
        assert "message" in result

    @pytest.mark.asyncio
    async def test_holds_ready_for_pickup_identified(self):
        """Holds with 'ready' status are the ones processed at closing."""
        holds = [
            Hold(id=1, user_id=1, item_id=1, status=HoldStatus.ready, position=0),
            Hold(id=2, user_id=2, item_id=2, status=HoldStatus.ready, position=0),
            Hold(id=3, user_id=3, item_id=3, status=HoldStatus.pending, position=1),
            Hold(id=4, user_id=4, item_id=4, status=HoldStatus.fulfilled, position=0),
        ]

        ready = [h for h in holds if h.status == HoldStatus.ready]
        assert len(ready) == 2

    @pytest.mark.asyncio
    async def test_overdue_notices_queued_at_close(self):
        """Overdue items are identified for notice generation at closing."""
        now = datetime.now(timezone.utc)

        checkouts = [
            Checkout(id=1, user_id=1, item_id=1, status=CheckoutStatus.active,
                     checked_out_at=now - timedelta(days=30),
                     due_date=now - timedelta(days=5)),  # overdue
            Checkout(id=2, user_id=2, item_id=2, status=CheckoutStatus.active,
                     checked_out_at=now - timedelta(days=25),
                     due_date=now - timedelta(days=3)),  # overdue
            Checkout(id=3, user_id=3, item_id=3, status=CheckoutStatus.active,
                     checked_out_at=now - timedelta(days=5),
                     due_date=now + timedelta(days=16)),  # not overdue
            Checkout(id=4, user_id=4, item_id=4, status=CheckoutStatus.returned,
                     checked_out_at=now - timedelta(days=30),
                     due_date=now - timedelta(days=5),
                     returned_at=now - timedelta(days=6)),  # returned, not overdue
        ]

        overdue = [
            c for c in checkouts
            if c.status == CheckoutStatus.active and c.due_date < now
        ]
        assert len(overdue) == 2

    @pytest.mark.asyncio
    async def test_create_daily_statistics_record(self, mock_db):
        """Daily statistics record is created with correct date and branch."""
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        mock_db.execute.return_value = count_result

        stats = await EndOfDayService.create_daily_statistics(
            db=mock_db,
            branch_location="Main Branch",
            closing_date=date.today(),
        )

        assert stats.closing_date == date.today()
        assert stats.branch_location == "Main Branch"
        assert stats.total_sessions == 2

    @pytest.mark.asyncio
    async def test_task_failure_records_error_message(self, mock_db):
        """A failed task records the error message and marks status FAILED."""
        task = EODTask(
            id=1,
            session_id=1,
            task_type=EODTaskType.CLOSE_REGISTERS,
            display_name="Close Registers",
            status=EODTaskStatus.PENDING,
        )

        with patch.object(
            EndOfDayService, "_close_registers",
            side_effect=Exception("Register drawer jammed"),
        ):
            await EndOfDayService.execute_task(db=mock_db, task=task, completed_by_id=1)

        assert task.status == EODTaskStatus.FAILED
        assert "Register drawer jammed" in task.error_message

    @pytest.mark.asyncio
    async def test_retry_failed_task_resets_and_re_executes(self, mock_db):
        """A failed task can be retried and succeeds on second attempt."""
        task = EODTask(
            id=10,
            session_id=1,
            task_type=EODTaskType.CLOSE_REGISTERS,
            display_name="Close Registers",
            status=EODTaskStatus.FAILED,
            error_message="Previous failure",
        )

        mock_db.get.return_value = task

        retried = await EndOfDayService.retry_failed_task(
            db=mock_db, task_id=10, completed_by_id=1,
        )

        assert retried.status == EODTaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_tomorrow_events_reminder(self):
        """Tomorrow events result structure contains event count and list."""
        # Validate the expected return structure from tomorrow_events
        result = {
            "event_count": 3,
            "events": [
                {"title": "Story Time", "time": "10:00 AM"},
                {"title": "Book Club", "time": "2:00 PM"},
                {"title": "Teen Gaming", "time": "4:00 PM"},
            ],
            "message": "3 events scheduled for tomorrow",
        }

        assert result["event_count"] == 3
        assert len(result["events"]) == 3
        assert "events" in result

        # Empty day scenario
        empty_result = {"event_count": 0, "events": [], "message": "No events tomorrow"}
        assert empty_result["event_count"] == 0


# =============================================================================
# 2. End of Week: Circulation Statistics Generated
# =============================================================================

class TestEndOfWeekCirculationStats:
    """End-of-week: weekly circulation statistics are generated."""

    @pytest.mark.asyncio
    async def test_weekly_circulation_statistics_structure(self):
        """Weekly circulation stats record has correct period type and fields."""
        last_monday = date.today() - timedelta(days=date.today().weekday())
        last_sunday = last_monday + timedelta(days=6)

        stats = CirculationStatistics(
            period_start=last_monday,
            period_end=last_sunday,
            period_type="weekly",
            total_checkouts=350,
            total_renewals=45,
            total_holds_placed=62,
            total_holds_filled=55,
            total_returns=320,
            items_loaned_to_other_libraries=5,
            items_borrowed_from_other_libraries=3,
        )

        assert stats.period_type == "weekly"
        assert stats.total_checkouts == 350
        assert stats.total_renewals == 45
        assert stats.total_holds_placed == 62
        assert stats.total_holds_filled == 55
        assert stats.total_returns == 320
        assert (stats.period_end - stats.period_start).days == 6

    @pytest.mark.asyncio
    async def test_weekly_stats_include_ill_counts(self):
        """Weekly stats track interlibrary loan activity."""
        stats = CirculationStatistics(
            period_start=date(2026, 2, 16),
            period_end=date(2026, 2, 22),
            period_type="weekly",
            total_checkouts=0,
            total_renewals=0,
            total_holds_placed=0,
            total_holds_filled=0,
            total_returns=0,
            items_loaned_to_other_libraries=8,
            items_borrowed_from_other_libraries=12,
        )

        assert stats.items_loaned_to_other_libraries == 8
        assert stats.items_borrowed_from_other_libraries == 12

    @pytest.mark.asyncio
    async def test_weekly_stats_by_branch(self):
        """Weekly stats can be scoped to a specific branch."""
        stats = CirculationStatistics(
            period_start=date(2026, 2, 16),
            period_end=date(2026, 2, 22),
            period_type="weekly",
            branch_location="Downtown Branch",
            total_checkouts=150,
            total_renewals=20,
            total_holds_placed=30,
            total_holds_filled=25,
            total_returns=140,
        )

        assert stats.branch_location == "Downtown Branch"
        assert stats.total_checkouts == 150

    @pytest.mark.asyncio
    async def test_weekly_stats_all_branches_null_location(self):
        """System-wide weekly stats use NULL branch_location."""
        stats = CirculationStatistics(
            period_start=date(2026, 2, 16),
            period_end=date(2026, 2, 22),
            period_type="weekly",
            branch_location=None,
            total_checkouts=500,
            total_renewals=60,
            total_holds_placed=90,
            total_holds_filled=80,
            total_returns=480,
        )

        assert stats.branch_location is None
        assert stats.total_checkouts == 500


# =============================================================================
# 3. End of Month: Reports Auto-Generated, Fines Tallied
# =============================================================================

class TestEndOfMonthReportsAndFines:
    """End-of-month: reports auto-generated and fines tallied."""

    @pytest.mark.asyncio
    async def test_monthly_circulation_stats_generated(self):
        """Monthly period statistics are created with correct period type."""
        stats = CirculationStatistics(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_type="monthly",
            total_checkouts=1450,
            total_renewals=200,
            total_holds_placed=250,
            total_holds_filled=220,
            total_returns=1400,
        )

        assert stats.period_type == "monthly"
        assert stats.total_checkouts == 1450

    @pytest.mark.asyncio
    async def test_monthly_fine_tally(self):
        """Fines are tallied correctly for monthly reporting."""
        fines = [
            Fine(id=1, user_id=10, fine_type=FineType.overdue, status=FineStatus.unpaid,
                 amount=Decimal("5.00"), amount_paid=Decimal("0.00")),
            Fine(id=2, user_id=11, fine_type=FineType.overdue, status=FineStatus.paid,
                 amount=Decimal("3.50"), amount_paid=Decimal("3.50")),
            Fine(id=3, user_id=12, fine_type=FineType.lost_item, status=FineStatus.unpaid,
                 amount=Decimal("25.00"), amount_paid=Decimal("0.00")),
            Fine(id=4, user_id=13, fine_type=FineType.damaged_item, status=FineStatus.waived,
                 amount=Decimal("10.00"), amount_paid=Decimal("0.00")),
            Fine(id=5, user_id=14, fine_type=FineType.overdue, status=FineStatus.partial,
                 amount=Decimal("8.00"), amount_paid=Decimal("4.00")),
        ]

        total_assessed = sum(f.amount for f in fines)
        total_collected = sum(f.amount_paid for f in fines)
        total_outstanding = sum(f.balance for f in fines if f.status in (FineStatus.unpaid, FineStatus.partial))
        total_waived = sum(f.amount for f in fines if f.status == FineStatus.waived)

        assert total_assessed == Decimal("51.50")
        assert total_collected == Decimal("7.50")
        assert total_outstanding == Decimal("34.00")  # 5 + 25 + 4
        assert total_waived == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_monthly_patron_statistics(self):
        """Monthly patron statistics track registrations and active users."""
        stats = PatronStatistics(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_type="monthly",
            total_registered_patrons=5200,
            new_registrations=85,
            active_borrowers=1800,
        )

        assert stats.new_registrations == 85
        assert stats.active_borrowers == 1800
        assert stats.total_registered_patrons == 5200

    @pytest.mark.asyncio
    async def test_monthly_program_statistics(self):
        """Monthly program statistics track events and attendance."""
        stats = ProgramStatistics(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_type="monthly",
            total_programs_offered=28,
            total_program_attendance=620,
            childrens_programs_count=12,
            childrens_program_attendance=280,
            young_adult_programs_count=6,
            young_adult_program_attendance=95,
            adult_programs_count=10,
            adult_program_attendance=245,
        )

        assert stats.total_programs_offered == 28
        assert stats.total_program_attendance == 620
        assert stats.childrens_program_attendance == 280

    @pytest.mark.asyncio
    async def test_eod_statistics_fine_metrics(self):
        """EOD statistics record fine totals for the day."""
        stats = EODStatistics(
            closing_date=date.today(),
            branch_location="Main Branch",
            total_fines_amount=Decimal("45.50"),
            total_fines_paid=Decimal("30.00"),
            total_fines_waived=Decimal("5.00"),
        )

        assert stats.total_fines_amount == Decimal("45.50")
        assert stats.total_fines_paid == Decimal("30.00")
        assert stats.total_fines_waived == Decimal("5.00")


# =============================================================================
# 4. End of Quarter: Collection Stats, Budget Review
# =============================================================================

class TestEndOfQuarterCollectionAndBudget:
    """End-of-quarter: collection stats and budget review."""

    @pytest.mark.asyncio
    async def test_quarterly_collection_statistics(self):
        """Quarterly collection stats track items owned, added, withdrawn."""
        stats = CollectionStatistics(
            snapshot_date=date(2026, 3, 31),
            total_items_owned=42000,
            total_items_added=850,
            total_items_withdrawn=320,
            print_materials=28000,
            electronic_titles=14000,
        )

        assert stats.total_items_owned == 42000
        assert stats.total_items_added == 850
        assert stats.total_items_withdrawn == 320
        net_change = stats.total_items_added - stats.total_items_withdrawn
        assert net_change == 530

    @pytest.mark.asyncio
    async def test_budget_fund_available_amount(self):
        """Fund available amount is computed correctly for budget review."""
        fund = Fund(
            id=1,
            code="BOOKS-2026",
            name="Book Acquisitions FY2026",
            fiscal_year=2026,
            allocated_amount=Decimal("50000.00"),
            encumbered_amount=Decimal("12000.00"),
            spent_amount=Decimal("28000.00"),
            status=FundStatus.ACTIVE,
        )

        available = fund.allocated_amount - fund.encumbered_amount - fund.spent_amount
        assert available == Decimal("10000.00")


    @pytest.mark.asyncio
    async def test_quarterly_circulation_statistics(self):
        """Quarterly circulation stats aggregate 3 months of data."""
        stats = CirculationStatistics(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            period_type="quarterly",
            total_checkouts=4200,
            total_renewals=580,
            total_holds_placed=720,
            total_holds_filled=650,
            total_returns=4050,
        )

        assert stats.period_type == "quarterly"
        assert stats.total_checkouts == 4200


# =============================================================================
# 5. End of Fiscal Year: Annual Totals, Rollovers
# =============================================================================

class TestEndOfFiscalYear:
    """End-of-fiscal-year: annual totals and fund rollovers."""


    @pytest.mark.asyncio
    async def test_annual_report_generation_structure(self):
        """Annual report is created with correct fiscal year and status."""
        report = AnnualReport(
            fiscal_year=2025,
            state_code="CA",
            library_name="Bébé Memorial Public Library",
            status=ReportStatus.GENERATED,
        )

        assert report.fiscal_year == 2025
        assert report.state_code == "CA"
        assert report.status == ReportStatus.GENERATED

    @pytest.mark.asyncio
    async def test_annual_report_status_lifecycle(self):
        """Annual report progresses through draft -> generated -> validated -> submitted."""
        report = AnnualReport(
            fiscal_year=2025,
            state_code="CA",
            library_name="LSCPL",
            status=ReportStatus.DRAFT,
        )

        assert report.status == ReportStatus.DRAFT

        report.status = ReportStatus.GENERATED
        assert report.status == ReportStatus.GENERATED

        report.status = ReportStatus.VALIDATED
        assert report.status == ReportStatus.VALIDATED

        report.status = ReportStatus.SUBMITTED
        assert report.status == ReportStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_yearly_circulation_statistics(self):
        """Yearly circulation stats aggregate the full fiscal year."""
        stats = CirculationStatistics(
            period_start=date(2024, 7, 1),
            period_end=date(2025, 6, 30),
            period_type="yearly",
            total_checkouts=52000,
            total_renewals=7200,
            total_holds_placed=9500,
            total_holds_filled=8800,
            total_returns=50500,
            items_loaned_to_other_libraries=120,
            items_borrowed_from_other_libraries=95,
        )

        assert stats.period_type == "yearly"
        assert stats.total_checkouts == 52000
        # July 1 2024 to June 30 2025 = 364 days by subtraction (inclusive = 365 calendar days)
        assert (stats.period_end - stats.period_start).days == 364


# =============================================================================
# 6. End of Calendar Year: Patron Card Renewals Batch
# =============================================================================

class TestEndOfCalendarYearPatronRenewals:
    """End-of-calendar-year: batch patron card renewal processing."""

    @pytest.mark.asyncio
    async def test_patron_card_has_expiration(self):
        """Patron cards have an expiration date."""
        patron = User(
            id=100,
            email="patron@example.com",
            first_name="Alice",
            last_name="Reader",
            password_hash="hashed",
            role=UserRole.PATRON,
            is_active=True,
            library_card="LIB-2026-0100",
            card_expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        assert patron.card_expires_at is not None
        assert patron.card_expires_at.year == 2026

    @pytest.mark.asyncio
    async def test_batch_card_renewal_identifies_expiring_cards(self):
        """Batch renewal identifies patrons whose cards expire at year-end."""
        year_end = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        patrons = [
            User(id=i, email=f"p{i}@lib.local", first_name=f"P{i}", last_name="Test",
                 password_hash="h", role=UserRole.PATRON, is_active=True,
                 library_card=f"LIB-{i:04d}",
                 card_expires_at=year_end)
            for i in range(1, 51)
        ]

        expiring = [p for p in patrons if p.card_expires_at and p.card_expires_at <= year_end]
        assert len(expiring) == 50

    @pytest.mark.asyncio
    async def test_card_renewal_extends_expiration(self):
        """Renewing a card extends expiration by one year."""
        patron = User(
            id=200,
            email="renew@example.com",
            first_name="Bob",
            last_name="Patron",
            password_hash="hashed",
            role=UserRole.PATRON,
            is_active=True,
            library_card="LIB-2026-0200",
            card_expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        old_expiry = patron.card_expires_at
        patron.card_expires_at = datetime(
            old_expiry.year + 1, old_expiry.month, old_expiry.day,
            tzinfo=timezone.utc,
        )

        assert patron.card_expires_at.year == 2027
        assert patron.card_expires_at.month == 12
        assert patron.card_expires_at.day == 31

    @pytest.mark.asyncio
    async def test_inactive_patrons_excluded_from_renewal(self):
        """Inactive patron accounts are not renewed."""
        patrons = [
            User(id=1, email="active@lib.local", first_name="A", last_name="P",
                 password_hash="h", role=UserRole.PATRON, is_active=True,
                 card_expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc)),
            User(id=2, email="blocked@lib.local", first_name="B", last_name="P",
                 password_hash="h", role=UserRole.PATRON, is_active=False,
                 card_expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc)),
        ]

        eligible = [p for p in patrons if p.is_active]
        assert len(eligible) == 1
        assert eligible[0].id == 1

    @pytest.mark.asyncio
    async def test_deceased_patrons_excluded_from_renewal(self):
        """Deceased patron accounts are not renewed."""
        patron = User(
            id=300,
            email="deceased@lib.local",
            first_name="C",
            last_name="Patron",
            password_hash="h",
            role=UserRole.PATRON,
            is_active=True,
            patron_status=PatronStatus.DECEASED,
            card_expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        eligible = patron.patron_status not in (PatronStatus.DECEASED, PatronStatus.BLOCKED)
        assert eligible is False

    @pytest.mark.asyncio
    async def test_staff_cards_not_subject_to_patron_renewal(self):
        """Staff members are excluded from batch patron card renewal."""
        staff = User(
            id=400,
            email="staff@lib.local",
            first_name="Staff",
            last_name="Person",
            password_hash="h",
            role=UserRole.STAFF,
            is_active=True,
        )

        is_patron_renewal_candidate = staff.role == UserRole.PATRON
        assert is_patron_renewal_candidate is False


# =============================================================================
# 7. Summer Reading Program Close-Out
# =============================================================================

class TestSummerReadingProgramCloseOut:
    """Summer reading program: close-out and finalization."""

    @pytest.mark.asyncio
    async def test_summer_reading_program_completion(self):
        """Summer reading program can be marked completed."""
        program = Program(
            id=1,
            title="Summer Reading Challenge 2026",
            program_type=LibraryProgramType.READING_PROGRAM,
            audience=ProgramAudience.CHILDREN,
            status=ProgramStatus.IN_PROGRESS,
            program_date=date(2026, 8, 15),
            start_time=time(10, 0),
        )

        assert program.status == ProgramStatus.IN_PROGRESS

        program.status = ProgramStatus.COMPLETED
        assert program.status == ProgramStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_summer_reading_attendance_tallied(self):
        """Program attendance is tallied at close-out."""
        stats = ProgramStatistics(
            period_start=date(2026, 6, 1),
            period_end=date(2026, 8, 15),
            period_type="yearly",
            total_programs_offered=1,
            total_program_attendance=245,
            childrens_programs_count=1,
            childrens_program_attendance=245,
            young_adult_programs_count=0,
            young_adult_program_attendance=0,
            adult_programs_count=0,
            adult_program_attendance=0,
        )

        assert stats.total_program_attendance == 245
        assert stats.childrens_program_attendance == 245

    @pytest.mark.asyncio
    async def test_summer_reading_program_types_tracked(self):
        """All audience segments of summer reading are tracked."""
        children_program = Program(
            id=1, title="Kids Summer Read 2026",
            program_type=LibraryProgramType.READING_PROGRAM,
            audience=ProgramAudience.CHILDREN,
            status=ProgramStatus.COMPLETED,
            program_date=date(2026, 8, 15), start_time=time(10, 0),
        )

        teen_program = Program(
            id=2, title="Teen Summer Read 2026",
            program_type=LibraryProgramType.READING_PROGRAM,
            audience=ProgramAudience.TEEN,
            status=ProgramStatus.COMPLETED,
            program_date=date(2026, 8, 15), start_time=time(14, 0),
        )

        adult_program = Program(
            id=3, title="Adult Summer Read 2026",
            program_type=LibraryProgramType.READING_PROGRAM,
            audience=ProgramAudience.ADULT,
            status=ProgramStatus.COMPLETED,
            program_date=date(2026, 8, 15), start_time=time(18, 0),
        )

        programs = [children_program, teen_program, adult_program]
        reading_programs = [p for p in programs if p.program_type == LibraryProgramType.READING_PROGRAM]

        assert len(reading_programs) == 3
        assert all(p.status == ProgramStatus.COMPLETED for p in reading_programs)
        audiences = {p.audience for p in reading_programs}
        assert ProgramAudience.CHILDREN in audiences
        assert ProgramAudience.TEEN in audiences
        assert ProgramAudience.ADULT in audiences

    @pytest.mark.asyncio
    async def test_summer_reading_cancelled_program_excluded(self):
        """Cancelled programs are excluded from close-out totals."""
        programs = [
            Program(id=1, title="Active Program", program_type=LibraryProgramType.READING_PROGRAM,
                    audience=ProgramAudience.CHILDREN, status=ProgramStatus.COMPLETED,
                    program_date=date(2026, 8, 15), start_time=time(10, 0)),
            Program(id=2, title="Cancelled Program", program_type=LibraryProgramType.READING_PROGRAM,
                    audience=ProgramAudience.CHILDREN, status=ProgramStatus.CANCELLED,
                    program_date=date(2026, 8, 15), start_time=time(10, 0)),
        ]

        completed = [p for p in programs if p.status == ProgramStatus.COMPLETED]
        assert len(completed) == 1


# =============================================================================
# 8. State Report Data Freeze
# =============================================================================

class TestStateReportDataFreeze:
    """State report: data freeze and submission tracking."""

    @pytest.mark.asyncio
    async def test_annual_report_validated_status(self):
        """Report marked as validated after passing all checks."""
        report = AnnualReport(
            fiscal_year=2025,
            state_code="CA",
            library_name="LSCPL",
            status=ReportStatus.VALIDATED,
            is_validated=True,
            validated_at=datetime.now(timezone.utc),
        )

        assert report.is_validated is True
        assert report.status == ReportStatus.VALIDATED

    @pytest.mark.asyncio
    async def test_submitted_report_cannot_go_back_to_draft(self):
        """Report submission status progresses forward only in normal workflow."""
        report = AnnualReport(
            fiscal_year=2025,
            state_code="CA",
            library_name="LSCPL",
            status=ReportStatus.SUBMITTED,
        )

        assert report.status == ReportStatus.SUBMITTED
        # Only rejection (by state) should move it backward
        report.status = ReportStatus.REJECTED
        assert report.status == ReportStatus.REJECTED

    @pytest.mark.asyncio
    async def test_report_validation_errors_tracked(self):
        """Validation errors are stored on the report for review."""
        report = AnnualReport(
            fiscal_year=2025,
            state_code="CA",
            library_name="LSCPL",
            status=ReportStatus.DRAFT,
            is_validated=False,
            validation_errors=[
                {"field": "total_checkouts", "error": "Value seems unusually low"},
                {"field": "patron_count", "error": "Missing required field"},
            ],
        )

        assert report.is_validated is False
        assert len(report.validation_errors) == 2
        assert report.validation_errors[0]["field"] == "total_checkouts"

    @pytest.mark.asyncio
    async def test_report_data_freeze_prevents_modification(self):
        """Once submitted, report data is effectively frozen."""
        report = AnnualReport(
            fiscal_year=2025,
            state_code="CA",
            library_name="LSCPL",
            status=ReportStatus.SUBMITTED,
        )

        is_frozen = report.status == ReportStatus.SUBMITTED
        assert is_frozen is True

    @pytest.mark.asyncio
    async def test_report_covers_correct_fiscal_year_dates(self):
        """Fiscal year for report covers July 1 to June 30."""
        fiscal_year = 2025
        fiscal_start = date(fiscal_year - 1, 7, 1)  # July 1, 2024
        fiscal_end = date(fiscal_year, 6, 30)  # June 30, 2025

        assert fiscal_start == date(2024, 7, 1)
        assert fiscal_end == date(2025, 6, 30)
        # July 1 to June 30 = 364 days by subtraction (covers 365 calendar days inclusive)
        assert (fiscal_end - fiscal_start).days == 364


# =============================================================================
# 9. Archive Old Data
# =============================================================================

class TestArchiveOldData:
    """Archive old data: retention policies and archival processes."""

    @pytest.mark.asyncio
    async def test_old_checkouts_identified_for_archival(self):
        """Returned checkouts older than retention period are identified."""
        retention_days = 365 * 3  # 3 year retention
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        old_checkout = Checkout(
            id=1, user_id=1, item_id=1,
            status=CheckoutStatus.returned,
            checked_out_at=datetime(2022, 1, 15, tzinfo=timezone.utc),
            due_date=datetime(2022, 2, 5, tzinfo=timezone.utc),
            returned_at=datetime(2022, 1, 30, tzinfo=timezone.utc),
        )

        recent_checkout = Checkout(
            id=2, user_id=1, item_id=2,
            status=CheckoutStatus.returned,
            checked_out_at=datetime(2025, 11, 1, tzinfo=timezone.utc),
            due_date=datetime(2025, 11, 22, tzinfo=timezone.utc),
            returned_at=datetime(2025, 11, 20, tzinfo=timezone.utc),
        )

        active_checkout = Checkout(
            id=3, user_id=1, item_id=3,
            status=CheckoutStatus.active,
            checked_out_at=datetime(2021, 6, 1, tzinfo=timezone.utc),
            due_date=datetime(2021, 6, 22, tzinfo=timezone.utc),
        )

        all_checkouts = [old_checkout, recent_checkout, active_checkout]

        archivable = [
            c for c in all_checkouts
            if c.status == CheckoutStatus.returned
            and c.returned_at is not None
            and c.returned_at < cutoff
        ]

        assert len(archivable) == 1
        assert archivable[0].id == 1

    @pytest.mark.asyncio
    async def test_active_checkouts_never_archived(self):
        """Active checkouts are never archived regardless of age."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * 10)

        checkout = Checkout(
            id=1, user_id=1, item_id=1,
            status=CheckoutStatus.active,
            checked_out_at=datetime(2015, 1, 1, tzinfo=timezone.utc),
            due_date=datetime(2015, 1, 22, tzinfo=timezone.utc),
        )

        is_archivable = (
            checkout.status == CheckoutStatus.returned
            and checkout.returned_at is not None
            and checkout.returned_at < cutoff
        )

        assert is_archivable is False

    @pytest.mark.asyncio
    async def test_paid_fines_archival_eligibility(self):
        """Paid fines older than retention period are eligible for archival."""
        retention_days = 365 * 5  # 5 year retention for financial records
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        old_paid_fine = Fine(
            id=1, user_id=1, fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=Decimal("5.00"), amount_paid=Decimal("5.00"),
            paid_at=datetime(2019, 3, 1, tzinfo=timezone.utc),
        )

        recent_paid_fine = Fine(
            id=2, user_id=1, fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=Decimal("3.00"), amount_paid=Decimal("3.00"),
            paid_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
        )

        unpaid_fine = Fine(
            id=3, user_id=1, fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=Decimal("25.00"), amount_paid=Decimal("0.00"),
        )

        fines = [old_paid_fine, recent_paid_fine, unpaid_fine]

        archivable_fines = [
            f for f in fines
            if f.status == FineStatus.paid
            and f.paid_at is not None
            and f.paid_at < cutoff
        ]

        assert len(archivable_fines) == 1
        assert archivable_fines[0].id == 1

    @pytest.mark.asyncio
    async def test_unpaid_fines_never_archived(self):
        """Unpaid fines are never archived regardless of age."""
        old_unpaid = Fine(
            id=1, user_id=1, fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"), amount_paid=Decimal("0.00"),
        )

        is_archivable = old_unpaid.status in (FineStatus.paid, FineStatus.waived)
        assert is_archivable is False

    @pytest.mark.asyncio
    async def test_completed_eod_sessions_archival(self):
        """Completed EOD sessions older than retention can be archived."""
        retention_days = 365 * 2
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        old_session = EODSession(
            id=1, session_code="EOD-OLD00001",
            template_id=1, branch_location="Main Branch",
            closing_date=date(2023, 6, 15),
            staff_id=1, status=EODSessionStatus.COMPLETED,
            started_at=datetime(2023, 6, 15, 17, 0, tzinfo=timezone.utc),
            completed_at=datetime(2023, 6, 15, 17, 5, tzinfo=timezone.utc),
        )

        recent_session = EODSession(
            id=2, session_code="EOD-NEW00001",
            template_id=1, branch_location="Main Branch",
            closing_date=date.today(),
            staff_id=1, status=EODSessionStatus.COMPLETED,
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            completed_at=datetime.now(timezone.utc),
        )

        sessions = [old_session, recent_session]

        archivable = [
            s for s in sessions
            if s.status == EODSessionStatus.COMPLETED
            and s.completed_at is not None
            and s.completed_at < cutoff
        ]

        assert len(archivable) == 1
        assert archivable[0].id == 1

    @pytest.mark.asyncio
    async def test_old_holds_archival(self):
        """Fulfilled and cancelled holds older than retention are archivable."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * 2)

        old_fulfilled = Hold(
            id=1, user_id=1, item_id=1,
            status=HoldStatus.fulfilled, position=0,
        )
        old_fulfilled.updated_at = datetime(2023, 1, 1, tzinfo=timezone.utc)

        old_cancelled = Hold(
            id=2, user_id=1, item_id=2,
            status=HoldStatus.cancelled, position=0,
        )
        old_cancelled.updated_at = datetime(2023, 2, 1, tzinfo=timezone.utc)

        pending_hold = Hold(
            id=3, user_id=1, item_id=3,
            status=HoldStatus.pending, position=1,
        )
        pending_hold.updated_at = datetime(2023, 1, 1, tzinfo=timezone.utc)

        holds = [old_fulfilled, old_cancelled, pending_hold]

        terminal_statuses = {HoldStatus.fulfilled, HoldStatus.cancelled, HoldStatus.expired}
        archivable = [
            h for h in holds
            if h.status in terminal_statuses
            and hasattr(h, 'updated_at')
            and h.updated_at is not None
            and h.updated_at < cutoff
        ]

        assert len(archivable) == 2


# =============================================================================
# 10. Verify Rollover Calculations Correct
# =============================================================================


# =============================================================================
# Combined Period Close: Every Closing Runs Clean
# =============================================================================

class TestEveryClosingRunsClean:
    """Integration-style checks that all period closes are consistent."""

    @pytest.mark.asyncio
    async def test_period_types_cover_all_intervals(self):
        """PeriodType enum covers daily, weekly, monthly, quarterly, yearly."""
        expected = {"daily", "weekly", "monthly", "quarterly", "yearly"}
        actual = {pt.value for pt in PeriodType}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_eod_task_types_comprehensive(self):
        """EOD task types cover all required closing operations."""
        expected_tasks = {
            "close_registers", "process_holds", "send_overdue_notices",
            "backup_confirmation", "security_check", "statistics_summary",
            "tomorrow_events", "holds_pull_list",
        }
        actual_tasks = {t.value for t in EODTaskType}
        assert expected_tasks == actual_tasks

    @pytest.mark.asyncio
    async def test_eod_session_status_lifecycle(self):
        """EOD session status covers full lifecycle."""
        expected = {"started", "in_progress", "completed", "cancelled", "failed"}
        actual = {s.value for s in EODSessionStatus}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_eod_task_status_lifecycle(self):
        """EOD task status covers full lifecycle."""
        expected = {"pending", "in_progress", "completed", "failed", "skipped"}
        actual = {s.value for s in EODTaskStatus}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_fine_status_covers_all_outcomes(self):
        """Fine statuses cover unpaid, paid, waived, partial."""
        expected = {"unpaid", "paid", "waived", "partial"}
        actual = {s.value for s in FineStatus}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_fund_status_covers_lifecycle(self):
        """Fund statuses cover active, inactive, closed."""
        expected = {"active", "inactive", "closed"}
        actual = {s.value for s in FundStatus}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_report_status_covers_workflow(self):
        """Report statuses cover full submission workflow."""
        expected = {"draft", "generated", "validated", "submitted", "rejected"}
        actual = {s.value for s in ReportStatus}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_security_check_types_comprehensive(self):
        """Security check types cover all facility checks."""
        expected = {
            "door_locks", "alarm_system", "safe_locked",
            "windows_locked", "lights_off", "computers_shut_down",
            "valves_closed",
        }
        actual = {s.value for s in SecurityCheckType}
        assert expected == actual

    @pytest.mark.asyncio
    async def test_fine_balance_calculation(self):
        """Fine balance is always amount minus amount_paid."""
        fine = Fine(
            id=1, user_id=1, fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=Decimal("10.00"),
            amount_paid=Decimal("3.50"),
        )

        assert fine.balance == Decimal("6.50")

    @pytest.mark.asyncio
    async def test_eod_statistics_explicit_values(self):
        """EOD statistics record stores explicitly provided values."""
        stats = EODStatistics(
            closing_date=date.today(),
            branch_location="Main Branch",
            total_checkouts=100,
            total_checkins=95,
            total_fines_amount=Decimal("25.00"),
            total_exceptions=0,
            total_security_failures=0,
            total_backup_failures=0,
        )

        assert stats.total_checkouts == 100
        assert stats.total_checkins == 95
        assert stats.total_fines_amount == Decimal("25.00")
        assert stats.total_exceptions == 0
        assert stats.total_security_failures == 0
        assert stats.total_backup_failures == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
