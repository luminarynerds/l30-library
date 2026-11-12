# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Performance Benchmark Suite for Top 20 LSC Endpoints

Measures p50/p95/p99 latencies for the 20 most critical API endpoints.
Results are written to a JSON file for regression comparison in CI.

Usage:
    pytest tests/test_benchmark_endpoints.py -v -s --benchmark-output=benchmarks/results.json

The CI workflow compares results against benchmarks/baseline.json and
fails the PR if any endpoint regresses by more than 20%.
"""

import json
import os
import statistics
import time
from pathlib import Path
from typing import Dict, List

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WARMUP_REQUESTS = 3  # Warm up each endpoint before measuring
BENCHMARK_ITERATIONS = 30  # Measured requests per endpoint

RESULTS_DIR = Path(__file__).resolve().parent.parent / "benchmarks"
RESULTS_FILE = RESULTS_DIR / "results.json"


# ---------------------------------------------------------------------------
# Top 20 endpoint definitions (method, path, requires_auth, payload/params)
# ---------------------------------------------------------------------------

TOP_20_ENDPOINTS = [
    {
        "name": "GET /api/v1/health",
        "method": "GET",
        "path": "/api/v1/health",
        "auth": False,
    },
    {
        "name": "POST /api/v1/auth/login",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "auth": False,
        "json": {"email": "patron@test.com", "password": "password123"},
    },
    {
        "name": "GET /api/v1/auth/me",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "auth": True,
    },
    {
        "name": "POST /api/v1/auth/refresh",
        "method": "POST",
        "path": "/api/v1/auth/refresh",
        "auth": True,
    },
    {
        "name": "GET /api/v1/catalog",
        "method": "GET",
        "path": "/api/v1/catalog",
        "auth": False,
        "params": {"q": "fiction", "limit": 20},
    },
    {
        "name": "GET /api/v1/catalog/search",
        "method": "GET",
        "path": "/api/v1/catalog/search",
        "auth": False,
        "params": {"q": "history", "limit": 20},
    },
    {
        "name": "POST /api/v1/catalog/advanced-search",
        "method": "POST",
        "path": "/api/v1/catalog/advanced-search",
        "auth": False,
        "json": {"title": "mystery", "limit": 20},
    },
    {
        "name": "GET /api/v1/catalog/special/new-arrivals",
        "method": "GET",
        "path": "/api/v1/catalog/special/new-arrivals",
        "auth": False,
    },
    {
        "name": "GET /api/v1/search/unified",
        "method": "GET",
        "path": "/api/v1/search/unified",
        "auth": False,
        "params": {"q": "python", "limit": 20},
    },
    {
        "name": "GET /api/v1/circulation/checkouts",
        "method": "GET",
        "path": "/api/v1/circulation/checkouts",
        "auth": True,
    },
    {
        "name": "GET /api/v1/circulation/checkouts/active",
        "method": "GET",
        "path": "/api/v1/circulation/checkouts/active",
        "auth": True,
    },
    {
        "name": "GET /api/v1/circulation/holds",
        "method": "GET",
        "path": "/api/v1/circulation/holds",
        "auth": True,
    },
    {
        "name": "GET /api/v1/circulation/holds/active",
        "method": "GET",
        "path": "/api/v1/circulation/holds/active",
        "auth": True,
    },
    {
        "name": "GET /api/v1/circulation/fines",
        "method": "GET",
        "path": "/api/v1/circulation/fines",
        "auth": True,
    },
    {
        "name": "GET /api/v1/circulation/fines/summary",
        "method": "GET",
        "path": "/api/v1/circulation/fines/summary",
        "auth": True,
    },
    {
        "name": "GET /api/v1/favorites",
        "method": "GET",
        "path": "/api/v1/favorites",
        "auth": True,
    },
    {
        "name": "GET /api/v1/notifications",
        "method": "GET",
        "path": "/api/v1/notifications",
        "auth": True,
    },
    {
        "name": "GET /api/v1/branches",
        "method": "GET",
        "path": "/api/v1/branches",
        "auth": False,
    },
    {
        "name": "GET /api/v1/events",
        "method": "GET",
        "path": "/api/v1/events",
        "auth": False,
    },
    {
        "name": "GET /api/v1/staff/patrons",
        "method": "GET",
        "path": "/api/v1/staff/patrons",
        "auth": True,
        "staff": True,
    },
]


def _percentile(data: List[float], pct: float) -> float:
    """Calculate percentile from a sorted list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * pct / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


async def _get_auth_token(client: AsyncClient, email: str, password: str) -> str | None:
    """Authenticate and return a bearer token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


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
    elif method == "PUT":
        if "json" in endpoint:
            kwargs["json"] = endpoint["json"]
        start = time.perf_counter()
        resp = await client.put(path, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
    else:
        raise ValueError(f"Unsupported method: {method}")

    return duration_ms, resp.status_code


@pytest.mark.asyncio
class TestEndpointBenchmarks:
    """
    Benchmark the top 20 endpoints and write results to JSON.

    The test itself always passes -- regression detection is handled by the
    compare_benchmarks.py script that runs as a separate CI step.
    """

    async def test_benchmark_top_20_endpoints(self):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Obtain auth tokens
            patron_token = await _get_auth_token(
                client, "patron@test.com", "password123"
            )
            staff_token = await _get_auth_token(
                client, "staff@test.com", "password123"
            )

            patron_headers = (
                {"Authorization": f"Bearer {patron_token}"} if patron_token else {}
            )
            staff_headers = (
                {"Authorization": f"Bearer {staff_token}"} if staff_token else {}
            )

            results: Dict[str, dict] = {}

            for ep in TOP_20_ENDPOINTS:
                name = ep["name"]

                # Pick the right auth headers
                if ep.get("staff"):
                    headers = staff_headers
                elif ep.get("auth"):
                    headers = patron_headers
                else:
                    headers = {}

                # Warm-up
                for _ in range(WARMUP_REQUESTS):
                    try:
                        await _make_request(client, ep, headers)
                    except Exception:
                        pass

                # Measured iterations
                durations: List[float] = []
                errors = 0

                for _ in range(BENCHMARK_ITERATIONS):
                    try:
                        duration_ms, status_code = await _make_request(
                            client, ep, headers
                        )
                        durations.append(duration_ms)
                        if status_code >= 500:
                            errors += 1
                    except Exception:
                        errors += 1

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
                        "p95_ms": round(_percentile(durations, 95), 2),
                        "p99_ms": round(_percentile(durations, 99), 2),
                        "stdev_ms": round(
                            statistics.stdev(durations) if len(durations) > 1 else 0.0,
                            2,
                        ),
                    }
                else:
                    results[name] = {
                        "method": ep["method"],
                        "path": ep["path"],
                        "iterations": 0,
                        "errors": errors,
                        "min_ms": 0,
                        "max_ms": 0,
                        "mean_ms": 0,
                        "median_ms": 0,
                        "p95_ms": 0,
                        "p99_ms": 0,
                        "stdev_ms": 0,
                    }

            # Write results
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            RESULTS_FILE.write_text(json.dumps(results, indent=2))

            # Print summary table
            print("\n" + "=" * 90)
            print("ENDPOINT BENCHMARK RESULTS")
            print("=" * 90)
            print(
                f"{'Endpoint':<45} {'Mean':>8} {'P95':>8} {'P99':>8} {'Err':>5}"
            )
            print("-" * 90)
            for name, metrics in results.items():
                print(
                    f"{name:<45} "
                    f"{metrics['mean_ms']:>7.1f}ms "
                    f"{metrics['p95_ms']:>7.1f}ms "
                    f"{metrics['p99_ms']:>7.1f}ms "
                    f"{metrics['errors']:>4}",
                )
            print("=" * 90)
            print(f"\nResults written to {RESULTS_FILE}")

            # Verification check: at least some endpoints responded
            successful = sum(
                1 for r in results.values() if r["iterations"] > 0
            )
            assert successful > 0, "No endpoints returned successful responses"
