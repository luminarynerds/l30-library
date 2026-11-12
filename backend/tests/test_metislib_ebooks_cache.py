# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for /ebooks serve-stale caching (indie shelf resilience).

When MetisLib is slow / down / circuit-open, the public shelves must degrade to
the last good cached copy instead of a blank or errored shelf (the /indie
flakiness). Also: the per-item hydration loops must let a service outage
propagate (so the stale copy serves) and only swallow a dead single id.
"""

import pathlib

import pytest
from unittest.mock import patch

from app.services.metislib_errors import MetisLibUnavailable

BACKEND = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_cache():
    store: dict = {}

    async def _get(key):
        return store.get(key)

    async def _set(key, value, ttl_seconds=300):
        store[key] = value

    with patch("app.api.v1.metislib_ebooks.get_cached", side_effect=_get), \
         patch("app.api.v1.metislib_ebooks.set_cached", side_effect=_set):
        yield store


@pytest.mark.asyncio
async def test_caches_fresh_and_skips_second_produce(fake_cache):
    from app.api.v1.metislib_ebooks import _cached_or_stale
    calls = []

    async def produce():
        calls.append(1)
        return {"items": [1, 2]}

    r1 = await _cached_or_stale("k", produce)
    assert r1 == {"items": [1, 2]}
    assert fake_cache["ebooks:fresh:k"] == {"items": [1, 2]}
    assert fake_cache["ebooks:stale:k"] == {"items": [1, 2]}

    r2 = await _cached_or_stale("k", produce)  # fresh hit
    assert r2 == {"items": [1, 2]}
    assert len(calls) == 1  # produce not called again


@pytest.mark.asyncio
async def test_serves_stale_on_metislib_failure(fake_cache):
    from app.api.v1.metislib_ebooks import _cached_or_stale
    fake_cache["ebooks:stale:k"] = {"items": ["old"]}  # a prior good copy

    async def produce():
        raise MetisLibUnavailable("circuit open")

    r = await _cached_or_stale("k", produce)
    assert r == {"items": ["old"]}  # degraded to stale, not an error


@pytest.mark.asyncio
async def test_reraises_when_no_stale(fake_cache):
    from app.api.v1.metislib_ebooks import _cached_or_stale

    async def produce():
        raise MetisLibUnavailable("circuit open")

    with pytest.raises(MetisLibUnavailable):
        await _cached_or_stale("k", produce)


def test_inner_loops_only_swallow_notfound():
    # Per-item hydration must NOT swallow outages (that blanked the shelf); it may
    # only skip a dead single id, letting MetisLibUnavailable/Error propagate to
    # _cached_or_stale for the stale fallback.
    s = (BACKEND / "app/api/v1/metislib_ebooks.py").read_text()
    assert "except (MetisLibNotFound, MetisLibUnavailable, MetisLibError)" not in s
    assert "except MetisLibNotFound as" in s
    assert "_cached_or_stale" in s
