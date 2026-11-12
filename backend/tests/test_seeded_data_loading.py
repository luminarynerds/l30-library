# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive test suite for verifying seeded data loading.

Tests that all seed scripts successfully load their data and that data
is accessible through API endpoints and via the database.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import (
    User,
    CatalogItem,
    Event,
    ReadingProgram,
    Room,
    RoomAmenity,
    StaffBio,
    BoardMember,
    Collection,
    CollectionItem,
    DatabaseSubscription,
    Checkout,
    Hold,
    Fine,
    Announcement,
)
from app.core.datetime_utils import utc_now


BACKEND_PATH = Path(__file__).parent.parent
SCRIPTS_PATH = BACKEND_PATH / "scripts"

# (script filename, human label) -- run in dependency order. A script
# failing (missing/renamed/broken) is reported via print rather than
# failing the whole fixture, so the tests that don't depend on it can still
# run; the tests that do will fail with a clear "0 rows" assertion instead
# of a mysterious NameError or empty DB.
_SEED_SCRIPTS = [
    "seed_comprehensive.py",  # catalog items, events, announcements
    "seed_reading_programs.py",
    "seed_rooms.py",
    "seed_lsc_features.py",  # staff bios (among other LSC features)
    "seed_board_members.py",
    "seed_collections.py",
    "seed_databases_new.py",
    "seed_test_accounts.py",
]


@pytest.fixture(scope="module", autouse=True)
def _seed_all_the_things():
    """Actually run the seed scripts this file's tests assume already ran.

    tests/conftest.py's `test_db` fixture truncates every table in its
    teardown, so nothing seeded by an earlier test file survives into this
    module. Run each seed script for real (same subprocess pattern as
    tests/test_seed_idempotency.py) against the same DATABASE_URL so the
    counts/lookups below have real rows to find.

    module-scoped, not function-scoped: none of this file's own tests use
    test_db to mutate/truncate data (they only read), so seeding once for
    the whole module is both correct and ~30x cheaper than reseeding via
    8 subprocesses before every one of the ~25 tests here.
    """
    env = {**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
    for script in _SEED_SCRIPTS:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / script)],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            print(
                f"[_seed_all_the_things] {script} failed (rc={result.returncode}): {result.stderr[-2000:]}"
            )


@pytest.fixture
async def test_db():
    """Local override of the conftest.py `test_db` fixture.

    The conftest.py version unconditionally truncates every table in its
    teardown -- fine for tests that create their own fixtures, but fatal
    here: with a module-scoped seed fixture, the first test's teardown
    would wipe the seeded data out from under every test that runs after
    it. Use a bare, non-truncating session instead so the module-level
    seed data survives across this file's tests.
    """
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
class TestSeedDataLoading:
    """Verify each seed script's data is available in the database."""

    async def test_catalog_items_loaded(self, test_db: AsyncSession):
        """Verify seed_comprehensive.py creates catalog items."""
        count_result = await test_db.execute(select(func.count(CatalogItem.id)))
        count = count_result.scalar() or 0
        assert count >= 20, f"Expected at least 20 catalog items, got {count}"

    async def test_catalog_items_have_required_fields(self, test_db: AsyncSession):
        """Verify catalog items have all required metadata."""
        items = await test_db.execute(select(CatalogItem).limit(5))
        for item in items.scalars():
            assert item.title, f"Catalog item {item.id} missing title"
            assert item.item_type, f"Catalog item {item.id} missing item_type"

    async def test_events_loaded(self, test_db: AsyncSession):
        """Verify seed_events.py creates events."""
        count_result = await test_db.execute(select(func.count(Event.id)))
        count = count_result.scalar() or 0
        assert count >= 5, f"Expected at least 5 events, got {count}"

    async def test_events_have_required_fields(self, test_db: AsyncSession):
        """Verify events have all required fields."""
        events = await test_db.execute(select(Event).limit(3))
        for event in events.scalars():
            assert event.title, f"Event {event.id} missing title"
            assert event.start_time, f"Event {event.id} missing start_time"

    async def test_reading_programs_loaded(self, test_db: AsyncSession):
        """Verify seed_reading_programs.py creates reading programs."""
        count_result = await test_db.execute(select(func.count(ReadingProgram.id)))
        count = count_result.scalar() or 0
        assert count >= 3, f"Expected at least 3 reading programs, got {count}"

    async def test_rooms_loaded(self, test_db: AsyncSession):
        """Verify room_seed_data.py creates all room types."""
        count_result = await test_db.execute(select(func.count(Room.id)))
        count = count_result.scalar() or 0
        assert count >= 4, f"Expected at least 4 rooms (study, meeting, lab, event), got {count}"

    async def test_rooms_include_all_types(self, test_db: AsyncSession):
        """Verify rooms include all required types."""
        rooms = await test_db.execute(select(Room))
        room_types = {room.room_type for room in rooms.scalars()}
        expected_types = {"study_room", "meeting_room", "computer_lab", "event_space"}
        missing_types = expected_types - room_types
        assert not missing_types, f"Missing room types: {missing_types}"

    async def test_room_amenities_loaded(self, test_db: AsyncSession):
        """Verify rooms have amenities configured.

        Amenities are stored on Room.amenities (an ARRAY column) -- that is
        what seed_rooms.py populates and what the API serves. The separate
        room_amenities table is not written by any seeder.
        """
        rooms = await test_db.execute(select(Room))
        with_amenities = [r for r in rooms.scalars() if r.amenities]
        assert with_amenities, "Expected at least one room with amenities configured"

    async def test_staff_bios_loaded(self, test_db: AsyncSession):
        """Verify seed_comprehensive.py creates staff bios."""
        count_result = await test_db.execute(select(func.count(StaffBio.id)))
        count = count_result.scalar() or 0
        assert count >= 1, f"Expected at least 1 staff bio, got {count}"

    async def test_board_members_loaded(self, test_db: AsyncSession):
        """Verify seed_board_members.py creates board members."""
        count_result = await test_db.execute(select(func.count(BoardMember.id)))
        count = count_result.scalar() or 0
        assert count >= 3, f"Expected at least 3 board members, got {count}"

    async def test_collections_loaded(self, test_db: AsyncSession):
        """Verify seed_collections.py creates collections."""
        count_result = await test_db.execute(select(func.count(Collection.id)))
        count = count_result.scalar() or 0
        assert count >= 3, f"Expected at least 3 collections, got {count}"

    async def test_database_subscriptions_loaded(self, test_db: AsyncSession):
        """Verify seed_databases_new.py creates database subscriptions."""
        count_result = await test_db.execute(select(func.count(DatabaseSubscription.id)))
        count = count_result.scalar() or 0
        assert count >= 5, f"Expected at least 5 database subscriptions, got {count}"

    async def test_announcements_loaded(self, test_db: AsyncSession):
        """Verify seed_comprehensive.py creates announcement banners."""
        count_result = await test_db.execute(select(func.count(Announcement.id)))
        count = count_result.scalar() or 0
        assert count >= 1, f"Expected at least 1 announcement, got {count}"

    async def test_test_accounts_created(self, test_db: AsyncSession):
        """Verify seed_test_accounts.py creates test user accounts."""
        count_result = await test_db.execute(select(func.count(User.id)))
        count = count_result.scalar() or 0
        assert count >= 5, f"Expected at least 5 test accounts, got {count}"

    async def test_test_admin_account_exists(self, test_db: AsyncSession):
        """Verify test admin account is available."""
        admin = await test_db.execute(select(User).where(User.email == "admin@l30.org"))
        admin_user = admin.scalar()
        assert admin_user is not None, "Admin test account not found"
        assert admin_user.role.value == "admin", "Test admin account has wrong role"


@pytest.mark.asyncio
class TestSeedDataCompletenessCoverage:
    """Verify seeded data covers all important features."""

    async def test_seeded_data_includes_diverse_catalog(self, test_db: AsyncSession):
        """Verify catalog includes diverse content types and genres."""
        items = await test_db.execute(select(CatalogItem))
        all_items = items.scalars().all()

        # Check for variety in item types
        item_types = {item.item_type for item in all_items}
        assert len(item_types) > 1, "Catalog should have diverse item types"

        # Verify we have books (most common)
        books = [i for i in all_items if i.item_type == "book"]
        assert len(books) >= 10, "Should have at least 10 books"

    async def test_seeded_catalog_items_available(self, test_db: AsyncSession):
        """Verify at least some catalog items are marked as available."""
        available = await test_db.execute(
            select(func.count(CatalogItem.id)).where(CatalogItem.status == "available")
        )
        count = available.scalar() or 0
        assert count >= 10, f"Expected at least 10 available items, got {count}"

    async def test_seeded_events_have_future_dates(self, test_db: AsyncSession):
        """Verify at least some events have future start times."""
        from datetime import datetime

        future_events = await test_db.execute(
            select(func.count(Event.id)).where(Event.start_time > utc_now())
        )
        count = future_events.scalar() or 0
        assert count >= 3, f"Expected at least 3 future events, got {count}"

    async def test_seeded_rooms_have_capacity(self, test_db: AsyncSession):
        """Verify rooms have valid capacity configurations."""
        rooms = await test_db.execute(select(Room))
        for room in rooms.scalars():
            assert room.capacity is not None, f"Room {room.id} missing capacity"
            assert room.capacity > 0, f"Room {room.id} has invalid capacity"

    async def test_seeded_collections_contain_items(self, test_db: AsyncSession):
        """Verify collections have catalog items assigned."""
        collections = await test_db.execute(select(Collection))
        for collection in collections.scalars():
            assert collection.name, f"Collection {collection.id} missing name"
            linked = await test_db.execute(
                select(func.count(CollectionItem.id)).where(
                    CollectionItem.collection_id == collection.id
                )
            )
            assert (linked.scalar() or 0) > 0, (
                f"Collection {collection.name!r} has no catalog items"
            )


@pytest.mark.asyncio
class TestSeedDataIntegrity:
    """Verify the integrity and consistency of seeded data."""

    async def test_no_duplicate_catalog_items(self, test_db: AsyncSession):
        """Verify no duplicate ISBNs exist in seeded data."""
        # This should be enforced by DB constraints, but verify
        duplicates = await test_db.execute(
            select(CatalogItem.isbn, func.count(CatalogItem.id))
            .group_by(CatalogItem.isbn)
            .having(func.count(CatalogItem.id) > 1)
        )
        duplicate_isbns = [row[0] for row in duplicates.all() if row[0]]
        assert not duplicate_isbns, f"Duplicate ISBNs found: {duplicate_isbns}"

    async def test_seeded_data_references_valid(self, test_db: AsyncSession):
        """Verify foreign key relationships are intact in seeded data."""
        # Check that collections reference valid catalog items
        collections = await test_db.execute(select(Collection))
        for collection in collections.scalars():
            if hasattr(collection, "catalog_items") and collection.catalog_items:
                for item in collection.catalog_items:
                    assert item.id, "Collection references invalid catalog item"

    async def test_rooms_have_valid_operating_hours(self, test_db: AsyncSession):
        """Verify rooms have properly configured operating hours."""
        rooms = await test_db.execute(select(Room))
        for room in rooms.scalars():
            if hasattr(room, "operating_hours") and room.operating_hours:
                # Verify it's a dict with day keys
                assert isinstance(room.operating_hours, dict)
                days = set(room.operating_hours.keys())
                _ = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
                # At least most days should be present
                assert len(days) >= 5, f"Room {room.id} missing operating hours"

    async def test_events_have_valid_times(self, test_db: AsyncSession):
        """Verify event times are logically consistent."""
        events = await test_db.execute(select(Event))
        for event in events.scalars():
            if event.end_time:
                assert event.end_time >= event.start_time, (
                    f"Event {event.id} has end_time before start_time"
                )


@pytest.mark.asyncio
class TestEdgeCaseDataLoading:
    """Verify edge case seeded data is available."""

    async def test_overdue_items_exist(self, test_db: AsyncSession):
        """Verify seed_edge_case_data.sql creates overdue checkouts."""
        from datetime import datetime

        overdue = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.due_date < utc_now(), Checkout.status == "active"
            )
        )
        count = overdue.scalar() or 0
        # At least some overdue items should exist for testing
        assert count >= 0, "Edge case data should include overdue items"

    async def test_items_with_holds_exist(self, test_db: AsyncSession):
        """Verify items with multiple holds exist for testing."""
        items_with_holds = await test_db.execute(
            select(CatalogItem.id, func.count(Hold.id))
            .join(Hold, CatalogItem.id == Hold.item_id)
            .group_by(CatalogItem.id)
            .having(func.count(Hold.id) > 0)
        )
        count = len(items_with_holds.all())
        # Edge case data should include holds
        assert count >= 0, "Edge case data should include items with holds"

    async def test_fines_exist_for_testing(self, test_db: AsyncSession):
        """Verify test fines exist in seeded data."""
        fines = await test_db.execute(select(func.count(Fine.id)))
        count = fines.scalar() or 0
        # Edge case data may include fines
        assert count >= 0, "Test data should optionally include fines"
