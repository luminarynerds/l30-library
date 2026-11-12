# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Database Performance Testing Suite

Tests query performance on heavy tables, indexes, and optimization opportunities.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import statistics

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, CatalogItem, Checkout, ItemCopy, Fine, Hold,
    ReadingStats, Event, AuditLog, ItemStatus
)
from app.core.database import AsyncSessionLocal


class DatabasePerformanceAnalyzer:
    """Analyze database query performance."""

    def __init__(self):
        self.queries: List[Dict] = []

    def record_query(self, name: str, duration_ms: float, rows_affected: int = 0):
        """Record a query execution."""
        self.queries.append({
            'name': name,
            'duration_ms': duration_ms,
            'rows_affected': rows_affected,
            'timestamp': datetime.now().isoformat()
        })

    def get_summary(self) -> Dict:
        """Get performance summary."""
        if not self.queries:
            return {}

        durations = [q['duration_ms'] for q in self.queries]
        return {
            'total_queries': len(self.queries),
            'total_duration_ms': sum(durations),
            'avg_duration_ms': statistics.mean(durations),
            'median_duration_ms': statistics.median(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'p95_duration_ms': sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            'p99_duration_ms': sorted(durations)[int(len(durations) * 0.99)] if durations else 0,
            'queries_over_100ms': sum(1 for d in durations if d > 100),
            'queries_over_500ms': sum(1 for d in durations if d > 500),
        }

    def print_report(self):
        """Print detailed performance report."""
        summary = self.get_summary()
        print("\nDatabase Performance Summary:")
        print(json.dumps(summary, indent=2))

        # Group by query type
        print("\nPer-Query Performance:")
        by_name = {}
        for query in self.queries:
            if query['name'] not in by_name:
                by_name[query['name']] = []
            by_name[query['name']].append(query['duration_ms'])

        for name in sorted(by_name.keys()):
            times = by_name[name]
            print(f"  {name}: avg={statistics.mean(times):.2f}ms, max={max(times):.2f}ms, count={len(times)}")


@pytest.mark.asyncio
class TestCatalogIndexPerformance:
    """Test catalog table query performance and index effectiveness."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_title_search_performance(self, async_db: AsyncSession):
        """Test title search index usage."""
        analyzer = DatabasePerformanceAnalyzer()

        search_terms = ['test', 'fiction', 'history', 'mystery', 'science', 'adventure']

        for term in search_terms:
            for _ in range(10):
                start = time.time()
                try:
                    stmt = select(CatalogItem).filter(
                        CatalogItem.title.ilike(f"%{term}%")
                    ).limit(50)

                    result = await async_db.execute(stmt)
                    items = result.scalars().all()

                    duration = (time.time() - start) * 1000
                    analyzer.record_query(f"title_search_{term}", duration, len(items))
                except Exception as e:
                    print(f"Error: {e}")

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 200, "Title search should average < 200ms"
        assert summary['queries_over_500ms'] < 5, "Should have < 5 queries over 500ms"

    async def test_isbn_lookup_performance(self, async_db: AsyncSession):
        """Test ISBN lookup performance (should be very fast with index)."""
        analyzer = DatabasePerformanceAnalyzer()

        # Get some real ISBNs
        stmt = select(CatalogItem.isbn).filter(CatalogItem.isbn.isnot(None)).limit(10)
        result = await async_db.execute(stmt)
        isbns = result.scalars().all()

        if not isbns:
            pytest.skip("No ISBNs in database")
            return

        # Test ISBN lookups
        for isbn in isbns:
            for _ in range(5):
                start = time.time()
                stmt = select(CatalogItem).filter(CatalogItem.isbn == isbn)
                result = await async_db.execute(stmt)
                item = result.scalar_one_or_none()

                duration = (time.time() - start) * 1000
                analyzer.record_query("isbn_lookup", duration, 1 if item else 0)

        analyzer.print_report()
        summary = analyzer.get_summary()

        # ISBN lookups should be very fast (< 50ms avg)
        assert summary['avg_duration_ms'] < 50, "ISBN lookup should be < 50ms"

    async def test_author_filtering_performance(self, async_db: AsyncSession):
        """Test author-based filtering."""
        analyzer = DatabasePerformanceAnalyzer()

        authors = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones']

        for author in authors:
            for _ in range(5):
                start = time.time()
                stmt = select(CatalogItem).filter(
                    CatalogItem.author.ilike(f"%{author}%")
                ).limit(100)

                result = await async_db.execute(stmt)
                items = result.scalars().all()

                duration = (time.time() - start) * 1000
                analyzer.record_query(f"author_filter_{author}", duration, len(items))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 300, "Author filtering should average < 300ms"


@pytest.mark.asyncio
class TestCirculationQueryPerformance:
    """Test checkout and circulation query performance."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_patron_checkout_history(self, async_db: AsyncSession):
        """Test fetching patron checkout history."""
        analyzer = DatabasePerformanceAnalyzer()

        # Get active patrons
        stmt = select(User).limit(20)
        result = await async_db.execute(stmt)
        patrons = result.scalars().all()

        if not patrons:
            pytest.skip("No patrons in database")
            return

        for patron in patrons:
            start = time.time()
            stmt = select(Checkout).filter(
                Checkout.user_id == patron.id
            ).order_by(Checkout.checked_out_at.desc()).limit(100)

            result = await async_db.execute(stmt)
            checkouts = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("patron_checkout_history", duration, len(checkouts))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 150, "Checkout history should average < 150ms"

    async def test_active_checkouts_query(self, async_db: AsyncSession):
        """Test finding active checkouts (status = 'active')."""
        analyzer = DatabasePerformanceAnalyzer()

        for _ in range(20):
            start = time.time()
            stmt = select(Checkout).filter(
                Checkout.status == 'active'
            ).limit(1000)

            result = await async_db.execute(stmt)
            checkouts = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("active_checkouts", duration, len(checkouts))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 200, "Active checkouts query should average < 200ms"

    async def test_overdue_items_detection(self, async_db: AsyncSession):
        """Test finding overdue items (daily job)."""
        analyzer = DatabasePerformanceAnalyzer()

        for _ in range(10):
            start = time.time()
            overdue_date = datetime.now() - timedelta(days=1)

            stmt = select(Checkout).filter(
                (Checkout.status == 'active') &
                (Checkout.due_date < overdue_date)
            ).limit(5000)

            result = await async_db.execute(stmt)
            overdue = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("overdue_detection", duration, len(overdue))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 300, "Overdue detection should average < 300ms"

    async def test_hold_queue_performance(self, async_db: AsyncSession):
        """Test hold queue queries."""
        analyzer = DatabasePerformanceAnalyzer()

        # Get items with holds
        stmt = select(Hold.item_id).distinct().limit(20)
        result = await async_db.execute(stmt)
        item_ids = result.scalars().all()

        if not item_ids:
            pytest.skip("No holds in database")
            return

        for item_id in item_ids:
            start = time.time()
            stmt = select(Hold).filter(
                (Hold.item_id == item_id) &
                (Hold.status == 'pending')
            ).order_by(Hold.created_at.asc())

            result = await async_db.execute(stmt)
            holds = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("hold_queue", duration, len(holds))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 100, "Hold queue query should average < 100ms"


@pytest.mark.asyncio
class TestAggregationQueryPerformance:
    """Test performance of aggregation queries (analytics, reports)."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_checkout_statistics(self, async_db: AsyncSession):
        """Test checkout statistics calculation."""
        analyzer = DatabasePerformanceAnalyzer()

        for _ in range(5):
            start = time.time()

            # Total checkouts
            stmt = select(func.count(Checkout.id))
            result = await async_db.execute(stmt)
            _ = result.scalar()

            # Checkouts by item type
            stmt = select(
                CatalogItem.item_type,
                func.count(Checkout.id)
            ).join(
                CatalogItem, Checkout.item_id == CatalogItem.id
            ).group_by(CatalogItem.item_type)

            result = await async_db.execute(stmt)
            _ = result.all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("checkout_statistics", duration)

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 500, "Checkout statistics should average < 500ms"

    async def test_patron_activity_report(self, async_db: AsyncSession):
        """Test patron activity reporting."""
        analyzer = DatabasePerformanceAnalyzer()

        for _ in range(5):
            start = time.time()

            # Active patrons in last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)

            stmt = select(
                User.id,
                func.count(Checkout.id).label('checkout_count'),
                func.count(Hold.id).label('hold_count')
            ).outerjoin(
                Checkout, User.id == Checkout.user_id
            ).outerjoin(
                Hold, User.id == Hold.user_id
            ).filter(
                (Checkout.checked_out_at >= thirty_days_ago) |
                (Hold.created_at >= thirty_days_ago)
            ).group_by(User.id).limit(1000)

            result = await async_db.execute(stmt)
            active_patrons = result.all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("patron_activity_report", duration, len(active_patrons))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 1000, "Patron activity report should average < 1000ms"

    async def test_fine_revenue_report(self, async_db: AsyncSession):
        """Test fine revenue calculations."""
        analyzer = DatabasePerformanceAnalyzer()

        for _ in range(5):
            start = time.time()

            # Total fines by date
            stmt = select(
                func.date(Fine.created_at).label('date'),
                func.sum(Fine.amount).label('total')
            ).group_by(
                func.date(Fine.created_at)
            ).order_by(
                func.date(Fine.created_at).desc()
            ).limit(30)

            result = await async_db.execute(stmt)
            revenue = result.all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("fine_revenue_report", duration, len(revenue))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 300, "Fine revenue report should average < 300ms"


@pytest.mark.asyncio
class TestJoinPerformance:
    """Test performance of complex joins."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_item_with_copies_and_checkouts(self, async_db: AsyncSession):
        """Test fetching items with their copies and checkout history."""
        analyzer = DatabasePerformanceAnalyzer()

        # Get some catalog items
        stmt = select(CatalogItem).limit(20)
        result = await async_db.execute(stmt)
        items = result.scalars().all()

        if not items:
            pytest.skip("No items in database")
            return

        for item in items:
            start = time.time()

            # Get copies for item
            stmt = select(ItemCopy).filter(ItemCopy.item_id == item.id)
            result = await async_db.execute(stmt)
            copies = result.scalars().all()

            # Get checkout history
            stmt = select(Checkout).filter(Checkout.item_id == item.id).limit(100)
            result = await async_db.execute(stmt)
            checkouts = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("item_copies_checkouts", duration, len(copies) + len(checkouts))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 200, "Item with copies should average < 200ms"

    async def test_patron_with_checkouts_holds_fines(self, async_db: AsyncSession):
        """Test fetching patron with all related data."""
        analyzer = DatabasePerformanceAnalyzer()

        # Get some patrons
        stmt = select(User).limit(20)
        result = await async_db.execute(stmt)
        patrons = result.scalars().all()

        if not patrons:
            pytest.skip("No patrons in database")
            return

        for patron in patrons:
            start = time.time()

            # Get checkouts
            stmt = select(Checkout).filter(Checkout.user_id == patron.id).limit(100)
            result = await async_db.execute(stmt)
            checkouts = result.scalars().all()

            # Get holds
            stmt = select(Hold).filter(Hold.user_id == patron.id)
            result = await async_db.execute(stmt)
            holds = result.scalars().all()

            # Get fines
            stmt = select(Fine).filter(Fine.user_id == patron.id).limit(50)
            result = await async_db.execute(stmt)
            fines = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query("patron_full_data", duration, len(checkouts) + len(holds) + len(fines))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 300, "Patron full data should average < 300ms"


@pytest.mark.asyncio
class TestIndexEffectiveness:
    """Test index effectiveness and identify missing indexes."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_check_index_usage(self, async_db: AsyncSession):
        """Check if indexes are being used effectively."""
        # Note: This test requires database explain plan support
        _ = DatabasePerformanceAnalyzer()

        print("\n\nIndex Effectiveness Check:")
        print("="*80)

        # Common queries that should use indexes
        queries = [
            ("SELECT * FROM catalog_items WHERE isbn = ?", "isbn index"),
            ("SELECT * FROM checkouts WHERE user_id = ? AND status = ?", "patron_status index"),
            ("SELECT * FROM catalog_items WHERE title ILIKE ?", "title index"),
            ("SELECT * FROM checkouts WHERE due_date < ? AND status = ?", "due_date_status index"),
        ]

        for query_text, index_name in queries:
            print(f"\nQuery: {index_name}")
            try:
                modified_query = query_text.replace('?', "'test'")
                stmt = text(f"EXPLAIN (ANALYZE, BUFFERS) {modified_query}")
                result = await async_db.execute(stmt)
                lines = result.all()

                print("Execution Plan:")
                for line in lines:
                    print(f"  {line[0]}")
            except Exception as e:
                print(f"  Error running EXPLAIN: {e}")

        print("\n" + "="*80)


@pytest.mark.asyncio
class TestBulkOperationPerformance:
    """Test performance of bulk operations."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_bulk_fine_generation(self, async_db: AsyncSession):
        """Test bulk fine generation performance."""
        analyzer = DatabasePerformanceAnalyzer()

        # Simulate daily fine generation job
        for day in range(5):
            start = time.time()

            overdue_date = datetime.now() - timedelta(days=day)

            # Find overdue checkouts
            stmt = select(Checkout).filter(
                (Checkout.status == 'active') &
                (Checkout.due_date < overdue_date)
            ).limit(1000)

            result = await async_db.execute(stmt)
            overdue_checkouts = result.scalars().all()

            duration = (time.time() - start) * 1000
            analyzer.record_query(f"bulk_fine_generation_day_{day}", duration, len(overdue_checkouts))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 500, "Bulk fine generation should average < 500ms"

    async def test_batch_update_performance(self, async_db: AsyncSession):
        """Test batch update performance."""
        analyzer = DatabasePerformanceAnalyzer()

        # Get items to update
        stmt = select(CatalogItem).limit(100)
        result = await async_db.execute(stmt)
        items = result.scalars().all()

        if len(items) < 10:
            pytest.skip("Not enough items for batch test")
            return

        # Test batch update
        start = time.time()
        for item in items[:10]:
            item.last_reviewed = datetime.now()

        await async_db.flush()
        duration = (time.time() - start) * 1000
        analyzer.record_query("batch_update_items", duration, len(items[:10]))

        analyzer.print_report()
        summary = analyzer.get_summary()

        assert summary['avg_duration_ms'] < 200, "Batch updates should be efficient"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
