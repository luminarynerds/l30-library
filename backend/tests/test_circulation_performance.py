# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD Tests for Circulation Performance and Composite Indexes

Tests that composite indexes exist and improve query performance for circulation operations.
These tests follow TDD principles - write tests first, create indexes second.
"""

import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy import text, select, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus


class TestCompositeIndexes:
    """Test that composite indexes exist in the database"""

    @pytest.mark.asyncio
    async def test_checkouts_user_status_index_exists(self, test_db: AsyncSession):
        """Test that composite index on (user_id, status) exists for checkouts"""
        # Query database for index
        result = await test_db.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'checkouts'
                AND indexname = 'ix_checkouts_user_status'
            """)
        )
        index = result.fetchone()

        assert index is not None
        assert "user_id" in index[1]
        assert "status" in index[1]

    @pytest.mark.asyncio
    async def test_checkouts_due_status_index_exists(self, test_db: AsyncSession):
        """Test that composite index on (due_date, status) exists for checkouts"""
        # Query database for index
        result = await test_db.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'checkouts'
                AND indexname = 'ix_checkouts_due_status'
            """)
        )
        index = result.fetchone()

        assert index is not None
        assert "due_date" in index[1]
        assert "status" in index[1]

    @pytest.mark.asyncio
    async def test_holds_user_status_index_exists(self, test_db: AsyncSession):
        """Test that composite index on (user_id, status) exists for holds"""
        # Query database for index
        result = await test_db.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'holds'
                AND indexname = 'ix_holds_user_status'
            """)
        )
        index = result.fetchone()

        assert index is not None
        assert "user_id" in index[1]
        assert "status" in index[1]

    @pytest.mark.asyncio
    async def test_holds_item_status_position_index_exists(self, test_db: AsyncSession):
        """Test that composite index on (item_id, status, position) exists for holds"""
        # Query database for index
        result = await test_db.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'holds'
                AND indexname = 'ix_holds_item_status_position'
            """)
        )
        index = result.fetchone()

        assert index is not None
        assert "item_id" in index[1]
        assert "status" in index[1]
        assert "position" in index[1]


class TestQueryPerformanceWithIndexes:
    """Test that queries use composite indexes for better performance"""

    @pytest.mark.asyncio
    async def test_user_checkouts_query_uses_composite_index(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that querying user's checkouts by status uses composite index"""
        # Create test data
        for i in range(10):
            item = CatalogItem(title=f"Book {i}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Get query plan. On a handful of test rows, Postgres's cost-based
        # planner correctly prefers a sequential scan over the index -- that's
        # not a regression, just accurate costing on tiny data. Disable
        # seqscan for this EXPLAIN so the planner is forced to prove the
        # index CAN serve the query, which is what we actually want to pin.
        # Literal values (not bound params) so Postgres plans against the
        # actual value instead of falling back to a generic parameterized
        # plan, which can pick a different (still valid, but not the one
        # we're pinning) index.
        await test_db.execute(text("SET LOCAL enable_seqscan = OFF"))
        result = await test_db.execute(
            text(f"""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM checkouts
                WHERE user_id = {test_patron.id} AND status = 'active'
            """)
        )
        plan = result.fetchone()[0]

        # Check that an index scan is used (not a sequential scan). Which
        # specific index Postgres picks among several valid options for
        # (user_id, status=active) -- e.g. the composite
        # ix_checkouts_user_status vs. the partial ix_active_item_copy_checkout
        # (itself scoped to status='active') -- is a cost-based,
        # cardinality-dependent choice at this tiny table size; pinning one
        # exact name is brittle. The real regression guard is "doesn't
        # seq-scan checkouts".
        plan_str = str(plan)
        assert "Index Scan" in plan_str or "Bitmap Index Scan" in plan_str
        assert "Seq Scan" not in plan_str

    @pytest.mark.asyncio
    async def test_overdue_query_uses_composite_index(self, test_db: AsyncSession):
        """Test that querying overdue items by due_date and status uses composite index"""
        # Create test data with overdue checkouts
        patron = User(
            email="overdue@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
        )
        test_db.add(patron)
        await test_db.commit()

        for i in range(10):
            item = CatalogItem(title=f"Book {i}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.overdue,
                checked_out_at=datetime.now() - timedelta(days=30),
                due_date=datetime.now() - timedelta(days=i),
            )
            test_db.add(checkout)
        await test_db.commit()

        # See test_user_checkouts_query_uses_composite_index for why seqscan
        # is disabled and literal values (not bound params) are used here.
        await test_db.execute(text("SET LOCAL enable_seqscan = OFF"))
        today_str = datetime.now().isoformat()
        result = await test_db.execute(
            text(f"""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM checkouts
                WHERE due_date < '{today_str}' AND status = 'overdue'
            """)
        )
        plan = result.fetchone()[0]

        # Check that an index scan is used (not a sequential scan). See
        # test_user_checkouts_query_uses_composite_index above for why the
        # exact index name isn't pinned.
        plan_str = str(plan)
        assert "Index Scan" in plan_str or "Bitmap Index Scan" in plan_str
        assert "Seq Scan" not in plan_str

    @pytest.mark.asyncio
    async def test_hold_queue_query_uses_composite_index(self, test_db: AsyncSession):
        """Test that querying hold queue uses composite index on (item_id, status, position)"""
        # Create item with multiple holds
        item = CatalogItem(title="Popular Book", status=ItemStatus.on_hold)
        test_db.add(item)
        await test_db.commit()

        for i in range(10):
            patron = User(
                email=f"patron{i}@test.com",
                password_hash="hash",
                first_name=f"Patron{i}",
                last_name="User",
                role=UserRole.PATRON,
            )
            test_db.add(patron)
            await test_db.commit()

            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=i + 1,
            )
            test_db.add(hold)
        await test_db.commit()

        # See test_user_checkouts_query_uses_composite_index for why seqscan
        # is disabled here.
        await test_db.execute(text("SET LOCAL enable_seqscan = OFF"))
        result = await test_db.execute(
            text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM holds
                WHERE item_id = :item_id AND status = :status
                ORDER BY position
            """),
            {"item_id": item.id, "status": "pending"},
        )
        plan = result.fetchone()[0]

        # Check that index scan is used
        plan_str = str(plan)
        assert "Index Scan" in plan_str or "Bitmap Index Scan" in plan_str
        assert "ix_holds_item_status_position" in plan_str.lower()


class TestPerformanceBenchmarks:
    """Benchmark query performance with indexes.

    These time a whole ORM round-trip (asyncpg call + SQLAlchemy materialising the
    rows), not the query. The database side is ~0.2ms -- EXPLAIN ANALYZE on the
    hold-queue query below reports 0.167ms execution -- so the wall clock here is
    almost entirely Python and host jitter. Measured on this VPS at idle, a single
    run of the hold-queue benchmark ranged from 15ms to 169ms.

    The ceilings therefore bound *pathological* regressions (a dropped index turning
    a lookup into a multi-second seq scan over a real table), not tens of
    milliseconds. The previous 100ms ceiling sat below the host's own noise floor:
    it failed roughly one run in four at idle, and it false-failed the deploy gate at
    126ms -- blocking every backend deploy for no correctness reason.
    """

    # Wall-clock ceiling for a read benchmark. See the class docstring: this bounds
    # pathology, not latency. Do not tighten it toward the host's noise floor.
    READ_CEILING_MS = 1000

    @pytest.mark.asyncio
    async def test_indexed_query_performance_baseline(self, test_db: AsyncSession):
        """Test that indexed queries perform within acceptable time limits"""
        # Create large dataset
        patron = User(
            email="benchmark@test.com",
            password_hash="hash",
            first_name="Benchmark",
            last_name="User",
            role=UserRole.PATRON,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create 100 checkouts
        for i in range(100):
            item = CatalogItem(title=f"Book {i}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active if i % 2 == 0 else CheckoutStatus.returned,
                checked_out_at=datetime.now() - timedelta(days=i),
                due_date=datetime.now() + timedelta(days=21 - i),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Benchmark query
        start_time = time.perf_counter()

        result = await test_db.execute(
            select(Checkout).where(
                Checkout.user_id == patron.id, Checkout.status == CheckoutStatus.active
            )
        )
        checkouts = result.scalars().all()

        end_time = time.perf_counter()
        query_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert query_time < self.READ_CEILING_MS
        assert len(checkouts) == 50  # Half are active

    @pytest.mark.asyncio
    async def test_overdue_detection_query_performance(self, test_db: AsyncSession):
        """Test that overdue detection queries perform efficiently"""
        # Create large dataset
        patrons = []
        for i in range(10):
            patron = User(
                email=f"patron{i}@perf.com",
                password_hash="hash",
                first_name=f"Patron{i}",
                last_name="User",
                role=UserRole.PATRON,
            )
            test_db.add(patron)
            patrons.append(patron)
        await test_db.commit()

        # Create 200 checkouts with various due dates
        for i in range(200):
            item = CatalogItem(title=f"Book {i}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=patrons[i % 10].id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now() - timedelta(days=i),
                due_date=datetime.now() - timedelta(days=(i - 100)),  # Some overdue
            )
            test_db.add(checkout)
        await test_db.commit()

        # Benchmark overdue query
        start_time = time.perf_counter()

        result = await test_db.execute(
            select(Checkout).where(
                Checkout.due_date < datetime.now(), Checkout.status == CheckoutStatus.active
            )
        )
        overdue = result.scalars().all()

        end_time = time.perf_counter()
        query_time = (end_time - start_time) * 1000

        assert query_time < self.READ_CEILING_MS
        assert len(overdue) > 0

    @pytest.mark.asyncio
    async def test_hold_queue_query_performance(self, test_db: AsyncSession):
        """Test that hold queue queries perform efficiently"""
        # Create item
        item = CatalogItem(title="Very Popular Book", status=ItemStatus.on_hold)
        test_db.add(item)
        await test_db.commit()

        # Create 50 holds
        patrons = []
        for i in range(50):
            patron = User(
                email=f"waitlist{i}@test.com",
                password_hash="hash",
                first_name=f"Wait{i}",
                last_name="List",
                role=UserRole.PATRON,
            )
            test_db.add(patron)
            patrons.append(patron)
        await test_db.commit()

        for i, patron in enumerate(patrons):
            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=i + 1,
            )
            test_db.add(hold)
        await test_db.commit()

        # Benchmark hold queue query
        start_time = time.perf_counter()

        result = await test_db.execute(
            select(Hold)
            .where(Hold.item_id == item.id, Hold.status == HoldStatus.pending)
            .order_by(Hold.position)
        )
        holds = result.scalars().all()

        end_time = time.perf_counter()
        query_time = (end_time - start_time) * 1000

        assert query_time < self.READ_CEILING_MS
        assert len(holds) == 50
        # Verify order
        assert holds[0].position == 1
        assert holds[-1].position == 50


class TestIndexImpactOnWrites:
    """Test that indexes don't significantly slow down write operations"""

    @pytest.mark.asyncio
    async def test_checkout_creation_performance(self, test_db: AsyncSession, test_patron: User):
        """Test that checkout creation is still fast with indexes"""
        # Create items
        items = []
        for i in range(10):
            item = CatalogItem(title=f"Book {i}", status=ItemStatus.available)
            test_db.add(item)
            items.append(item)
        await test_db.commit()

        # Benchmark checkout creation
        start_time = time.perf_counter()

        for item in items:
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        end_time = time.perf_counter()
        write_time = (end_time - start_time) * 1000

        # Writes should still be fast (under 500ms for 10 inserts)
        assert write_time < 500

    @pytest.mark.asyncio
    async def test_hold_creation_performance(self, test_db: AsyncSession):
        """Test that hold creation is still fast with indexes"""
        # Create item
        item = CatalogItem(title="Book", status=ItemStatus.on_hold)
        test_db.add(item)
        await test_db.commit()

        # Create patrons and holds
        start_time = time.perf_counter()

        for i in range(20):
            patron = User(
                email=f"speedtest{i}@test.com",
                password_hash="hash",
                first_name=f"Speed{i}",
                last_name="Test",
                role=UserRole.PATRON,
            )
            test_db.add(patron)
            await test_db.flush()

            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=i + 1,
            )
            test_db.add(hold)

        await test_db.commit()

        end_time = time.perf_counter()
        write_time = (end_time - start_time) * 1000

        # Writes should still be fast (under 1000ms for 20 inserts)
        assert write_time < 1000


class TestPartialIndexes:
    """Test partial/conditional indexes"""

    @pytest.mark.asyncio
    async def test_active_item_checkout_partial_index_exists(self, test_db: AsyncSession):
        """Test that partial unique index on active checkouts exists.

        Uniqueness is enforced per physical copy (ix_active_item_copy_checkout
        on item_copy_id), not per title. The old title-level
        ix_active_item_checkout was deliberately dropped (#1427) since it
        wrongly capped a whole title at one active loan regardless of copy
        count -- see alembic/versions/drop_title_active_idx_001.py.
        """
        # Query database for partial index
        result = await test_db.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'checkouts'
                AND indexname = 'ix_active_item_copy_checkout'
            """)
        )
        index = result.fetchone()

        assert index is not None
        # Should be a partial index with WHERE clause
        assert "WHERE" in index[1].upper() or "where" in index[1]
        assert "status" in index[1]

    @pytest.mark.asyncio
    async def test_active_hold_partial_index_exists(self, test_db: AsyncSession):
        """Test that partial unique index on active holds exists"""
        # Query database for partial index
        result = await test_db.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'holds'
                AND indexname = 'ix_active_user_item_hold'
            """)
        )
        index = result.fetchone()

        assert index is not None
        # Should be a partial index with WHERE clause
        assert "WHERE" in index[1].upper() or "where" in index[1]
        assert "status" in index[1]
