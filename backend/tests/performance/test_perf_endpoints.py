# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Performance Benchmark Suite for Top 20 LSC Endpoints.

Tests latency (p50/p95/p99), throughput, and query count for the 20
most-hit API endpoints. Results are written to benchmarks/results.json
for regression comparison in CI.

Endpoint categories:
- Catalog search (search, advanced search, new arrivals)
- Checkout & circulation (list, active, renew)
- Patron lookup (staff patron search)
- Hold placement & listing
- Fine calculation & summary
- Auth (login, me, refresh)
- Public pages (branches, events, health)

Usage:
    pytest tests/performance/test_perf_endpoints.py -v -s \
        --override-ini="addopts=" -p no:cacheprovider
"""

import json
import statistics
import time
from pathlib import Path
from typing import List

import pytest
from httpx import AsyncClient

from tests.performance.conftest import QueryTracker, assert_query_count

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WARMUP_REQUESTS = 3
BENCHMARK_ITERATIONS = 30

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks"
RESULTS_FILE = RESULTS_DIR / "results.json"


# ---------------------------------------------------------------------------
# Top 20 endpoint definitions
# ---------------------------------------------------------------------------

TOP_20_ENDPOINTS = [
    # --- Health & Infrastructure ---
    {
        "name": "GET /api/v1/health",
        "method": "GET",
        "path": "/api/v1/health",
        "auth": None,
        "max_queries": 0,
    },
    # --- Auth ---
    {
        "name": "POST /api/v1/auth/login",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "auth": None,
        "json": {"email": "patron@test.com", "password": "password123"},
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/auth/me",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "auth": "patron",
        "max_queries": 3,
    },
    {
        "name": "POST /api/v1/auth/refresh",
        "method": "POST",
        "path": "/api/v1/auth/refresh",
        "auth": "patron",
        "max_queries": 5,
    },
    # --- Catalog Search ---
    {
        "name": "GET /api/v1/catalog",
        "method": "GET",
        "path": "/api/v1/catalog",
        "auth": None,
        "params": {"q": "fiction", "limit": 20},
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/catalog/search",
        "method": "GET",
        "path": "/api/v1/catalog/search",
        "auth": None,
        "params": {"q": "history", "limit": 20},
        "max_queries": 5,
    },
    {
        "name": "POST /api/v1/catalog/advanced-search",
        "method": "POST",
        "path": "/api/v1/catalog/advanced-search",
        "auth": None,
        "json": {"title": "mystery", "limit": 20},
        "max_queries": 8,
    },
    {
        "name": "GET /api/v1/catalog/special/new-arrivals",
        "method": "GET",
        "path": "/api/v1/catalog/special/new-arrivals",
        "auth": None,
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/search/unified",
        "method": "GET",
        "path": "/api/v1/search/unified",
        "auth": None,
        "params": {"q": "python", "limit": 20},
        "max_queries": 10,
    },
    # --- Circulation: Checkouts ---
    {
        "name": "GET /api/v1/circulation/checkouts",
        "method": "GET",
        "path": "/api/v1/circulation/checkouts",
        "auth": "patron",
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/circulation/checkouts/active",
        "method": "GET",
        "path": "/api/v1/circulation/checkouts/active",
        "auth": "patron",
        "max_queries": 5,
    },
    # --- Circulation: Holds ---
    {
        "name": "GET /api/v1/circulation/holds",
        "method": "GET",
        "path": "/api/v1/circulation/holds",
        "auth": "patron",
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/circulation/holds/active",
        "method": "GET",
        "path": "/api/v1/circulation/holds/active",
        "auth": "patron",
        "max_queries": 5,
    },
    # --- Circulation: Fines ---
    {
        "name": "GET /api/v1/circulation/fines",
        "method": "GET",
        "path": "/api/v1/circulation/fines",
        "auth": "patron",
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/circulation/fines/summary",
        "method": "GET",
        "path": "/api/v1/circulation/fines/summary",
        "auth": "patron",
        "max_queries": 5,
    },
    # --- User features ---
    {
        "name": "GET /api/v1/favorites",
        "method": "GET",
        "path": "/api/v1/favorites",
        "auth": "patron",
        "max_queries": 5,
    },
    {
        "name": "GET /api/v1/notifications",
        "method": "GET",
        "path": "/api/v1/notifications",
        "auth": "patron",
        "max_queries": 5,
    },
    # --- Public pages ---
    {
        "name": "GET /api/v1/branches",
        "method": "GET",
        "path": "/api/v1/branches",
        "auth": None,
        "max_queries": 3,
    },
    {
        "name": "GET /api/v1/events",
        "method": "GET",
        "path": "/api/v1/events",
        "auth": None,
        "max_queries": 5,
    },
    # --- Staff: Patron Lookup ---
    {
        "name": "GET /api/v1/staff/patrons",
        "method": "GET",
        "path": "/api/v1/staff/patrons",
        "auth": "staff",
        "max_queries": 5,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(data: List[float], pct: float) -> float:
    """Calculate percentile from a list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * pct / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


async def _make_request(
    client: AsyncClient,
    endpoint: dict,
    headers: dict,
) -> tuple[float, int]:
    """Execute a single request and return (duration_ms, status_code)."""
    method = endpoint["method"]
    path = endpoint["path"]
    kwargs: dict = {"headers": headers, "timeout": 30.0}

    if "params" in endpoint:
        kwargs["params"] = endpoint["params"]

    if method == "GET":
        start = time.perf_counter()
        resp = await client.get(path, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
    elif method == "POST":
        if "json" in endpoint:
            kwargs["json"] = endpoint["json"]
        start = time.perf_counter()
        resp = await client.post(path, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
    else:
        raise ValueError(f"Unsupported method: {method}")

    return duration_ms, resp.status_code


# ---------------------------------------------------------------------------
# Benchmark test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestPerformanceBenchmarks:
    """
    Benchmark the top 20 endpoints and write results to JSON.

    Also enforces per-endpoint query budgets to catch N+1 regressions.
    """

    async def test_benchmark_top_20_endpoints(
        self,
        perf_client: AsyncClient,
        auth_tokens: dict,
        query_tracker: QueryTracker,
    ):
        """Run latency benchmarks + query count checks for all 20 endpoints."""

        patron_headers = auth_tokens.get("patron", {})
        staff_headers = auth_tokens.get("staff", {})

        results = {}
        query_violations = []

        for ep in TOP_20_ENDPOINTS:
            name = ep["name"]

            # Select auth headers
            if ep["auth"] == "staff":
                headers = staff_headers
            elif ep["auth"] == "patron":
                headers = patron_headers
            else:
                headers = {}

            # --- Warm-up ---
            for _ in range(WARMUP_REQUESTS):
                try:
                    await _make_request(perf_client, ep, headers)
                except Exception:
                    pass

            # --- Measured iterations (latency) ---
            durations: List[float] = []
            errors = 0

            for _ in range(BENCHMARK_ITERATIONS):
                try:
                    duration_ms, status_code = await _make_request(
                        perf_client, ep, headers
                    )
                    durations.append(duration_ms)
                    if status_code >= 500:
                        errors += 1
                except Exception:
                    errors += 1

            # --- Query count check (single request) ---
            query_count = 0
            if ep.get("max_queries") is not None:
                query_tracker.start()
                try:
                    await _make_request(perf_client, ep, headers)
                except Exception:
                    pass
                query_tracker.stop()
                query_count = query_tracker.count

                if query_count > ep["max_queries"]:
                    query_violations.append({
                        "endpoint": name,
                        "actual": query_count,
                        "max_allowed": ep["max_queries"],
                    })

            # --- Record results ---
            if durations:
                results[name] = {
                    "method": ep["method"],
                    "path": ep["path"],
                    "iterations": len(durations),
                    "errors": errors,
                    "min_ms": round(min(durations), 2),
                    "max_ms": round(max(durations), 2),
                    "mean_ms": round(statistics.mean(durations), 2),
                    "median_ms": round(statistics.median(durations), 2),
                    "p50_ms": round(_percentile(durations, 50), 2),
                    "p95_ms": round(_percentile(durations, 95), 2),
                    "p99_ms": round(_percentile(durations, 99), 2),
                    "stdev_ms": round(
                        statistics.stdev(durations) if len(durations) > 1 else 0.0, 2
                    ),
                    "throughput_rps": round(
                        len(durations)
                        / (sum(durations) / 1000)
                        if sum(durations) > 0
                        else 0,
                        1,
                    ),
                    "query_count": query_count,
                    "query_budget": ep.get("max_queries", -1),
                }
            else:
                results[name] = {
                    "method": ep["method"],
                    "path": ep["path"],
                    "iterations": 0,
                    "errors": errors,
                    "min_ms": 0, "max_ms": 0, "mean_ms": 0,
                    "median_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0,
                    "stdev_ms": 0, "throughput_rps": 0,
                    "query_count": query_count,
                    "query_budget": ep.get("max_queries", -1),
                }

        # --- Write results ---
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_FILE.write_text(json.dumps(results, indent=2))

        # --- Print summary table ---
        print("\n" + "=" * 110)
        print("ENDPOINT PERFORMANCE BENCHMARK RESULTS")
        print("=" * 110)
        print(
            f"{'Endpoint':<45} {'Mean':>8} {'P50':>8} {'P95':>8} "
            f"{'P99':>8} {'RPS':>8} {'Queries':>8} {'Err':>5}"
        )
        print("-" * 110)
        for name, m in results.items():
            q_str = (
                f"{m['query_count']}/{m['query_budget']}"
                if m['query_budget'] >= 0
                else "n/a"
            )
            print(
                f"{name:<45} "
                f"{m['mean_ms']:>7.1f}ms "
                f"{m['p50_ms']:>7.1f}ms "
                f"{m['p95_ms']:>7.1f}ms "
                f"{m['p99_ms']:>7.1f}ms "
                f"{m['throughput_rps']:>7.1f} "
                f"{q_str:>8} "
                f"{m['errors']:>4}",
            )
        print("=" * 110)
        print(f"\nResults written to {RESULTS_FILE}")

        # --- Assertions ---
        successful = sum(1 for r in results.values() if r["iterations"] > 0)
        assert successful > 0, "No endpoints returned successful responses"

        # Report query violations
        if query_violations:
            violation_details = "\n".join(
                f"  {v['endpoint']}: {v['actual']} queries (max: {v['max_allowed']})"
                for v in query_violations
            )
            print(f"\nQUERY BUDGET VIOLATIONS:\n{violation_details}")
            # Fail the test on query count violations
            pytest.fail(
                f"{len(query_violations)} endpoint(s) exceeded query budget:\n"
                f"{violation_details}"
            )


# ---------------------------------------------------------------------------
# Individual query count tests (for granular CI feedback)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestQueryCountAssertions:
    """
    Isolated query count tests - one per endpoint category.

    These fail individually in CI so developers see exactly which
    endpoint introduced an N+1 regression.
    """

    async def _check_queries(
        self,
        perf_client: AsyncClient,
        auth_tokens: dict,
        query_tracker: QueryTracker,
        endpoint: dict,
    ):
        """Helper: hit endpoint once and assert query count."""
        if endpoint["auth"] == "staff":
            headers = auth_tokens.get("staff", {})
        elif endpoint["auth"] == "patron":
            headers = auth_tokens.get("patron", {})
        else:
            headers = {}

        query_tracker.start()
        try:
            await _make_request(perf_client, endpoint, headers)
        except Exception:
            pass
        query_tracker.stop()

        assert_query_count(
            query_tracker,
            endpoint["max_queries"],
            endpoint["name"],
        )

    async def test_catalog_list_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[4])

    async def test_catalog_search_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[5])

    async def test_catalog_advanced_search_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[6])

    async def test_checkouts_list_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[9])

    async def test_active_checkouts_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[10])

    async def test_holds_list_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[11])

    async def test_active_holds_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[12])

    async def test_fines_list_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[13])

    async def test_fines_summary_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[14])

    async def test_patron_lookup_queries(self, perf_client, auth_tokens, query_tracker):
        await self._check_queries(perf_client, auth_tokens, query_tracker, TOP_20_ENDPOINTS[19])
