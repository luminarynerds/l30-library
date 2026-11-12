# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for in-worker Resend rate-limit pacing (2026-05-19).

Catches the regression where a single submit-for-approval handler fires
N director notifications back-to-back and trips Resend's 5 req/s 429.
"""

import asyncio
import time

import pytest

from app.core import email as email_mod


@pytest.mark.asyncio
async def test_resend_pace_enforces_min_interval(monkeypatch):
    """Two consecutive _resend_pace() calls are separated by at least the
    configured interval."""
    monkeypatch.setattr(email_mod.settings, "resend_min_interval_s", 0.05)
    email_mod._resend_last_call_monotonic = 0.0

    start = time.monotonic()
    await email_mod._resend_pace()  # primes the timestamp; no sleep
    await email_mod._resend_pace()  # this one must wait ~0.05s
    elapsed = time.monotonic() - start

    assert elapsed >= 0.045, f"expected >= 0.045s pacing, got {elapsed:.4f}s"


@pytest.mark.asyncio
async def test_resend_pace_zero_interval_disables(monkeypatch):
    """Setting RESEND_MIN_INTERVAL_S=0 short-circuits to no pacing."""
    monkeypatch.setattr(email_mod.settings, "resend_min_interval_s", 0.0)
    email_mod._resend_last_call_monotonic = 0.0

    start = time.monotonic()
    for _ in range(5):
        await email_mod._resend_pace()
    elapsed = time.monotonic() - start

    assert elapsed < 0.02, f"expected ~0s with pacing disabled, got {elapsed:.4f}s"


@pytest.mark.asyncio
async def test_resend_pace_serializes_concurrent_callers(monkeypatch):
    """Three concurrent pace() callers are spaced out, not coalesced."""
    monkeypatch.setattr(email_mod.settings, "resend_min_interval_s", 0.05)
    email_mod._resend_last_call_monotonic = 0.0

    start = time.monotonic()
    await asyncio.gather(*(email_mod._resend_pace() for _ in range(3)))
    elapsed = time.monotonic() - start

    # 3 calls at 0.05s spacing -> at least 0.10s total (first is free).
    assert elapsed >= 0.095, f"expected >= 0.095s for 3 paced calls, got {elapsed:.4f}s"
