# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test suite for seed_learning_journeys.py

Tests that learning journey seed script works correctly and produces
expected data structures for Carmen, Amir, and Sofia.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole, PatronStatus
from app.models.learning import Enrollment, Course
from app.models.event_registration import EventRegistration
from app.models.circulation import Checkout


BACKEND_PATH = Path(__file__).parent.parent
SCRIPTS_PATH = BACKEND_PATH / "scripts"


@pytest.fixture(autouse=True)
def _seed_learning_journeys():
    """Actually run the seed scripts before each test.

    This file's tests read from a bare AsyncSessionLocal() session (see the
    `db` fixture below), not the `test_db` fixture -- so nothing in this
    file itself seeds Carmen/Amir/Sofia. Every other test file's `test_db`
    fixture truncates all tables in its teardown (tests/conftest.py), so by
    the time this module runs there is no guarantee any of that data still
    exists. Run the seed scripts for real (same subprocess pattern as
    tests/test_seed_idempotency.py) so the assertions below have something
    to find.

    seed_learning_journeys.py's event-registration and checkout activities
    (add_journey_activities) attach to *existing* catalog items/events/item
    copies -- it doesn't create its own. In the real bootstrap order (see
    scripts/seed_demo_master.py: CORE_SCRIPTS runs seed_test_accounts.py and
    seed_comprehensive.py in Phase 1 and seed_inventory_operations.py in
    Phase 4, all well before DEMO_SCRIPTS runs seed_learning_journeys.py in
    Phase 9) that's fine, but run in isolation against a freshly-truncated
    test DB there's nothing to attach to: no catalog items/events means no
    enrollments/registrations, and seed_inventory_operations.py needs both
    catalog items AND a staff/admin user to create any ItemCopy rows (it
    bails with no-op if either is missing) -- without ItemCopy rows,
    add_journey_activities' `if item_copy:` guard never fires, so no
    checkouts. Seed accounts/catalog items/events/item-copies first to
    match that real ordering.
    """
    for script in (
        "seed_test_accounts.py",
        "seed_comprehensive.py",
        "seed_inventory_operations.py",
        "seed_learning_journeys.py",
    ):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / script)],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")},
        )
        if result.returncode != 0:
            pytest.fail(
                f"{script} failed (rc={result.returncode}): "
                f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}"
            )


@pytest.mark.asyncio
class TestLearningJourneySeeding:
    """Test suite for learning journey seed data."""

    @pytest.fixture
    async def db(self):
        """Provide database session."""
        async with AsyncSessionLocal() as session:
            yield session

    async def test_carmen_accessibility_journey_created(self, db):
        """Test that Carmen's accessibility journey patron is created."""
        result = await db.execute(
            select(User).where(User.email == "carmen.accessibility@l30.org")
        )
        carmen = result.scalar_one_or_none()

        assert carmen is not None, "Carmen should be created"
        assert carmen.first_name == "Carmen"
        assert carmen.last_name == "Rivera"
        assert carmen.role == UserRole.PATRON
        assert carmen.patron_status == PatronStatus.ACTIVE
        assert "ADHD" in carmen.accessibility_needs or "Dyslexia" in carmen.accessibility_needs

    async def test_amir_digital_literacy_journey_created(self, db):
        """Test that Amir's digital literacy journey patron is created."""
        result = await db.execute(
            select(User).where(User.email == "amir.digital@l30.org")
        )
        amir = result.scalar_one_or_none()

        assert amir is not None, "Amir should be created"
        assert amir.first_name == "Amir"
        assert amir.last_name == "Hassan"
        assert amir.role == UserRole.PATRON
        assert amir.patron_status == PatronStatus.ACTIVE

    async def test_sofia_makerspace_journey_created(self, db):
        """Test that Sofia's makerspace journey patron is created."""
        result = await db.execute(
            select(User).where(User.email == "sofia.maker@l30.org")
        )
        sofia = result.scalar_one_or_none()

        assert sofia is not None, "Sofia should be created"
        assert sofia.first_name == "Sofia"
        assert sofia.last_name == "Chen"
        assert sofia.role == UserRole.PATRON
        assert sofia.patron_status == PatronStatus.ACTIVE

    async def test_carmen_has_course_enrollments(self, db):
        """Test that Carmen is enrolled in accessibility courses."""
        result = await db.execute(
            select(User).where(User.email == "carmen.accessibility@l30.org")
        )
        carmen = result.scalar_one_or_none()

        assert carmen is not None

        # Check enrollments
        enrollments = await db.execute(
            select(Enrollment).where(Enrollment.user_id == carmen.id)
        )
        enrollments_list = enrollments.scalars().all()

        assert len(enrollments_list) > 0, "Carmen should have course enrollments"

        # Verify courses are accessibility-related
        for enrollment in enrollments_list:
            assert enrollment.course_id is not None
            course = await db.execute(
                select(Course).where(Course.id == enrollment.course_id)
            )
            course_obj = course.scalar_one_or_none()
            assert course_obj is not None
            # Course should be accessibility or digital literacy related
            assert "Accessibility" in course_obj.title or "Digital" in course_obj.title

    async def test_amir_has_course_enrollments(self, db):
        """Test that Amir is enrolled in digital literacy courses."""
        result = await db.execute(
            select(User).where(User.email == "amir.digital@l30.org")
        )
        amir = result.scalar_one_or_none()

        assert amir is not None

        # Check enrollments
        enrollments = await db.execute(
            select(Enrollment).where(Enrollment.user_id == amir.id)
        )
        enrollments_list = enrollments.scalars().all()

        assert len(enrollments_list) > 0, "Amir should have course enrollments"

        # Verify courses are digital literacy related
        for enrollment in enrollments_list:
            assert enrollment.course_id is not None
            course = await db.execute(
                select(Course).where(Course.id == enrollment.course_id)
            )
            course_obj = course.scalar_one_or_none()
            assert course_obj is not None
            # Course should be digital literacy or related
            assert (
                "Digital" in course_obj.title
                or "Internet" in course_obj.title
                or "Productivity" in course_obj.title
            )

    async def test_sofia_has_course_enrollments(self, db):
        """Test that Sofia is enrolled in makerspace courses."""
        result = await db.execute(
            select(User).where(User.email == "sofia.maker@l30.org")
        )
        sofia = result.scalar_one_or_none()

        assert sofia is not None

        # Check enrollments
        enrollments = await db.execute(
            select(Enrollment).where(Enrollment.user_id == sofia.id)
        )
        enrollments_list = enrollments.scalars().all()

        assert len(enrollments_list) > 0, "Sofia should have course enrollments"

        # Verify courses are makerspace related
        for enrollment in enrollments_list:
            assert enrollment.course_id is not None
            course = await db.execute(
                select(Course).where(Course.id == enrollment.course_id)
            )
            course_obj = course.scalar_one_or_none()
            assert course_obj is not None
            # Course should be makerspace or design related
            assert (
                "Makerspace" in course_obj.title
                or "Printer" in course_obj.title
                or "Laser" in course_obj.title
                or "CNC" in course_obj.title
            )

    async def test_patrons_have_event_registrations(self, db):
        """Test that journey patrons are registered for events."""
        emails = [
            "carmen.accessibility@l30.org",
            "amir.digital@l30.org",
            "sofia.maker@l30.org",
        ]

        for email in emails:
            registrations = await db.execute(
                select(EventRegistration).where(EventRegistration.patron_email == email)
            )
            reg_list = registrations.scalars().all()

            assert (
                len(reg_list) > 0
            ), f"Patron {email} should have event registrations"

    async def test_patrons_have_checkouts(self, db):
        """Test that journey patrons have made checkouts."""
        result = await db.execute(
            select(User).where(User.email == "carmen.accessibility@l30.org")
        )
        carmen = result.scalar_one_or_none()

        assert carmen is not None

        checkouts = await db.execute(
            select(Checkout).where(Checkout.user_id == carmen.id)
        )
        checkout_list = checkouts.scalars().all()

        assert len(checkout_list) > 0, "Carmen should have checkouts"

    async def test_carmen_has_accessibility_preferences(self, db):
        """Test that Carmen has accessibility preferences configured."""
        from app.models.learning import UserPreferences

        result = await db.execute(
            select(User).where(User.email == "carmen.accessibility@l30.org")
        )
        carmen = result.scalar_one_or_none()

        assert carmen is not None

        prefs = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == carmen.id)
        )
        pref_obj = prefs.scalar_one_or_none()

        assert pref_obj is not None, "Carmen should have accessibility preferences"
        assert pref_obj.dyslexia_font or pref_obj.high_contrast

    async def test_idempotency_no_duplicates(self, db):
        """Test that running seed twice doesn't create duplicates."""
        # First query - should find Carmen
        result1 = await db.execute(
            select(User).where(User.email == "carmen.accessibility@l30.org")
        )
        carmen1 = result1.scalar_one_or_none()

        # Second query - should find same Carmen
        result2 = await db.execute(
            select(User).where(User.email == "carmen.accessibility@l30.org")
        )
        carmen2 = result2.scalar_one_or_none()

        if carmen1 and carmen2:
            assert carmen1.id == carmen2.id, "Should be same patron"

    async def test_all_three_journeys_distinct(self, db):
        """Test that the three journey patrons are distinct."""
        carmen_email = "carmen.accessibility@l30.org"
        amir_email = "amir.digital@l30.org"
        sofia_email = "sofia.maker@l30.org"

        # Query all three
        result = await db.execute(
            select(User).where(
                User.email.in_([carmen_email, amir_email, sofia_email])
            )
        )
        patrons = result.scalars().all()

        assert len(patrons) == 3, "Should have exactly three journey patrons"

        # Verify they're distinct
        ids = [p.id for p in patrons]
        assert len(set(ids)) == 3, "All patrons should have unique IDs"


@pytest.mark.asyncio
class TestLearningJourneyDataQuality:
    """Test data quality of seeded learning journeys."""

    @pytest.fixture
    async def db(self):
        """Provide database session."""
        async with AsyncSessionLocal() as session:
            yield session

    async def test_patrons_are_active(self, db):
        """Test that all journey patrons are active."""
        result = await db.execute(
            select(User).where(
                User.email.in_([
                    "carmen.accessibility@l30.org",
                    "amir.digital@l30.org",
                    "sofia.maker@l30.org",
                ])
            )
        )
        patrons = result.scalars().all()

        for patron in patrons:
            assert patron.is_active, f"{patron.email} should be active"
            assert patron.patron_status == PatronStatus.ACTIVE

    async def test_email_verified(self, db):
        """Test that test emails are verified."""
        result = await db.execute(
            select(User).where(
                User.email.in_([
                    "carmen.accessibility@l30.org",
                    "amir.digital@l30.org",
                    "sofia.maker@l30.org",
                ])
            )
        )
        patrons = result.scalars().all()

        for patron in patrons:
            assert patron.email_verified, f"{patron.email} should be verified"

    async def test_tracking_enabled(self, db):
        """Test that reading history tracking is enabled."""
        result = await db.execute(
            select(User).where(
                User.email.in_([
                    "carmen.accessibility@l30.org",
                    "amir.digital@l30.org",
                    "sofia.maker@l30.org",
                ])
            )
        )
        patrons = result.scalars().all()

        for patron in patrons:
            assert patron.track_reading_history, f"{patron.email} should track reading history"

    async def test_proper_timestamps(self, db):
        """Test that created/updated timestamps are reasonable."""
        result = await db.execute(
            select(User).where(
                User.email.in_([
                    "carmen.accessibility@l30.org",
                    "amir.digital@l30.org",
                    "sofia.maker@l30.org",
                ])
            )
        )
        patrons = result.scalars().all()

        now = datetime.now(timezone.utc)

        for patron in patrons:
            assert patron.created_at is not None
            # Created should be recent (within last hour for testing)
            time_diff = (now - patron.created_at).total_seconds()
            assert 0 <= time_diff <= 3600, f"{patron.email} creation time seems off"
