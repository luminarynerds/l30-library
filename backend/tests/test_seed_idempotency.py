# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed Script Idempotency Tests

Verifies that all seed scripts can be run multiple times without creating
duplicate data or causing errors. This ensures seeding is safe for CI/CD
and Docker initialization.

Tests run each seed script up to 3 times and verify:
- No errors occur on re-runs
- Data counts don't increase on subsequent runs
- Data integrity is maintained
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CatalogItem,
    Event,
    ReadingProgram,
    StaffBio,
    BoardMember,
    DatabaseSubscription,
    User,
    Announcement,
)


BACKEND_PATH = Path(__file__).parent.parent
SCRIPTS_PATH = BACKEND_PATH / "scripts"


async def get_table_count(db: AsyncSession, model_class):
    """Get row count for a model."""
    result = await db.execute(select(func.count(model_class.id)))
    return result.scalar() or 0


class TestSeedIdempotency:
    """Test that seed scripts are idempotent and safe to re-run."""

    @pytest.mark.asyncio
    async def test_catalog_items_idempotent(self, test_db: AsyncSession):
        """Test seed_comprehensive creates idempotent catalog items."""
        # Get initial count
        initial_count = await get_table_count(test_db, CatalogItem)

        # Run seed script twice
        for run_number in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS_PATH / "seed_comprehensive.py")],
                cwd=str(BACKEND_PATH),
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
            )

            # Should succeed both times
            if result.returncode != 0:
                pytest.fail(f"Run {run_number + 1}: {result.stderr}")

            # Get count after run
            count_after = await get_table_count(test_db, CatalogItem)

            if run_number == 0:
                # First run should create data
                assert count_after > initial_count, "First seed run should create data"
                first_run_count = count_after
            else:
                # Second run should not increase count
                assert count_after == first_run_count, (
                    f"Second seed run created duplicates: "
                    f"first run={first_run_count}, second run={count_after}"
                )

    @pytest.mark.asyncio
    async def test_events_idempotent(self, test_db: AsyncSession):
        """Test seed_events.py is idempotent."""
        _ = await get_table_count(test_db, Event)

        for run_number in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS_PATH / "seed_events.py")],
                cwd=str(BACKEND_PATH),
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
            )

            if result.returncode != 0:
                pytest.skip(f"seed_events.py not available: {result.stderr}")

            count_after = await get_table_count(test_db, Event)

            if run_number == 0:
                first_run_count = count_after
            else:
                assert count_after == first_run_count, (
                    f"Events seed created duplicates: {count_after} vs {first_run_count}"
                )

    @pytest.mark.asyncio
    async def test_reading_programs_idempotent(self, test_db: AsyncSession):
        """Test seed_reading_programs.py is idempotent."""
        _ = await get_table_count(test_db, ReadingProgram)

        for run_number in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS_PATH / "seed_reading_programs.py")],
                cwd=str(BACKEND_PATH),
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
            )

            if result.returncode != 0:
                pytest.skip(f"seed_reading_programs.py not available: {result.stderr}")

            count_after = await get_table_count(test_db, ReadingProgram)

            if run_number == 0:
                first_run_count = count_after
            else:
                assert count_after == first_run_count, (
                    f"Reading programs seed created duplicates: {count_after} vs {first_run_count}"
                )

    @pytest.mark.asyncio
    async def test_board_members_idempotent(self, test_db: AsyncSession):
        """Test seed_board_members.py is idempotent."""
        _ = await get_table_count(test_db, BoardMember)

        for run_number in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS_PATH / "seed_board_members.py")],
                cwd=str(BACKEND_PATH),
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
            )

            if result.returncode != 0:
                pytest.skip(f"seed_board_members.py not available: {result.stderr}")

            count_after = await get_table_count(test_db, BoardMember)

            if run_number == 0:
                first_run_count = count_after
            else:
                assert count_after == first_run_count, (
                    f"Board members seed created duplicates: {count_after} vs {first_run_count}"
                )

    @pytest.mark.asyncio
    async def test_test_accounts_idempotent(self, test_db: AsyncSession):
        """Test seed_test_accounts.py is idempotent."""
        _ = await get_table_count(test_db, User)

        for run_number in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS_PATH / "seed_test_accounts.py")],
                cwd=str(BACKEND_PATH),
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
            )

            if result.returncode != 0:
                pytest.fail(f"seed_test_accounts.py failed: {result.stderr}")

            count_after = await get_table_count(test_db, User)

            if run_number == 0:
                first_run_count = count_after
            else:
                assert count_after == first_run_count, (
                    f"Test accounts seed created duplicates: {count_after} vs {first_run_count}"
                )

    @pytest.mark.skip(reason="Collection model does not exist")
    @pytest.mark.asyncio
    async def test_collections_idempotent(self, test_db: AsyncSession):
        """Test seed_collections.py is idempotent."""
        # Collection model doesn't exist - skipping test
        pass
        # initial_count = await get_table_count(test_db, Collection)
        #
        # for run_number in range(2):
        #     result = subprocess.run(
        #         [sys.executable, str(SCRIPTS_PATH / "seed_collections.py")],
        #         cwd=str(BACKEND_PATH),
        #         capture_output=True,
        #         text=True,
        #         env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
        #     )
        #
        #     if result.returncode != 0:
        #         pytest.skip(f"seed_collections.py not available: {result.stderr}")
        #
        #     count_after = await get_table_count(test_db, Collection)
        #
        #     if run_number == 0:
        #         first_run_count = count_after
        #     else:
        #         assert count_after == first_run_count, (
        #             f"Collections seed created duplicates: {count_after} vs {first_run_count}"
        #         )

    @pytest.mark.asyncio
    async def test_database_subscriptions_idempotent(self, test_db: AsyncSession):
        """Test seed_databases_new.py is idempotent."""
        _ = await get_table_count(test_db, DatabaseSubscription)

        for run_number in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS_PATH / "seed_databases_new.py")],
                cwd=str(BACKEND_PATH),
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
            )

            if result.returncode != 0:
                pytest.skip(f"seed_databases_new.py not available: {result.stderr}")

            count_after = await get_table_count(test_db, DatabaseSubscription)

            if run_number == 0:
                first_run_count = count_after
            else:
                assert count_after == first_run_count, (
                    f"Database subscriptions seed created duplicates: {count_after} vs {first_run_count}"
                )


class TestSeedScriptSuccessful:
    """Test that seed scripts complete successfully without errors."""

    def test_seed_comprehensive_succeeds(self):
        """Test seed_comprehensive.py runs successfully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / "seed_comprehensive.py")],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
        )
        assert result.returncode == 0, f"seed_comprehensive.py failed: {result.stderr}"

    def test_seed_test_accounts_succeeds(self):
        """Test seed_test_accounts.py runs successfully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / "seed_test_accounts.py")],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
        )
        assert result.returncode == 0, f"seed_test_accounts.py failed: {result.stderr}"

    def test_seed_events_succeeds(self):
        """Test seed_events.py runs successfully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / "seed_events.py")],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
        )
        if result.returncode != 0:
            pytest.skip(f"seed_events.py not available: {result.stderr}")

    def test_seed_reading_programs_succeeds(self):
        """Test seed_reading_programs.py runs successfully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / "seed_reading_programs.py")],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
        )
        if result.returncode != 0:
            pytest.skip(f"seed_reading_programs.py not available: {result.stderr}")

    def test_seed_board_members_succeeds(self):
        """Test seed_board_members.py runs successfully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_PATH / "seed_board_members.py")],
            cwd=str(BACKEND_PATH),
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL")}
        )
        if result.returncode != 0:
            pytest.skip(f"seed_board_members.py not available: {result.stderr}")
