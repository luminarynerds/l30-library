# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for shelf reading features.

Tests cover:
- Shelf reading session lifecycle (create, pause, resume, complete, cancel)
- Item scanning with call number order detection
- Out-of-order item detection
- Wrong-shelf item detection
- Shelf reading progress tracking
- Shelving accuracy reports
- Scheduled shelf reads
- Gamification (points, leaderboard)
- Branch-level tracking
- Historical accuracy trends
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.catalog import CatalogItem, ItemStatus
from app.models.inventory import ItemCopy, ItemCondition
from app.models.multi_branch import Branch, BranchType, BranchStatus, LibrarySystem
from app.models.shelf_reading import (
    ScanResult,
    ScheduleFrequency,
    ShelfReadingSchedule,
    ShelfReadingScan,
    ShelfReadingSession,
    ShelfReadingStatus,
)
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.services.shelf_reading_service import (
    ShelfReadingService,
    POINTS_IN_ORDER,
    POINTS_OUT_OF_ORDER,
    POINTS_WRONG_SHELF,
    POINTS_SESSION_COMPLETE_BONUS,
    POINTS_PERFECT_ACCURACY_BONUS,
)
from app.services.call_number_service import CallNumberService


# ============ Fixtures ============


@pytest.fixture
async def library_system(test_db):
    """Create a library system for testing."""
    system = LibrarySystem(
        code="LSC",
        name="Bébé Memorial Library System",
    )
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)
    return system


@pytest.fixture
async def test_branch(test_db, library_system):
    """Create a test branch."""
    branch = Branch(
        library_system_id=library_system.id,
        code="MAIN",
        name="Main Branch",
        branch_type=BranchType.MAIN,
        status=BranchStatus.ACTIVE,
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


@pytest.fixture
async def second_branch(test_db, library_system):
    """Create a second branch for multi-branch tests."""
    branch = Branch(
        library_system_id=library_system.id,
        code="NORTH",
        name="North Branch",
        branch_type=BranchType.BRANCH,
        status=BranchStatus.ACTIVE,
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


@pytest.fixture
async def shelf_staff(test_db):
    """Create a staff user for shelf reading."""
    user = User(
        email="shelfreader@example.com",
        password_hash=hash_password("ShelfRead123!"),
        first_name="Shelf",
        last_name="Reader",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def second_staff(test_db):
    """Create a second staff user for leaderboard tests."""
    user = User(
        email="shelfreader2@example.com",
        password_hash=hash_password("ShelfRead456!"),
        first_name="Other",
        last_name="Reader",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def catalog_items(test_db):
    """Create catalog items with call numbers in a known order."""
    items_data = [
        {"title": "Applied Mathematics", "author": "Adams", "call_number": "QA100.A33", "location": "Adult Nonfiction A-1"},
        {"title": "Basic Statistics", "author": "Brown", "call_number": "QA276.B76", "location": "Adult Nonfiction A-1"},
        {"title": "Calculus Made Easy", "author": "Clark", "call_number": "QA303.C55", "location": "Adult Nonfiction A-1"},
        {"title": "Data Structures", "author": "Davis", "call_number": "QA76.73.D38", "location": "Adult Nonfiction A-1"},
        {"title": "English Literature", "author": "Evans", "call_number": "PR6001.E83", "location": "Adult Fiction B-2"},
        {"title": "Fiction Writing", "author": "Fisher", "call_number": "PS3556.F58", "location": "Adult Fiction B-2"},
    ]

    items = []
    for data in items_data:
        item = CatalogItem(
            title=data["title"],
            author=data["author"],
            call_number=data["call_number"],
            location=data["location"],
            status=ItemStatus.available,
        )
        test_db.add(item)
        items.append(item)

    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    return items


@pytest.fixture
async def item_copies(test_db, catalog_items):
    """Create item copies for the catalog items."""
    copies = []
    for i, cat_item in enumerate(catalog_items):
        copy = ItemCopy(
            catalog_item_id=cat_item.id,
            barcode=f"SHELF-{i+1:03d}",
            copy_number=1,
            condition=ItemCondition.GOOD,
            location=cat_item.location,
        )
        test_db.add(copy)
        copies.append(copy)

    await test_db.commit()
    for copy in copies:
        await test_db.refresh(copy)
    return copies


@pytest.fixture
async def shelf_session(test_db, test_branch, shelf_staff):
    """Create a shelf reading session."""
    session = await ShelfReadingService.create_session(
        db=test_db,
        name="Adult Nonfiction A-1 Check",
        branch_id=test_branch.id,
        location="Adult Nonfiction A-1",
        created_by_id=shelf_staff.id,
        description="Regular shelf read of nonfiction section A-1",
        call_number_start="QA",
        call_number_end="QZ",
    )
    await test_db.commit()
    await test_db.refresh(session)
    return session


# ============ Session Lifecycle Tests ============


class TestShelfReadingSessionLifecycle:
    """Tests for session creation, state transitions, and lifecycle."""

    async def test_create_session(self, test_db, test_branch, shelf_staff):
        """Test creating a new shelf reading session."""
        session = await ShelfReadingService.create_session(
            db=test_db,
            name="Test Session",
            branch_id=test_branch.id,
            location="Adult Fiction A-1",
            created_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert session.id is not None
        assert session.name == "Test Session"
        assert session.branch_id == test_branch.id
        assert session.location == "Adult Fiction A-1"
        assert session.status == ShelfReadingStatus.IN_PROGRESS
        assert session.total_items_scanned == 0
        assert session.items_in_order == 0
        assert session.items_out_of_order == 0
        assert session.items_wrong_shelf == 0
        assert session.accuracy_percentage == 0.0
        assert session.points_earned == 0

    async def test_create_session_with_range(
        self, test_db, test_branch, shelf_staff
    ):
        """Test creating a session with call number range."""
        session = await ShelfReadingService.create_session(
            db=test_db,
            name="QA Section",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
            call_number_start="QA1",
            call_number_end="QA999",
        )
        await test_db.commit()

        assert session.call_number_start == "QA1"
        assert session.call_number_end == "QA999"

    async def test_pause_session(self, test_db, shelf_session):
        """Test pausing an in-progress session."""
        session = await ShelfReadingService.pause_session(test_db, shelf_session)
        await test_db.commit()

        assert session.status == ShelfReadingStatus.PAUSED
        assert session.paused_at is not None

    async def test_resume_session(self, test_db, shelf_session):
        """Test resuming a paused session."""
        await ShelfReadingService.pause_session(test_db, shelf_session)
        await test_db.commit()

        session = await ShelfReadingService.resume_session(test_db, shelf_session)
        await test_db.commit()

        assert session.status == ShelfReadingStatus.IN_PROGRESS
        assert session.paused_at is None

    async def test_complete_session(self, test_db, shelf_session):
        """Test completing a shelf reading session."""
        session = await ShelfReadingService.complete_session(test_db, shelf_session)
        await test_db.commit()

        assert session.status == ShelfReadingStatus.COMPLETED
        assert session.completed_at is not None
        assert session.points_earned >= POINTS_SESSION_COMPLETE_BONUS

    async def test_cancel_session(self, test_db, shelf_session):
        """Test cancelling a shelf reading session."""
        session = await ShelfReadingService.cancel_session(test_db, shelf_session)
        await test_db.commit()

        assert session.status == ShelfReadingStatus.CANCELLED
        assert session.completed_at is not None

    async def test_get_session(self, test_db, shelf_session):
        """Test retrieving a session by ID."""
        found = await ShelfReadingService.get_session(test_db, shelf_session.id)
        assert found is not None
        assert found.id == shelf_session.id
        assert found.name == shelf_session.name

    async def test_get_nonexistent_session(self, test_db):
        """Test retrieving a non-existent session returns None."""
        found = await ShelfReadingService.get_session(test_db, 99999)
        assert found is None


# ============ Scanning Tests ============


class TestShelfReadingScanning:
    """Tests for item scanning, order detection, and misplacement detection."""

    async def test_scan_first_item_in_order(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """First scanned item is always in order."""
        scan = await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],  # QA100.A33
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert scan.result == ScanResult.IN_ORDER
        assert scan.scan_order == 1
        assert scan.previous_call_number is None
        assert shelf_session.total_items_scanned == 1
        assert shelf_session.items_in_order == 1

    async def test_scan_items_in_correct_order(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Scanning items in correct call number order."""
        # Scan first three items which are in correct order for the same location
        for i in range(3):
            _ = await ShelfReadingService.scan_item(
                db=test_db,
                session=shelf_session,
                item_copy=item_copies[i],
                scanned_by_id=shelf_staff.id,
            )
            await test_db.commit()

        assert shelf_session.total_items_scanned == 3
        assert shelf_session.items_in_order == 3
        assert shelf_session.items_out_of_order == 0
        assert shelf_session.accuracy_percentage == 100.0

    async def test_scan_item_out_of_order(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Detect when an item is scanned out of call number order."""
        # Scan item 1 (QA276.B76) then item 0 (QA100.A33) - out of order
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[1],  # QA276.B76
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        scan = await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],  # QA100.A33 - comes before B76
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert scan.result == ScanResult.OUT_OF_ORDER
        assert shelf_session.items_out_of_order == 1
        assert shelf_session.total_items_scanned == 2

    async def test_scan_item_wrong_shelf(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Detect when an item belongs on a different shelf."""
        # item_copies[4] has location "Adult Fiction B-2" but session is for "Adult Nonfiction A-1"
        scan = await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[4],  # PR6001.E83 - Adult Fiction B-2
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert scan.result == ScanResult.WRONG_SHELF
        assert scan.expected_location == "Adult Fiction B-2"
        assert shelf_session.items_wrong_shelf == 1

    async def test_scan_tracks_previous_call_number(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Verify that each scan records the previous item's call number."""
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],  # QA100.A33
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        scan2 = await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[1],  # QA276.B76
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert scan2.previous_call_number == "QA100.A33"

    async def test_accuracy_percentage_updates(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Verify accuracy percentage is correctly calculated."""
        # Scan 3 items: 2 in order, 1 out of order
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],
            scanned_by_id=shelf_staff.id,
        )
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[1],
            scanned_by_id=shelf_staff.id,
        )
        # Scan item from wrong shelf
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[4],  # Wrong shelf
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        # 2 in order out of 3 total = 66.67%
        assert shelf_session.total_items_scanned == 3
        assert shelf_session.items_in_order == 2
        assert abs(shelf_session.accuracy_percentage - 66.67) < 0.1


# ============ Progress Tracking Tests ============


class TestShelfReadingProgress:
    """Tests for shelf reading progress tracking."""

    async def test_initial_progress(self, test_db, shelf_session):
        """New session shows zero progress."""
        assert shelf_session.total_items_scanned == 0
        assert shelf_session.accuracy_percentage == 0.0
        assert shelf_session.points_earned == 0

    async def test_progress_after_scans(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Progress updates after each scan."""
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert shelf_session.total_items_scanned == 1
        assert shelf_session.items_in_order == 1
        assert shelf_session.accuracy_percentage == 100.0

    async def test_get_session_scans(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Retrieve all scans for a session in order."""
        for i in range(3):
            await ShelfReadingService.scan_item(
                db=test_db,
                session=shelf_session,
                item_copy=item_copies[i],
                scanned_by_id=shelf_staff.id,
            )
        await test_db.commit()

        scans = await ShelfReadingService.get_session_scans(
            test_db, shelf_session.id
        )
        assert len(scans) == 3
        assert scans[0].scan_order == 1
        assert scans[1].scan_order == 2
        assert scans[2].scan_order == 3


# ============ Gamification Tests ============


class TestShelfReadingGamification:
    """Tests for points, bonuses, and leaderboard."""

    async def test_points_for_in_order_scan(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """In-order scans award standard points."""
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert shelf_session.points_earned == POINTS_IN_ORDER

    async def test_points_for_out_of_order_scan(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Out-of-order scans award more points (finding problems is valuable)."""
        # Scan item 1 then item 0 (out of order)
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[1],
            scanned_by_id=shelf_staff.id,
        )
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[0],
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert shelf_session.points_earned == POINTS_IN_ORDER + POINTS_OUT_OF_ORDER

    async def test_points_for_wrong_shelf_scan(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Wrong-shelf scans award the most points."""
        await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=item_copies[4],  # Wrong shelf
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert shelf_session.points_earned == POINTS_WRONG_SHELF

    async def test_completion_bonus_points(
        self, test_db, shelf_session, shelf_staff
    ):
        """Completing a session awards bonus points."""
        initial_points = shelf_session.points_earned

        await ShelfReadingService.complete_session(test_db, shelf_session)
        await test_db.commit()

        assert shelf_session.points_earned >= initial_points + POINTS_SESSION_COMPLETE_BONUS

    async def test_perfect_accuracy_bonus(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Perfect accuracy (100%) awards extra bonus on completion."""
        # Scan items in correct order
        for i in range(3):
            await ShelfReadingService.scan_item(
                db=test_db,
                session=shelf_session,
                item_copy=item_copies[i],
                scanned_by_id=shelf_staff.id,
            )
        await test_db.commit()

        assert shelf_session.accuracy_percentage == 100.0

        await ShelfReadingService.complete_session(test_db, shelf_session)
        await test_db.commit()

        expected_points = (
            3 * POINTS_IN_ORDER
            + POINTS_SESSION_COMPLETE_BONUS
            + POINTS_PERFECT_ACCURACY_BONUS
        )
        assert shelf_session.points_earned == expected_points

    async def test_leaderboard(
        self, test_db, test_branch, shelf_staff, second_staff, item_copies
    ):
        """Leaderboard ranks users by total points."""
        # Staff 1 completes a session
        session1 = await ShelfReadingService.create_session(
            db=test_db,
            name="Session 1",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        await ShelfReadingService.scan_item(
            test_db, session1, item_copies[0], shelf_staff.id
        )
        await ShelfReadingService.scan_item(
            test_db, session1, item_copies[1], shelf_staff.id
        )
        await ShelfReadingService.complete_session(test_db, session1)
        await test_db.commit()

        # Staff 2 completes a session
        session2 = await ShelfReadingService.create_session(
            db=test_db,
            name="Session 2",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=second_staff.id,
        )
        await ShelfReadingService.scan_item(
            test_db, session2, item_copies[2], second_staff.id
        )
        await ShelfReadingService.complete_session(test_db, session2)
        await test_db.commit()

        leaderboard = await ShelfReadingService.get_leaderboard(test_db)

        assert len(leaderboard) == 2
        # Staff 1 should be ranked first (more points from more scans)
        assert leaderboard[0]["user_id"] == shelf_staff.id
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["user_id"] == second_staff.id
        assert leaderboard[1]["rank"] == 2


# ============ Report Tests ============


class TestShelfReadingReports:
    """Tests for accuracy reports and branch summaries."""

    async def test_accuracy_report(
        self, test_db, test_branch, shelf_staff, item_copies
    ):
        """Generate an accuracy report for a branch."""
        # Create and complete a session
        session = await ShelfReadingService.create_session(
            db=test_db,
            name="Report Test Session",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        for i in range(3):
            await ShelfReadingService.scan_item(
                test_db, session, item_copies[i], shelf_staff.id
            )
        await ShelfReadingService.complete_session(test_db, session)
        await test_db.commit()

        now = datetime.now(timezone.utc)
        report = await ShelfReadingService.get_accuracy_report(
            db=test_db,
            branch_id=test_branch.id,
            period_start=now - timedelta(days=1),
            period_end=now + timedelta(days=1),
        )

        assert report["branch_id"] == test_branch.id
        assert report["branch_name"] == "Main Branch"
        assert report["total_sessions"] == 1
        assert report["total_items_scanned"] == 3
        assert report["items_in_order"] == 3
        assert report["overall_accuracy"] == 100.0

    async def test_branch_summaries(
        self, test_db, test_branch, second_branch, shelf_staff, item_copies
    ):
        """Get accuracy summaries across branches."""
        # Create session on first branch
        session1 = await ShelfReadingService.create_session(
            db=test_db,
            name="Main Branch Session",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        await ShelfReadingService.scan_item(
            test_db, session1, item_copies[0], shelf_staff.id
        )
        await ShelfReadingService.complete_session(test_db, session1)

        # Create session on second branch
        session2 = await ShelfReadingService.create_session(
            db=test_db,
            name="North Branch Session",
            branch_id=second_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        await ShelfReadingService.scan_item(
            test_db, session2, item_copies[1], shelf_staff.id
        )
        await ShelfReadingService.complete_session(test_db, session2)
        await test_db.commit()

        summaries = await ShelfReadingService.get_branch_summaries(test_db)

        assert len(summaries) == 2
        branch_ids = {s["branch_id"] for s in summaries}
        assert test_branch.id in branch_ids
        assert second_branch.id in branch_ids

    async def test_historical_accuracy(
        self, test_db, test_branch, shelf_staff, item_copies
    ):
        """Get historical accuracy trends."""
        # Create a completed session
        session = await ShelfReadingService.create_session(
            db=test_db,
            name="Historical Test",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        await ShelfReadingService.scan_item(
            test_db, session, item_copies[0], shelf_staff.id
        )
        await ShelfReadingService.complete_session(test_db, session)
        await test_db.commit()

        history = await ShelfReadingService.get_historical_accuracy(
            test_db, test_branch.id, months=12
        )

        assert len(history) >= 1
        assert history[0]["sessions"] == 1
        assert history[0]["accuracy"] == 100.0

    async def test_empty_accuracy_report(self, test_db, test_branch):
        """Report returns zero values when no sessions exist."""
        now = datetime.now(timezone.utc)
        report = await ShelfReadingService.get_accuracy_report(
            db=test_db,
            branch_id=test_branch.id,
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert report["total_sessions"] == 0
        assert report["total_items_scanned"] == 0
        assert report["overall_accuracy"] == 0.0


# ============ Schedule Tests ============


class TestShelfReadingSchedules:
    """Tests for shelf reading schedule management."""

    async def test_create_schedule(self, test_db, test_branch, shelf_staff):
        """Create a shelf reading schedule."""
        schedule = ShelfReadingSchedule(
            name="Weekly Fiction Check",
            branch_id=test_branch.id,
            location="Adult Fiction B-2",
            frequency=ScheduleFrequency.WEEKLY,
            is_active=True,
            created_by_id=shelf_staff.id,
            next_due_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        test_db.add(schedule)
        await test_db.commit()
        await test_db.refresh(schedule)

        assert schedule.id is not None
        assert schedule.frequency == ScheduleFrequency.WEEKLY
        assert schedule.is_active is True

    async def test_schedule_frequencies(self, test_db, test_branch, shelf_staff):
        """Verify all schedule frequencies work."""
        for freq in ScheduleFrequency:
            schedule = ShelfReadingSchedule(
                name=f"{freq.value} Check",
                branch_id=test_branch.id,
                location="Test Location",
                frequency=freq,
                created_by_id=shelf_staff.id,
            )
            test_db.add(schedule)

        await test_db.commit()

        from sqlalchemy import select, func
        count_result = await test_db.execute(
            select(func.count(ShelfReadingSchedule.id))
        )
        count = count_result.scalar()
        assert count == len(ScheduleFrequency)

    async def test_deactivate_schedule(self, test_db, test_branch, shelf_staff):
        """Deactivate a schedule."""
        schedule = ShelfReadingSchedule(
            name="Deactivation Test",
            branch_id=test_branch.id,
            location="Test",
            frequency=ScheduleFrequency.MONTHLY,
            is_active=True,
            created_by_id=shelf_staff.id,
        )
        test_db.add(schedule)
        await test_db.commit()

        schedule.is_active = False
        await test_db.commit()
        await test_db.refresh(schedule)

        assert schedule.is_active is False

    async def test_assign_schedule_to_staff(
        self, test_db, test_branch, shelf_staff
    ):
        """Assign a schedule to a specific staff member."""
        schedule = ShelfReadingSchedule(
            name="Assigned Check",
            branch_id=test_branch.id,
            location="Test",
            frequency=ScheduleFrequency.BIWEEKLY,
            assigned_to_id=shelf_staff.id,
            created_by_id=shelf_staff.id,
        )
        test_db.add(schedule)
        await test_db.commit()
        await test_db.refresh(schedule)

        assert schedule.assigned_to_id == shelf_staff.id


# ============ Call Number Order Tests ============


class TestCallNumberOrdering:
    """Tests for call number comparison used in shelf reading."""

    def test_lc_call_numbers_in_order(self):
        """LC call numbers sort correctly."""
        result = CallNumberService.compare_call_numbers("QA100.A33", "QA276.B76")
        assert result == -1  # First comes before second

    def test_lc_call_numbers_out_of_order(self):
        """Detect LC call numbers that are out of order."""
        result = CallNumberService.compare_call_numbers("QA276.B76", "QA100.A33")
        assert result == 1  # First comes after second

    def test_lc_call_numbers_equal(self):
        """Identical call numbers compare as equal."""
        result = CallNumberService.compare_call_numbers("QA100.A33", "QA100.A33")
        assert result == 0

    def test_dewey_call_numbers_in_order(self):
        """Dewey call numbers sort correctly."""
        result = CallNumberService.compare_call_numbers("025.04", "813.54")
        assert result == -1

    def test_mixed_call_number_sorting(self):
        """Sort a list of mixed call numbers."""
        numbers = ["PS3557.R3355", "QA76.73.P98", "025.04", "813.54"]
        sorted_numbers = CallNumberService.sort_call_numbers(numbers)
        assert len(sorted_numbers) == 4
        # LC should come before Dewey in this service's ordering
        assert sorted_numbers[0] in ("PS3557.R3355", "QA76.73.P98")

    def test_sort_key_empty_string(self):
        """Empty call number sorts to end."""
        key = CallNumberService.get_sort_key("")
        assert key == ("ZZZ", 0)


# ============ Model Tests ============


class TestShelfReadingModels:
    """Tests for shelf reading model integrity."""

    async def test_session_model_fields(self, test_db, test_branch, shelf_staff):
        """Verify all session model fields are stored and retrieved."""
        session = ShelfReadingSession(
            name="Field Test",
            description="Testing all fields",
            branch_id=test_branch.id,
            location="Test Location",
            call_number_start="A1",
            call_number_end="Z99",
            status=ShelfReadingStatus.IN_PROGRESS,
            created_by_id=shelf_staff.id,
        )
        test_db.add(session)
        await test_db.commit()
        await test_db.refresh(session)

        assert session.name == "Field Test"
        assert session.description == "Testing all fields"
        assert session.call_number_start == "A1"
        assert session.call_number_end == "Z99"
        assert session.started_at is not None
        assert session.created_at is not None

    async def test_scan_model_fields(
        self, test_db, shelf_session, item_copies, shelf_staff
    ):
        """Verify scan model fields."""
        scan = ShelfReadingScan(
            session_id=shelf_session.id,
            item_copy_id=item_copies[0].id,
            scan_order=1,
            scanned_call_number="QA100.A33",
            result=ScanResult.IN_ORDER,
            scanned_by_id=shelf_staff.id,
        )
        test_db.add(scan)
        await test_db.commit()
        await test_db.refresh(scan)

        assert scan.session_id == shelf_session.id
        assert scan.scan_order == 1
        assert scan.result == ScanResult.IN_ORDER
        assert scan.scanned_at is not None

    async def test_scan_result_enum_values(self):
        """Verify ScanResult enum has expected values."""
        assert ScanResult.IN_ORDER == "in_order"
        assert ScanResult.OUT_OF_ORDER == "out_of_order"
        assert ScanResult.WRONG_SHELF == "wrong_shelf"

    async def test_session_status_enum_values(self):
        """Verify ShelfReadingStatus enum has expected values."""
        assert ShelfReadingStatus.IN_PROGRESS == "in_progress"
        assert ShelfReadingStatus.PAUSED == "paused"
        assert ShelfReadingStatus.COMPLETED == "completed"
        assert ShelfReadingStatus.CANCELLED == "cancelled"

    async def test_schedule_frequency_enum_values(self):
        """Verify ScheduleFrequency enum has expected values."""
        assert ScheduleFrequency.WEEKLY == "weekly"
        assert ScheduleFrequency.BIWEEKLY == "biweekly"
        assert ScheduleFrequency.MONTHLY == "monthly"
        assert ScheduleFrequency.QUARTERLY == "quarterly"


# ============ Edge Cases ============


class TestShelfReadingEdgeCases:
    """Edge case and boundary condition tests."""

    async def test_scan_item_without_call_number(
        self, test_db, shelf_session, shelf_staff, test_branch
    ):
        """Handle items that have no call number."""
        # Create an item without a call number
        item = CatalogItem(
            title="Uncataloged Item",
            status=ItemStatus.available,
            location="Adult Nonfiction A-1",
        )
        test_db.add(item)
        await test_db.commit()

        copy = ItemCopy(
            catalog_item_id=item.id,
            barcode="NO-CN-001",
            copy_number=1,
            condition=ItemCondition.GOOD,
            location="Adult Nonfiction A-1",
        )
        test_db.add(copy)
        await test_db.commit()
        await test_db.refresh(copy)

        scan = await ShelfReadingService.scan_item(
            db=test_db,
            session=shelf_session,
            item_copy=copy,
            scanned_by_id=shelf_staff.id,
        )
        await test_db.commit()

        # Should still produce a result (IN_ORDER since no comparison possible)
        assert scan.result == ScanResult.IN_ORDER
        assert scan.scanned_call_number is None

    async def test_session_with_mixed_results(
        self, test_db, test_branch, shelf_staff, item_copies
    ):
        """Session with a mix of in-order, out-of-order, and wrong-shelf results."""
        session = await ShelfReadingService.create_session(
            db=test_db,
            name="Mixed Results",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )

        # First scan: in order (always)
        await ShelfReadingService.scan_item(
            test_db, session, item_copies[0], shelf_staff.id
        )
        # Second scan: in order (QA276 after QA100)
        await ShelfReadingService.scan_item(
            test_db, session, item_copies[1], shelf_staff.id
        )
        # Third scan: wrong shelf (Adult Fiction item on Nonfiction shelf)
        await ShelfReadingService.scan_item(
            test_db, session, item_copies[4], shelf_staff.id
        )
        await test_db.commit()

        assert session.total_items_scanned == 3
        assert session.items_in_order == 2
        assert session.items_wrong_shelf == 1

    async def test_multiple_sessions_for_same_location(
        self, test_db, test_branch, shelf_staff
    ):
        """Multiple sessions can exist for the same shelf location."""
        s1 = await ShelfReadingService.create_session(
            db=test_db,
            name="Morning Read",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        s2 = await ShelfReadingService.create_session(
            db=test_db,
            name="Afternoon Read",
            branch_id=test_branch.id,
            location="Adult Nonfiction A-1",
            created_by_id=shelf_staff.id,
        )
        await test_db.commit()

        assert s1.id != s2.id
        assert s1.location == s2.location
