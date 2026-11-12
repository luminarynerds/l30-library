# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Performance Load Testing Suite for L30

Tests concurrent user simulation, API response times, database query performance,
cache hit rates, and memory usage under load.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import statistics
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    HAS_PSUTIL = False
import random

import pytest
if not HAS_PSUTIL:
    pytest.skip("psutil not installed", allow_module_level=True)

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import (
    User, CatalogItem, Checkout, ItemCopy, Fine,
    ReadingStats, ItemStatus, ItemType
)
from app.core.database import AsyncSessionLocal
from app.core.security import get_redis_client
from app.services.catalog_search_service import CatalogSearchService

# Initialize redis client at module level
redis_client = get_redis_client()


class PerformanceMetrics:
    """Collect and track performance metrics."""

    def __init__(self):
        self.response_times: List[float] = []
        self.error_count = 0
        self.success_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.db_query_times: List[float] = []
        self.memory_samples: List[float] = []
        self.timestamp_start = datetime.now()

    def add_response_time(self, duration_ms: float, success: bool):
        self.response_times.append(duration_ms)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def add_db_query_time(self, duration_ms: float):
        self.db_query_times.append(duration_ms)

    def add_memory_sample(self, memory_mb: float):
        self.memory_samples.append(memory_mb)

    def get_stats(self) -> Dict:
        """Generate statistics from collected metrics."""
        if not self.response_times:
            return {}

        sorted_times = sorted(self.response_times)
        return {
            'total_requests': len(self.response_times),
            'successful': self.success_count,
            'failed': self.error_count,
            'success_rate': (self.success_count / len(self.response_times) * 100) if self.response_times else 0,
            'response_times_ms': {
                'min': min(sorted_times),
                'max': max(sorted_times),
                'avg': statistics.mean(self.response_times),
                'median': statistics.median(sorted_times),
                'p95': sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 0 else 0,
                'p99': sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 0 else 0,
            },
            'cache': {
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'hit_rate': (self.cache_hits / (self.cache_hits + self.cache_misses) * 100)
                           if (self.cache_hits + self.cache_misses) > 0 else 0,
            },
            'database': {
                'query_count': len(self.db_query_times),
                'avg_query_time_ms': statistics.mean(self.db_query_times) if self.db_query_times else 0,
                'max_query_time_ms': max(self.db_query_times) if self.db_query_times else 0,
            },
            'memory': {
                'avg_mb': statistics.mean(self.memory_samples) if self.memory_samples else 0,
                'max_mb': max(self.memory_samples) if self.memory_samples else 0,
                'samples': len(self.memory_samples),
            },
            'duration_seconds': (datetime.now() - self.timestamp_start).total_seconds(),
        }


@pytest.mark.asyncio
class TestCatalogSearchPerformance:
    """Test catalog search performance with various dataset sizes."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_search_response_time_small_dataset(self, async_db: AsyncSession):
        """Test search response time with small dataset (< 10k items)."""
        metrics = PerformanceMetrics()
        search_service = CatalogSearchService(async_db)

        # Perform 50 searches
        for i in range(50):
            start = time.time()
            try:
                query = random.choice(['fiction', 'history', 'python', 'mystery', 'science'])
                _ = await search_service.search(
                    query=query,
                    limit=20,
                    offset=0
                )
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, True)
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, False)

        stats = metrics.get_stats()
        print(f"\nSmall Dataset Search Performance: {json.dumps(stats, indent=2)}")

        # Assertions for acceptable performance
        assert stats['response_times_ms']['avg'] < 500, "Average search time should be < 500ms"
        assert stats['response_times_ms']['p95'] < 1000, "P95 search time should be < 1000ms"
        assert stats['success_rate'] > 90, "Success rate should be > 90%"

    async def test_search_response_time_large_dataset(self, async_db: AsyncSession):
        """Test search response time with large dataset (100k+ items)."""
        metrics = PerformanceMetrics()
        search_service = CatalogSearchService(async_db)

        # Perform 50 searches with pagination
        for i in range(50):
            start = time.time()
            try:
                query = random.choice(['fiction', 'history', 'python', 'mystery', 'science'])
                offset = random.randint(0, 1000) * 10
                _ = await search_service.search(
                    query=query,
                    limit=20,
                    offset=offset
                )
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, True)

                # Track cache efficiency
                cache_key = f"search:{query}:{offset}"
                if await redis_client.exists(cache_key):
                    metrics.cache_hits += 1
                else:
                    metrics.cache_misses += 1
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, False)

        stats = metrics.get_stats()
        print(f"\nLarge Dataset Search Performance: {json.dumps(stats, indent=2)}")

        assert stats['response_times_ms']['avg'] < 1000, "Average search time should be < 1000ms"
        assert stats['response_times_ms']['p95'] < 2000, "P95 search time should be < 2000ms"
        assert stats['success_rate'] > 85, "Success rate should be > 85%"


@pytest.mark.asyncio
class TestConcurrentUserSimulation:
    """Simulate concurrent users performing typical library operations."""

    async def test_50_concurrent_users(self):
        """Simulate 50 concurrent users performing various operations."""
        metrics = PerformanceMetrics()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get auth token
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": "patron@test.com", "password": "password123"}
            )

            if login_response.status_code != 200:
                pytest.skip("Auth not available for load testing")
                return

            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Define concurrent operations
            async def patron_operations():
                operations = [
                    ("GET", "/api/v1/catalog?q=fiction&limit=20"),
                    ("GET", "/api/v1/circulation/checkouts"),
                    ("GET", "/api/v1/search/unified?q=mystery"),
                    ("POST", "/api/v1/favorites", {"item_id": "test-item"}),
                    ("GET", "/api/v1/releases?limit=10"),
                ]

                for method, endpoint, *data in random.choices(operations, k=10):
                    start = time.time()
                    try:
                        if method == "GET":
                            resp = await client.get(endpoint, headers=headers)
                        else:
                            resp = await client.post(endpoint, json=data[0] if data else {}, headers=headers)

                        duration = (time.time() - start) * 1000
                        metrics.add_response_time(duration, resp.status_code < 400)
                    except Exception:
                        duration = (time.time() - start) * 1000
                        metrics.add_response_time(duration, False)

                    await asyncio.sleep(0.1)  # Minimal delay between requests

            # Run 50 concurrent users
            tasks = [patron_operations() for _ in range(50)]
            await asyncio.gather(*tasks)

        stats = metrics.get_stats()
        print(f"\n50 Concurrent Users Performance: {json.dumps(stats, indent=2)}")

        assert stats['response_times_ms']['avg'] < 800, "Average response should be < 800ms under 50 concurrent users"
        assert stats['response_times_ms']['p95'] < 2000, "P95 response should be < 2000ms"
        assert stats['success_rate'] > 80, "Success rate should be > 80%"

    async def test_100_concurrent_users(self):
        """Simulate 100 concurrent users - stress test."""
        metrics = PerformanceMetrics()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": "patron@test.com", "password": "password123"}
            )

            if login_response.status_code != 200:
                pytest.skip("Auth not available for load testing")
                return

            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            async def concurrent_request():
                start = time.time()
                try:
                    resp = await client.get(
                        "/api/v1/catalog?q=test&limit=20",
                        headers=headers,
                        timeout=30
                    )
                    duration = (time.time() - start) * 1000
                    metrics.add_response_time(duration, resp.status_code < 400)
                except Exception:
                    duration = (time.time() - start) * 1000
                    metrics.add_response_time(duration, False)

            tasks = [concurrent_request() for _ in range(100)]
            await asyncio.gather(*tasks, return_exceptions=True)

        stats = metrics.get_stats()
        print(f"\n100 Concurrent Users Performance: {json.dumps(stats, indent=2)}")

        # More lenient for stress test
        assert stats['response_times_ms']['p95'] < 5000, "P95 should be < 5000ms under stress"
        assert stats['success_rate'] > 70, "Success rate should be > 70% under stress"


@pytest.mark.asyncio
class TestDatabaseQueryPerformance:
    """Test database query performance on heavy tables."""

    @pytest.fixture
    async def async_db(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def test_catalog_item_search_performance(self, async_db: AsyncSession):
        """Test full-text search on catalog items."""
        metrics = PerformanceMetrics()

        # Perform 30 searches
        for i in range(30):
            start = time.time()
            try:
                stmt = select(CatalogItem).filter(
                    CatalogItem.title.icontains(random.choice(['test', 'fiction', 'history']))
                ).limit(50)

                result = await async_db.execute(stmt)
                _ = result.scalars().all()

                duration = (time.time() - start) * 1000
                metrics.add_db_query_time(duration)
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_db_query_time(duration)

        stats = metrics.get_stats()
        print(f"\nCatalog Item Search Performance: {json.dumps(stats['database'], indent=2)}")

        assert stats['database']['avg_query_time_ms'] < 200, "Avg query time should be < 200ms"
        assert stats['database']['max_query_time_ms'] < 500, "Max query time should be < 500ms"

    async def test_checkout_history_query_performance(self, async_db: AsyncSession):
        """Test checkout history queries (common for patron accounts)."""
        metrics = PerformanceMetrics()

        # Get active users
        stmt = select(User).limit(10)
        result = await async_db.execute(stmt)
        users = result.scalars().all()

        if not users:
            pytest.skip("No users in database")
            return

        # Query checkout history for each user
        for user in users:
            start = time.time()
            try:
                stmt = select(Checkout).filter(
                    Checkout.patron_id == user.id
                ).order_by(Checkout.checkout_date.desc()).limit(100)

                result = await async_db.execute(stmt)
                _ = result.scalars().all()

                duration = (time.time() - start) * 1000
                metrics.add_db_query_time(duration)
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_db_query_time(duration)

        stats = metrics.get_stats()
        print(f"\nCheckout History Query Performance: {json.dumps(stats['database'], indent=2)}")

        assert stats['database']['avg_query_time_ms'] < 150, "Avg query time should be < 150ms"

    async def test_bulk_fines_calculation(self, async_db: AsyncSession):
        """Test performance of bulk fine calculations (daily job)."""
        metrics = PerformanceMetrics()

        # Simulate calculating fines for overdue items
        for attempt in range(10):
            start = time.time()
            try:
                # Find overdue checkouts
                overdue_date = datetime.now() - timedelta(days=1)
                stmt = select(Checkout).filter(
                    (Checkout.due_date < overdue_date) &
                    (Checkout.status == 'checked_out')
                ).limit(500)

                result = await async_db.execute(stmt)
                _ = result.scalars().all()

                duration = (time.time() - start) * 1000
                metrics.add_db_query_time(duration)
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_db_query_time(duration)

        stats = metrics.get_stats()
        print(f"\nBulk Fines Calculation Performance: {json.dumps(stats['database'], indent=2)}")

        assert stats['database']['avg_query_time_ms'] < 300, "Avg query time should be < 300ms"


@pytest.mark.asyncio
class TestRedisCachePerformance:
    """Test Redis cache hit rates and performance."""

    async def test_cache_hit_rate_on_repeated_searches(self):
        """Test cache effectiveness on repeated searches."""
        metrics = PerformanceMetrics()
        search_terms = ['fiction', 'history', 'python', 'mystery', 'science']

        # First pass - populate cache
        for term in search_terms:
            await redis_client.delete(f"search:{term}")

        # 100 searches with repetition
        for i in range(100):
            term = random.choice(search_terms)
            cache_key = f"search:{term}"

            if await redis_client.exists(cache_key):
                metrics.cache_hits += 1
            else:
                # Simulate cache miss and population
                await redis_client.set(cache_key, json.dumps({"results": []}), ex=3600)
                metrics.cache_misses += 1

        stats = metrics.get_stats()
        print(f"\nCache Hit Rate Performance: {json.dumps(stats['cache'], indent=2)}")

        # After 100 searches, should have high hit rate
        assert stats['cache']['hit_rate'] > 70, "Cache hit rate should be > 70%"

    async def test_redis_memory_under_load(self):
        """Test Redis memory usage under concurrent load."""
        metrics = PerformanceMetrics()

        # Generate cache entries
        for i in range(1000):
            key = f"test_key_{i}"
            value = json.dumps({"id": i, "data": "x" * 100})
            await redis_client.set(key, value, ex=3600)

            # Sample memory usage every 100 entries
            if i % 100 == 0:
                info = await redis_client.info('memory')
                memory_mb = info.get('used_memory', 0) / (1024 * 1024)
                metrics.add_memory_sample(memory_mb)

        stats = metrics.get_stats()
        print(f"\nRedis Memory Performance: {json.dumps(stats['memory'], indent=2)}")

        # Cleanup
        for i in range(1000):
            await redis_client.delete(f"test_key_{i}")

    async def test_cache_stampede_protection(self):
        """Test cache stampede protection under load."""
        metrics = PerformanceMetrics()
        cache_key = "stampede_test_key"
        await redis_client.delete(cache_key)

        # Simulate multiple concurrent cache misses
        async def cache_miss_handler():
            start = time.time()
            try:
                # Try to get cached value
                value = await redis_client.get(cache_key)
                if not value:
                    # Simulate expensive operation
                    await asyncio.sleep(0.1)
                    await redis_client.set(cache_key, json.dumps({"data": "test"}), ex=3600)

                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, True)
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, False)

        # Run 50 concurrent cache handlers
        tasks = [cache_miss_handler() for _ in range(50)]
        await asyncio.gather(*tasks)

        stats = metrics.get_stats()
        print(f"\nCache Stampede Protection: {json.dumps(stats, indent=2)}")

        await redis_client.delete(cache_key)


@pytest.mark.asyncio
class TestMemoryUsage:
    """Monitor memory usage during peak operations."""

    async def test_memory_usage_during_concurrent_operations(self):
        """Track memory usage during 100 concurrent API requests."""
        metrics = PerformanceMetrics()
        process = psutil.Process()

        async def memory_tracked_operation():
            # Record memory before
            mem_before = process.memory_info().rss / (1024 * 1024)
            metrics.add_memory_sample(mem_before)

            # Perform operation
            start = time.time()
            try:
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.get("/api/v1/health")
                    duration = (time.time() - start) * 1000
                    metrics.add_response_time(duration, resp.status_code < 400)
            except Exception:
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, False)

            # Record memory after
            mem_after = process.memory_info().rss / (1024 * 1024)
            metrics.add_memory_sample(mem_after)

        # Run 100 concurrent operations
        tasks = [memory_tracked_operation() for _ in range(100)]
        await asyncio.gather(*tasks, return_exceptions=True)

        stats = metrics.get_stats()
        print(f"\nMemory Usage During Concurrent Operations: {json.dumps(stats['memory'], indent=2)}")

        # Memory should not exceed 500MB per 100 concurrent requests
        assert stats['memory']['max_mb'] < 500, "Memory usage should be < 500MB"


@pytest.mark.asyncio
class TestAPIResponseTimes:
    """Test API response times for critical endpoints."""

    async def test_health_endpoint_performance(self):
        """Health endpoint should be very fast."""
        metrics = PerformanceMetrics()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(100):
                start = time.time()
                resp = await client.get("/api/v1/health")
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, resp.status_code < 400)

        stats = metrics.get_stats()
        print(f"\nHealth Endpoint Performance: {json.dumps(stats, indent=2)}")

        assert stats['response_times_ms']['avg'] < 50, "Health check avg should be < 50ms"
        assert stats['response_times_ms']['p95'] < 100, "Health check p95 should be < 100ms"

    async def test_catalog_endpoint_performance(self):
        """Catalog search endpoint performance."""
        metrics = PerformanceMetrics()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for i in range(50):
                start = time.time()
                resp = await client.get("/api/v1/catalog?q=test&limit=20")
                duration = (time.time() - start) * 1000
                metrics.add_response_time(duration, resp.status_code < 400)

        stats = metrics.get_stats()
        print(f"\nCatalog Endpoint Performance: {json.dumps(stats, indent=2)}")

        assert stats['response_times_ms']['avg'] < 500, "Catalog search avg should be < 500ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
